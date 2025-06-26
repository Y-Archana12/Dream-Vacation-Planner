from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv
import time
import random
import sqlite3
from flask_sqlalchemy import SQLAlchemy
import json

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-123456789'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# API Keys
weather_api_key = "63467cd7e727542a1c312ec034d248e9"
unsplash_access_key = "RoQXgGwbu8DzFgHqAEpH3y2gPLS9kH3I4sx2r6tmroA"
locationiq_api_key = "pk.f3431b871a075efc876f69e4ca798ee6"
google_places_key = "AIzaSyDclOQ1g3Z8Z1Z1Z1Z1Z1Z1Z1Z1Z1"  # Replace with your key

# Settings
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    saved_cities = db.Column(db.Text, default='[]')
    theme_preference = db.Column(db.String(20), default='light')

    def __init__(self, username, password, email):
        self.username = username
        self.password = generate_password_hash(password, method='pbkdf2:sha256')
        self.email = email
        self.saved_cities = '[]'
        self.theme_preference = 'light'

    def get_saved_cities(self):
        try:
            return json.loads(self.saved_cities)
        except:
            return []

    def set_saved_cities(self, cities):
        self.saved_cities = json.dumps(cities)

# Initialize database
def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        # Create admin user if not exists
        admin = User('admin', 'admin123', 'admin@example.com')
        db.session.add(admin)
        db.session.commit()

# Initialize the database
init_db()

# Login manager user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Profile route
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

