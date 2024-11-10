function loadP5() {
    const script = document.createElement('script');
    script.src = "/content/2fd9bda05feb18801319b80f8991be03f581a478bf1bcce130183e12c3f7d43ai0"; //p5.js
    script.onload = () => {
        setup(); // Call setup after p5.js is loaded
    };
    document.head.appendChild(script);
}

loadP5();

// Apply styles dynamically
function applyStyles() {
    const style = document.createElement('style');
    style.textContent = `
        html, body {
            margin: 0;
            padding: 0;
            overflow: hidden; /* Prevent scrollbars */
            width: 100%;
            height: 100%;
        }
    `;
    document.head.appendChild(style);
}

applyStyles();

let images = [];
let imagesLoaded = 0;

let showText = false; // Flag to toggle text overlay

let compositeImage; // Off-screen graphics buffer
let compositeImageCreated = false; // Flag to track if composite image is created

let sn; // Declare sn at a higher scope to access it in draw

// Function to get the 'sn' meta tag content
function getMetaContentByName(name) {
    const meta = document.querySelector(`meta[name="${name}"]`);
    return meta ? meta.getAttribute('content') : null;
}

// Preload function to load a single image
function preload() {
    sn = getMetaContentByName('sn'); // Assign sn here
    if (sn) {
        const imageUrl = `/content/<emblem_inscription_id>`; // put the emblem inscription id here.
        console.log(`Loading image from: ${imageUrl}`); // Debugging: log the URL
        loadImage(imageUrl, img => {
            console.log(`Image loaded: ${imageUrl}`); // Confirm image load
            images.push(img);
            imagesLoaded++;
            if (imagesLoaded === 1) {
                redraw(); // Redraw when the image is loaded
            }
        }, () => {
            console.error(`Failed to load image from: ${imageUrl}`); // Error handling
            imagesLoaded++;
            if (imagesLoaded === 1) {
                redraw(); // Redraw when the image is loaded
            }
        });
    }
}

// Setup function for p5.js
function setup() {
    createCanvas(windowWidth, windowHeight); // Create a canvas that fills the window
    noLoop(); // Stop the draw loop after setup
}

// p5.js draw function
function draw() {
    background(255); // Clear the canvas

    if (imagesLoaded === 1 && images.length > 0) {
        if (!compositeImageCreated) {
            // Create composite image
            let imgWidth = images[0].width;
            let imgHeight = images[0].height;

            compositeImage = createGraphics(imgWidth, imgHeight);

            // Draw the image onto compositeImage
            compositeImage.image(images[0], 0, 0, imgWidth, imgHeight);

            if (showText) {
                // Overlay a semi-transparent black rectangle over the image area
                compositeImage.fill(0, 150); // Black with transparency
                compositeImage.rect(0, 0, imgWidth, imgHeight);

                compositeImage.fill(255); // White text
                compositeImage.textAlign(CENTER, CENTER);

                // Display the sn value
                compositeImage.textSize(16); // Set a fixed text size
                compositeImage.text(sn, imgWidth / 2, imgHeight / 2);
            }
            compositeImageCreated = true;
        }

        // Now draw compositeImage onto the canvas, scaling as needed
        let imgAspect = compositeImage.width / compositeImage.height;
        let canvasAspect = width / height;

        let drawWidth, drawHeight;

        if (imgAspect > canvasAspect) {
            drawWidth = width;
            drawHeight = drawWidth / imgAspect;
        } else {
            drawHeight = height;
            drawWidth = drawHeight * imgAspect;
        }

        let imgX = (width - drawWidth) / 2;
        let imgY = (height - drawHeight) / 2;

        image(compositeImage, imgX, imgY, drawWidth, drawHeight);
    }
}

// Function to handle window resizing
function windowResized() {
    resizeCanvas(windowWidth, windowHeight); // Adjust canvas size on window resize
    redraw(); // Redraw the canvas after resizing
}

// Function to handle mouse clicks
function mousePressed() {
    if (mouseButton === LEFT) {
        showText = !showText; // Toggle the showText flag on left click
        compositeImageCreated = false; // Reset to recreate composite image
        redraw(); // Redraw the canvas to update the display
    }
}