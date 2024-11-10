const jsonData = [
    {
        "inscriptionId": "76f55f9beb872a23ef07cf3d23ef47a7a169a16caec2f962e373d8839325ecb9i0",
        "name": "Spring Green",
        "traitIndex": "0:00"
    },
    {
        "inscriptionId": "ba29aa4c32893c43d0a648722f03d14210a54346ca065434d8aa0ed8ac7643bci0",
        "name": "Screamin' Green",
        "traitIndex": "0:01"
    },
    {
        "inscriptionId": "3aafea3fa9a63b60194ff5d51e9ff86851e880674173d18fac638101a069062bi0",
        "name": "Starship",
        "traitIndex": "0:02"
    },
    {
        "inscriptionId": "3ab1f0ef8f9d22957e96bb5b20d92e17b05e560913bc84eec8db0db1b2209c01i0",
        "name": "Flamingo",
        "traitIndex": "0:03"
    },
    {
        "inscriptionId": "c96f79da6dd81b5c3866eff61f4ee038d6f2f6a3653ea6946d0d11832a2f312ci0",
        "name": "Razzle Dazzle Rose",
        "traitIndex": "0:04"
    },
    {
        "inscriptionId": "da966dd1f908a3c9ccc4eee795db0b2f3dab319bd8d277dd24e050289c83b60di0",
        "name": "Royal Blue",
        "traitIndex": "0:05"
    },
    {
        "inscriptionId": "56d537b61bea135ca20d54a3580ec9d95163c2869fab6f0566314c31bf7cd10di0",
        "name": "Runner",
        "traitIndex": "1:00"
    },
    {
        "inscriptionId": "5f76a38f88170a4278bb444c5c8dcdf2864e3ae01339a692490e8531e264aae8i0",
        "name": "Dancer",
        "traitIndex": "1:01"
    },
    {
        "inscriptionId": "b869d1ed53406301ac35d5c4283ff85582ad4b2eaf27be168dc993074e7bcb8fi0",
        "name": "Expresser",
        "traitIndex": "1:02"
    },
    {
        "inscriptionId": "429e0974307cd58387945a069fb3fa81697de4fc964d26a130e06c0d23cf888fi0",
        "name": "Creeper",
        "traitIndex": "1:03"
    },
    {
        "inscriptionId": "bb30ca1e2879daaf088ce6718dd427bf44375711e4927aadce3259a99269c9a5i0",
        "name": "Wizzard",
        "traitIndex": "1:04"
    },
    {
        "inscriptionId": "e38218fef19bd823597e520bbcadbcd563de80dbb92dd80e0976a7dc0ac7e490i0",
        "name": "Sitter",
        "traitIndex": "1:05"
    },
    {
        "inscriptionId": "a9a2afa2f4584f968c3b483eb0b86a4f5b62080b4c999b39bb21fdea79dbc66bi0",
        "name": "Mole",
        "traitIndex": "2:00"
    },
    {
        "inscriptionId": "2e716672bc3e973e5d9de8b5370147d83d69f97263e7e64d06bda4909de26fbei0",
        "name": "Ohhh",
        "traitIndex": "2:01"
    },
    {
        "inscriptionId": "9dbe5820eef2468f1018b61f7b8b6d280c42b8602da41e876df848151a547ea1i0",
        "name": "Duh",
        "traitIndex": "2:02"
    },
    {
        "inscriptionId": "f16b0a3abed340d497efbaabd56fdfe8b7830aeac28fd4c300f0ddf6e8295269i0",
        "name": "Happy",
        "traitIndex": "2:03"
    },
    {
        "inscriptionId": "f30dc0bd49538ff54f9ccbbbacc88751546b20db6f47037a86f117f505119a32i0",
        "name": "Thinker",
        "traitIndex": "2:04"
    },
    {
        "inscriptionId": "11358a6734ea3694fb906e80bfa7d8c69679ef63d60d3ac3e3f7ae4e148ce6a4i0",
        "name": "Looker",
        "traitIndex": "2:05"
    }
];

