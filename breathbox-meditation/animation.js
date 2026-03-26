const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Set canvas size
canvas.width = 800;
canvas.height = 600;

// Animation variables
let frame = 0;
let personX = 100;
let personY = 400;
let direction = 1; // Always going right for infinite loop
const baseWalkSpeed = 2;
const slowSpeed = 1; // Speed going up
const fastSpeed = 3; // Speed going down
const hillStartX = 0;
const hillEndX = 800;
const hillPeakX = 300; // Moved left to make inhale shorter
const hillPeakY = 200;
const groundY = 500;

// Person dimensions
const personHeight = 60;
const personWidth = 30;

// Parabola parameters: y = a(x - h)² + k
// Vertex at (300, 200), passes through (0, 500) and (800, 500)
// Using point (0, 500): 500 = a(0 - 300)² + 200 => a = 300 / 90000 = 0.003333...
// But this needs to also work for (800, 500), so we'll use the left point
// a = (y - k) / (x - h)² = (500 - 200) / (0 - 300)² = 300 / 90000 = 0.003333...
const parabolaA = 0.003333;
const parabolaH = hillPeakX;
const parabolaK = hillPeakY;

// Calculate Y position on parabola based on X
function getHillY(x) {
    // Parabola equation: y = a(x - h)² + k
    return parabolaA * Math.pow(x - parabolaH, 2) + parabolaK;
}

// Calculate the slope angle at a given X position on the parabola
function getSlopeAngle(x) {
    // Derivative: dy/dx = 2a(x - h)
    const slope = 2 * parabolaA * (x - parabolaH);
    return Math.atan(slope);
}

// Draw the hill using parabola
function drawHill() {
    // Draw area below the curve (dark green)
    ctx.beginPath();
    ctx.moveTo(hillStartX, getHillY(hillStartX));
    
    // Draw parabola by connecting points
    for (let x = hillStartX; x <= hillEndX; x += 2) {
        ctx.lineTo(x, getHillY(x));
    }
    
    ctx.lineTo(hillEndX, canvas.height);
    ctx.lineTo(hillStartX, canvas.height);
    ctx.closePath();
    ctx.fillStyle = '#66BB6A'; // Light green color under the curve
    ctx.fill();
    
    // Draw area above the curve (blue)
    ctx.beginPath();
    ctx.moveTo(hillStartX, getHillY(hillStartX));
    
    // Draw parabola by connecting points (reverse direction)
    for (let x = hillStartX; x <= hillEndX; x += 2) {
        ctx.lineTo(x, getHillY(x));
    }
    
    ctx.lineTo(hillEndX, 0);
    ctx.lineTo(hillStartX, 0);
    ctx.closePath();
    ctx.fillStyle = '#64B5F6'; // Light blue color above the curve
    ctx.fill();
    
    // Draw the curve outline in black
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(hillStartX, getHillY(hillStartX));
    
    for (let x = hillStartX; x <= hillEndX; x += 2) {
        ctx.lineTo(x, getHillY(x));
    }
    ctx.stroke();
}

// Draw the person
function drawPerson(x, y, frame) {
    ctx.save();
    ctx.translate(x, y);
    
    // Rotate person to match the slope of the parabola
    const slopeAngle = getSlopeAngle(x);
    ctx.rotate(slopeAngle);
    
    // Determine if walking left or right based on direction
    const facingRight = direction === 1;
    if (!facingRight) {
        ctx.scale(-1, 1);
    }
    
    // Walking animation - leg position
    const legOffset = Math.sin(frame * 0.3) * 8;
    const armOffset = Math.sin(frame * 0.3 + Math.PI) * 6;
    
    // Head
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(0, -personHeight + 10, 8, 0, Math.PI * 2);
    ctx.fill();
    
    // Body
    ctx.strokeStyle = '#000';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(0, -personHeight + 18);
    ctx.lineTo(0, -personHeight + 40);
    ctx.stroke();
    
    // Arms
    ctx.beginPath();
    // Left arm (swinging)
    ctx.moveTo(0, -personHeight + 25);
    ctx.lineTo(-8 - armOffset, -personHeight + 35);
    // Right arm (swinging opposite)
    ctx.moveTo(0, -personHeight + 25);
    ctx.lineTo(8 + armOffset, -personHeight + 35);
    ctx.stroke();
    
    // Legs
    ctx.beginPath();
    // Left leg
    ctx.moveTo(0, -personHeight + 40);
    ctx.lineTo(-6 - legOffset, -personHeight + 55);
    // Right leg
    ctx.moveTo(0, -personHeight + 40);
    ctx.lineTo(6 + legOffset, -personHeight + 55);
    ctx.stroke();
    
    // Feet
    ctx.fillStyle = '#000';
    ctx.fillRect(-8 - legOffset, -personHeight + 55, 4, 3);
    ctx.fillRect(4 + legOffset, -personHeight + 55, 4, 3);
    
    ctx.restore();
}

