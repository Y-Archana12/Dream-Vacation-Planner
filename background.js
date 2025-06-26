// Three.js background animation
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
document.getElementById('bg-animation').appendChild(renderer.domElement);

// Create particles
const particlesGeometry = new THREE.BufferGeometry();
const particlesCount = 5000;
const posArray = new Float32Array(particlesCount * 3);
const colorArray = new Float32Array(particlesCount * 3);
const sizeArray = new Float32Array(particlesCount);

for(let i = 0; i < particlesCount * 3; i++) {
    posArray[i] = (Math.random() - 0.5) * 10;
    colorArray[i] = Math.random() * 0.5;
    sizeArray[i/3] = Math.random() * 0.02;
}

particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
particlesGeometry.setAttribute('color', new THREE.BufferAttribute(colorArray, 3));
particlesGeometry.setAttribute('size', new THREE.BufferAttribute(sizeArray, 1));

// Material
const particlesMaterial = new THREE.PointsMaterial({
    size: 0.02,
    vertexColors: true,
    transparent: true,
    opacity: 0.3,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true
});

// Mesh
const particlesMesh = new THREE.Points(particlesGeometry, particlesMaterial);
scene.add(particlesMesh);

// Add ambient light
const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
scene.add(ambientLight);

// Add point lights
const pointLight1 = new THREE.PointLight(0x4a90e2, 0.5);
pointLight1.position.set(5, 5, 5);
scene.add(pointLight1);

const pointLight2 = new THREE.PointLight(0x67b26f, 0.5);
pointLight2.position.set(-5, -5, 5);
scene.add(pointLight2);

camera.position.z = 5;

// Mouse interaction
let mouseX = 0;
let mouseY = 0;
let targetX = 0;
let targetY = 0;

document.addEventListener('mousemove', (event) => {
    mouseX = (event.clientX / window.innerWidth) * 2 - 1;
    mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
});

// Animation
const animate = () => {
    requestAnimationFrame(animate);
    
    // Smooth mouse follow
    targetX = mouseX * 0.0005;
    targetY = mouseY * 0.0005;
    
    // Rotate particles
    particlesMesh.rotation.y += 0.0002;
    particlesMesh.rotation.x += 0.0002;
    
    // Mouse interaction
    particlesMesh.rotation.x += targetY;
    particlesMesh.rotation.y += targetX;
    
    // Animate particles
    const positions = particlesGeometry.attributes.position.array;
    const sizes = particlesGeometry.attributes.size.array;
    
    for(let i = 0; i < positions.length; i += 3) {
        // Wave effect
        positions[i + 1] += Math.sin(Date.now() * 0.0005 + i) * 0.00005;
    }
    
    particlesGeometry.attributes.position.needsUpdate = true;
    
    // Animate lights
    pointLight1.position.x = Math.sin(Date.now() * 0.0005) * 3;
    pointLight1.position.y = Math.cos(Date.now() * 0.0005) * 3;
    
    pointLight2.position.x = Math.sin(Date.now() * 0.0005 + Math.PI) * 3;
    pointLight2.position.y = Math.cos(Date.now() * 0.0005 + Math.PI) * 3;
    
    renderer.render(scene, camera);
};

animate();

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}); 