function loadP5() {
    const script = document.createElement('script');
    script.src = "/content/2fd9bda05feb18801319b80f8991be03f581a478bf1bcce130183e12c3f7d43ai0";
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
let totalImages = 0;

let showText = false; // Flag to toggle text overlay

let compositeImage; // Off-screen graphics buffer
let compositeImageCreated = false; // Flag to track if composite image is created

// Function to get the 'sn' meta tag content
function getMetaContentByName(name) {
    const meta = document.querySelector(`meta[name="${name}"]`);
    return meta ? meta.getAttribute('content') : null;
}

// Preload function to load images
function preload() {
    const sn = getMetaContentByName('sn');
    if (sn) {
        const indices = sn.match(/.{1,2}/g); // Split into two-character pairs
        totalImages = indices.length; // Set total images to load
        indices.forEach((index, i) => {
            const traitIndex = `${i}:${index.padStart(2, '0')}`; // Construct traitIndex with leading zero
            console.log(`Looking for traitIndex: ${traitIndex}`); // Debugging: log the traitIndex
            const item = jsonData.find(obj => obj.traitIndex === traitIndex);
            if (item) {
                const imageUrl = `/content/${item.inscriptionId}`;
                console.log(`Loading image from: ${imageUrl}`); // Debugging: log the URL
                loadImage(imageUrl, img => {
                    console.log(`Image loaded: ${imageUrl}`); // Confirm image load
                    images.push(img);
                    imagesLoaded++;
                    if (imagesLoaded === totalImages) {
                        redraw(); // Redraw when all images are loaded
                    }
                }, () => {
                    console.error(`Failed to load image from: ${imageUrl}`); // Error handling
                    imagesLoaded++;
                    if (imagesLoaded === totalImages) {
                        redraw(); // Redraw when all images are loaded
                    }
                });
            } else {
                console.warn(`No item found for traitIndex: ${traitIndex}`); // Warn if no item found
                imagesLoaded++; // Increment to avoid hanging
                if (imagesLoaded === totalImages) {
                    redraw(); // Redraw when all images are loaded
                }
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

    if (imagesLoaded === totalImages && images.length > 0) {
        if (!compositeImageCreated) {
            // Create composite image
            let imgWidth = images[0].width;
            let imgHeight = images[0].height;

            compositeImage = createGraphics(imgWidth, imgHeight);

            // Draw images onto compositeImage
            images.forEach(img => {
                compositeImage.image(img, 0, 0, imgWidth, imgHeight);
            });

            if (showText) {
                // Overlay a semi-transparent black rectangle over the image area
                compositeImage.fill(0, 150); // Black with transparency
                compositeImage.rect(0, 0, imgWidth, imgHeight);

                compositeImage.fill(255); // White text
                compositeImage.textAlign(CENTER, CENTER);

                // Get the sn meta tag
                const sn = getMetaContentByName('sn');
                if (sn) {
                    const indices = sn.match(/.{1,2}/g);
                    const names = indices.map((index, i) => {
                        const traitIndex = `${i}:${index.padStart(2, '0')}`;
                        const item = jsonData.find(obj => obj.traitIndex === traitIndex);
                        return item ? item.name : '';
                    }).filter(name => name !== '');

                    // Define labels for each index
                    const labels = ['Background Color:', 'Body:', 'Face:'];

                    // Create text lines (label and name per trait)
                    let textLines = [];
                    names.forEach((name, index) => {
                        const label = labels[index] || `Index ${index} Name`;
                        textLines.push(label);
                        textLines.push(name);
                    });

                    // Adjust text size to fit within image area
                    const totalLines = textLines.length;
                    const linePadding = 2;

                    let textSizeValue = (imgHeight - totalLines * linePadding) / (totalLines * 0.2);
                    textSizeValue = compositeImage.constrain(textSizeValue, 2, 8);
                    compositeImage.textSize(textSizeValue);

                    const lineHeight = compositeImage.textAscent() + compositeImage.textDescent() + linePadding;
                    const totalTextHeight = lineHeight * totalLines;

                    // Start Y position for text
                    let textY = (imgHeight - totalTextHeight) / 2 + lineHeight / 2;

                    // Draw each line of text
                    textLines.forEach((line, index) => {
                        compositeImage.text(line, imgWidth / 2, textY + index * lineHeight);
                    });
                }
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