// Main animation loop
function animate() {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw hill
    drawHill();
    
    // Determine speed based on whether going up or down
    let currentSpeed;
    if (personX < hillPeakX) {
        // Going up - slower
        currentSpeed = slowSpeed;
    } else {
        // Going down - faster
        currentSpeed = fastSpeed;
    }
    
    // Update person position
    personX += currentSpeed * direction;
    
    // Infinite loop: wrap around when reaching edges
    if (personX >= hillEndX) {
        // Reached right edge, wrap to left edge
        personX = hillStartX;
    } else if (personX <= hillStartX) {
        // Reached left edge, wrap to right edge
        personX = hillEndX;
    }
    
    // Calculate Y position on parabola (person follows the parabola exactly)
    // Person's feet are at y - 5 (since feet are at -personHeight + 55 = -60 + 55 = -5)
    // So we set y = getHillY(personX) + 5 to put feet on the hill surface
    personY = getHillY(personX) + 5;
    
    // Draw person
    drawPerson(personX, personY, frame);
    
    // Draw inhale/exhale text
    ctx.fillStyle = '#000';
    ctx.textAlign = 'center';
    
    // Calculate progress for text size (0 to 1)
    // During inhale: grows from 0 to 1, during exhale: shrinks from 1 to 0
    let progress;
    if (personX < hillPeakX) {
        // Going up (inhale): progress from 0 to 1
        // Map personX from [hillStartX, hillPeakX] to [0, 1]
        progress = (personX - hillStartX) / (hillPeakX - hillStartX);
    } else {
        // Going down (exhale): progress from 1 to 0 (shrinking)
        // Map personX from [hillPeakX, hillEndX] to [1, 0]
        // At peak (400): progress = 1 (max size)
        // At end (800): progress = 0 (min size)
        // So as personX increases, progress must decrease
        progress = (hillEndX - personX) / (hillEndX - hillPeakX);
    }
    
    // Ensure progress stays in 0-1 range
    progress = Math.max(0, Math.min(1, progress));
    
    // Scale font size based on progress (grows from 16px to 80px for more dramatic effect)
    const minFontSize = 16;
    const maxFontSize = 80;
    const fontSize = minFontSize + (maxFontSize - minFontSize) * progress;
    ctx.font = `bold ${fontSize}px Arial`;
    
    // Show "inhale" when going up (before peak), "exhale" when going down (after peak)
    if (personX < hillPeakX) {
        ctx.fillText('inhale', canvas.width / 2, 80);
    } else {
        ctx.fillText('exhale', canvas.width / 2, 80);
    }
    
    // Draw instruction text at bottom left
    ctx.save();
    ctx.fillStyle = '#000';
    ctx.font = 'bold 28px Arial';
    ctx.textAlign = 'left';
    // Position text at bottom left of canvas
    ctx.fillText('Drink water, and find a quiet spot to breathe', 10, canvas.height - 30);
    ctx.restore();
    
    // Increment frame for animation
    frame++;
    
    requestAnimationFrame(animate);
}

// Start animation
animate();