# Save city route
@app.route('/save_city', methods=['POST'])
@login_required
def save_city():
    city = request.json.get('city')
    if city:
        try:
            saved_cities = current_user.get_saved_cities()
            if city not in saved_cities:
                saved_cities.append(city)
                current_user.set_saved_cities(saved_cities)
                db.session.commit()
                return jsonify({'success': True, 'message': f'{city} saved successfully!'})
            return jsonify({'success': False, 'message': f'{city} is already saved!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'No city provided'})

# Remove saved city route
@app.route('/remove_city', methods=['POST'])
@login_required
def remove_city():
    city = request.json.get('city')
    if city:
        try:
            saved_cities = current_user.get_saved_cities()
            if city in saved_cities:
                saved_cities.remove(city)
                current_user.set_saved_cities(saved_cities)
                db.session.commit()
                return jsonify({'success': True, 'message': f'{city} removed successfully!'})
            return jsonify({'success': False, 'message': f'{city} is not in saved cities!'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    return jsonify({'success': False, 'message': 'No city provided'})

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        # Create new user
        new_user = User(username=username, password=password, email=email)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('email')  # Using email field as username
        password = request.form.get('password')
        
        user = User.query.filter_by(email=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Settings route
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        theme = request.form.get('theme')
        if theme in ['light', 'dark']:
            current_user.theme_preference = theme
            db.session.commit()
            flash('Settings updated successfully!', 'success')
    return render_template('settings.html', user=current_user)

# Helper Functions
def make_api_request(url, params=None, headers=None):
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(1)
    return None

def generate_itinerary(city, places, weather_data=None):
    """Generate a location-specific itinerary based on tourist places"""
    if not places:
        return {
            "Day 1": ["Morning: City Center Exploration", "Afternoon: Local Museums", "Evening: Local Cuisine"],
            "Day 2": ["Morning: City Walking Tour", "Afternoon: Shopping Areas", "Evening: Cultural Show"],
            "Day 3": ["Morning: Remaining Attractions", "Afternoon: Local Markets", "Evening: Farewell Dinner"]
        }
    
    # Categorize places by type
    museums = [p for p in places if any(word in p['name'].lower() for word in ['museum', 'gallery', 'art', 'exhibition'])]
    landmarks = [p for p in places if any(word in p['name'].lower() for word in ['tower', 'monument', 'palace', 'castle', 'temple', 'church', 'cathedral'])]
    parks = [p for p in places if any(word in p['name'].lower() for word in ['park', 'garden', 'botanical', 'zoo'])]
    markets = [p for p in places if any(word in p['name'].lower() for word in ['market', 'mall', 'shopping', 'bazaar'])]
    
    # If categorization fails, use the first few places
    if not museums: museums = [p for p in places if p not in landmarks + parks + markets][:1]
    if not landmarks: landmarks = [p for p in places if p not in museums + parks + markets][:1]
    if not parks: parks = [p for p in places if p not in museums + landmarks + markets][:1]
    if not markets: markets = [p for p in places if p not in museums + landmarks + parks][:1]
    
    # Generate day-by-day itinerary
    itinerary = {
        "Day 1": [
            f"Morning: Visit {landmarks[0]['name']} - {landmarks[0].get('formatted_address', 'Famous landmark')}",
            f"Afternoon: Explore {museums[0]['name']} - {museums[0].get('formatted_address', 'Cultural site')}",
            f"Evening: Dinner at a highly-rated local restaurant near {landmarks[0]['name']}"
        ],
        "Day 2": [
            f"Morning: Guided tour of {landmarks[1]['name'] if len(landmarks) > 1 else landmarks[0]['name']}",
            f"Afternoon: Relax at {parks[0]['name']} - {parks[0].get('formatted_address', 'Beautiful park')}",
            "Evening: Experience local nightlife or cultural show"
        ],
        "Day 3": [
            f"Morning: Visit {museums[1]['name'] if len(museums) > 1 else museums[0]['name']}",
            f"Afternoon: Shopping at {markets[0]['name']} - {markets[0].get('formatted_address', 'Shopping area')}",
            "Evening: Farewell dinner with local specialties"
        ]
    }
    
    # Add travel tips
    itinerary["Travel Tips"] = [
        "Book popular attractions in advance",
        "Use public transportation to save money",
        "Try local cuisine at recommended restaurants",
        "Keep emergency contact numbers handy",
        "Carry a city map or use offline maps"
    ]
    
    return itinerary

# Routes
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    weather_data = None
    images = []
    tourist_places = []
    city = ""
    map_embed_url = None
    error_messages = []
    itinerary = None

    if request.method == "POST":
        city = request.form.get("city")
        if city:
            try:
                # WEATHER API
                try:
                    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
                    weather_response = make_api_request(weather_url)
                    if weather_response and weather_response.status_code == 200:
                        weather_data = weather_response.json()
                        print(f"Weather data received: {weather_data}")  # Debug print
                except Exception as e:
                    error_messages.append(f"Weather data unavailable: {str(e)}")
                    print(f"Weather error: {str(e)}")  # Debug print

                # UNSPLASH IMAGES
                try:
                    unsplash_url = f"https://api.unsplash.com/search/photos?query={city}&client_id={unsplash_access_key}&per_page=3"
                    image_response = make_api_request(unsplash_url)
                    if image_response and image_response.status_code == 200 and image_response.json().get("results"):
                        images = [result["urls"]["regular"] for result in image_response.json()["results"]]
                except Exception as e:
                    error_messages.append(f"City images unavailable: {str(e)}")
                    images = [
                        "https://via.placeholder.com/800x600.png?text=City+Image+1",
                        "https://via.placeholder.com/800x600.png?text=City+Image+2",
                        "https://via.placeholder.com/800x600.png?text=City+Image+3"
                    ]

                # GOOGLE PLACES API
                try:
                    places_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=tourist+attractions+in+{city}&key={google_places_key}"
                    places_response = make_api_request(places_url)
                    
                    if places_response and places_response.status_code == 200:
                        places_data = places_response.json()
                        if places_data.get('results'):
                            tourist_places = []
                            for place in places_data['results'][:6]:
                                tourist_places.append({
                                    'name': place.get('name', f'Attraction in {city}'),
                                    'formatted_address': place.get('formatted_address', 'Address not available'),
                                    'rating': place.get('rating', 'N/A'),
                                    'user_ratings_total': place.get('user_ratings_total', 'N/A')
                                })
                except Exception as e:
                    error_messages.append(f"Attractions data unavailable: {str(e)}")
                    tourist_places = [
                        {"name": f"Explore {city}", "formatted_address": "Various locations", "rating": "N/A"},
                        {"name": f"{city} Museum", "formatted_address": "City center", "rating": "N/A"},
                        {"name": f"{city} Park", "formatted_address": "Main park area", "rating": "N/A"}
                    ]

                # LOCATIONIQ MAP
                try:
                    loc_url = f"https://us1.locationiq.com/v1/search.php?key={locationiq_api_key}&q={city}&format=json"
                    loc_response = make_api_request(loc_url)
                    if loc_response and loc_response.status_code == 200:
                        loc_data = loc_response.json()
                        if loc_data:
                            lat, lon = loc_data[0]['lat'], loc_data[0]['lon']
                            map_embed_url = f"https://maps.google.com/maps?q={lat},{lon}&z=10&output=embed"
                except Exception as e:
                    error_messages.append(f"Map embed unavailable: {str(e)}")

                # Generate itinerary only if we have tourist places
                if tourist_places:
                    itinerary = generate_itinerary(city, tourist_places, weather_data)

            except Exception as e:
                error_messages.append(f"Error occurred: {str(e)}")

    return render_template(
        "index.html",
        city=city,
        weather=weather_data,  # Changed from weather_data to weather to match template
        images=images,
        tourist_places=tourist_places,
        itinerary=itinerary,
        error_messages=error_messages,
        map_embed_url=map_embed_url
    )

@app.route('/get_itinerary/<city>')
@login_required
def get_itinerary(city):
    try:
        # Get weather data for the city
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
        weather_response = make_api_request(weather_url)
        weather_data = weather_response.json() if weather_response else None

        # Get tourist places
        places_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=tourist+attractions+in+{city}&key={google_places_key}"
        places_response = make_api_request(places_url)
        places_data = places_response.json() if places_response else None
        tourist_places = places_data.get('results', []) if places_data else []

        # Generate itinerary
        itinerary = generate_itinerary(city, tourist_places, weather_data)
        return jsonify(itinerary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_packing_list/<city>')
@login_required
def get_packing_list(city):
    try:
        # Get weather data for the city
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_api_key}&units=metric"
        weather_response = make_api_request(weather_url)
        weather_data = weather_response.json() if weather_response else None

        # Base essentials
        essentials = [
            "Passport and travel documents",
            "Phone and charger",
            "Power adapter",
            "Wallet and cash",
            "Camera",
            "First aid kit",
            "Toiletries",
            "Hand sanitizer",
            "Face masks"
        ]

        # Base clothing
        clothing = [
            "Comfortable walking shoes",
            "Casual outfits",
            "Formal outfit",
            "Sleepwear",
            "Undergarments",
            "Socks"
        ]

        # Add weather-specific items
        weather_based = False
        if weather_data:
            temp = weather_data['main']['temp']
            weather_main = weather_data['weather'][0]['main'].lower()
            weather_based = True

            if temp < 10:  # Cold weather
                clothing.extend([
                    "Winter coat",
                    "Thermal underwear",
                    "Warm sweaters",
                    "Gloves and scarf",
                    "Winter boots",
                    "Warm hat"
                ])
            elif temp > 25:  # Hot weather
                clothing.extend([
                    "Sunglasses",
                    "Sun hat",
                    "Light, breathable clothing",
                    "Swimwear",
                    "Sandals"
                ])
                essentials.extend([
                    "Sunscreen",
                    "After-sun lotion",
                    "Insect repellent"
                ])

            if 'rain' in weather_main:
                clothing.append("Rain jacket")
                essentials.append("Umbrella")

        return jsonify({
            "essentials": essentials,
            "clothing": clothing,
            "weather_based": weather_based
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
