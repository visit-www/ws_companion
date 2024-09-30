document.addEventListener('DOMContentLoaded', function () {
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl);
    });
    toastList.forEach(toast => toast.show());
});
//code to ensure there is no background scrolling when embed code are displated 
document.addEventListener('DOMContentLoaded', () => {
    const modalElement = document.getElementById('embedCodeModal');

    // Check if modalElement exists to avoid errors
    if (modalElement) {
        modalElement.addEventListener('show.bs.modal', () => {
            document.body.classList.add('modal-open');
        });

        modalElement.addEventListener('hide.bs.modal', () => {
            document.body.classList.remove('modal-open');
        });
    } else {
        console.error('Modal element not found.');
    }
});
let lastUsedButton = null;
let lastUsedType = null;

document.addEventListener('DOMContentLoaded', function () {
    // Define the function to handle the embed code
    function setEmbedCodeFromButton(button) {
        // Retrieve the embed code from the data attribute
        var embedCode = button.getAttribute('data-embed-code');

        // Log the embed code to ensure it's retrieved correctly
        console.log('Embed Code:', embedCode);

        // Verify that 'button' is an HTML element
        if (!(button instanceof HTMLElement)) {
            console.error('The provided element is not a valid HTML element.');
            return; // Stop execution if the element is not valid
        }

        // Store the last used button
        lastUsedButton = button;

        // Determine the type of content from the embed code
        let type = '';
        if (embedCode.includes('video')) {
            type = 'video';
        } else if (embedCode.includes('img')) {
            type = 'image';
        } else if (embedCode.includes('script')) {
            type = 'script';
        } else {
            type = 'webpage'; // Default to webpage if no specific type is detected
        }

        // Store the last used type
        lastUsedType = type;

        // Get the containers for the different content types
        var video_container = document.getElementById('videoContainer');
        var webpage_container = document.getElementById('webpageContainer');
        var image_container = document.getElementById('imageContainer');

        // Clear all containers and display the appropriate one based on type
        video_container.style.display = 'none';
        webpage_container.style.display = 'none';
        image_container.style.display = 'none';

        if (type === 'video') {
            video_container.innerHTML = embedCode; // Inject the embed code
            video_container.style.display = 'block';
        } else if (type === 'webpage' || type === 'drawio') {
            webpage_container.innerHTML = embedCode;  // Inject webpage or draw.io content here
            webpage_container.style.display = 'block';
        } else if (type === 'image') {
            image_container.innerHTML = embedCode;

            // Handle embedded scripts within images, if necessary
            var scriptTag = image_container.querySelector('script');
            if (scriptTag) {
                var scriptSrc = scriptTag.src;
                scriptTag.remove();
                if (scriptSrc) {
                    var script = document.createElement('script');
                    script.src = scriptSrc;
                    script.async = true;
                    image_container.appendChild(script);
                }
            }
            image_container.style.display = 'block';
        } else if (type === 'script') {
            webpage_container.innerHTML = embedCode;

            // Reattach script tags to ensure execution
            var scriptTag = webpage_container.querySelector('script');
            if (scriptTag) {
                var scriptSrc = scriptTag.src;
                scriptTag.remove();
                if (scriptSrc) {
                    var script = document.createElement('script');
                    script.src = scriptSrc;
                    script.async = true;
                    webpage_container.appendChild(script);
                }
            }
            webpage_container.style.display = 'flex';
        }

        // Ensure the modal clears content when hidden
        var embedCodeModal = document.getElementById('embedCodeModal');
        embedCodeModal.addEventListener('hidden.bs.modal', function () {
            video_container.innerHTML = '';
            webpage_container.innerHTML = '';
            image_container.innerHTML = '';
        });
    }

    // Make the function globally accessible
    window.setEmbedCodeFromButton = setEmbedCodeFromButton;

    // Trigger the embed code re-injection when the modal is shown
    $('#embedCodeModal').on('shown.bs.modal', function () {
        if (lastUsedButton && lastUsedType) {
            setEmbedCodeFromButton(lastUsedButton); // Use the stored button element
        }
    });
});


// Functions to inject carousel when screen size is small.
// Functions to inject carousel when screen size is small.
//function initCarousel() {
//    $('.my-card-canvas').addClass('carousel slide').attr('data-bs-ride', 'carousel');
//    $('.my-card-box').addClass('carousel-inner').removeClass('row');
//    $('.card-img').removeClass('img-fluid rounded-start').addClass('carousel-img');
//    $('.my-card-item').removeClass('col-md-6 col-lg-4 mb-4').addClass('carousel-item').first().addClass('active');
//
//    $('#cardContainer').append(`
//        <button class="carousel-control-prev" type="button" data-bs-target="#cardContainer" data-bs-slide="prev">
//            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
//            <span class="visually-hidden">Previous</span>
//        </button>
//        <button class="carousel-control-next" type="button" data-bs-target="#cardContainer" data-bs-slide="next">
//            <span class="carousel-control-next-icon" aria-hidden="true"></span>
//            <span class="visually-hidden">Next</span>
//        </button>
//    `);
//
//    // Initialize the carousel
//    $('#cardContainer').carousel();
//}

//function destroyCarousel() {
//    $('.my-card-canvas').removeClass('carousel slide').removeAttr('data-bs-ride');
//    $('.my-card-box').removeClass('carousel-inner').addClass('row');
//    $('.my-card-item').removeClass('carousel-item active').addClass('col-md-6 col-lg-4 mb-4');
//    $('.card-img').removeClass('carousel-img').addClass('img-fluid rounded-start');
//    
//    // Removing carousel controls and indicators
 //   $('#cardContainer .carousel-control-prev, #cardContainer .carousel-control-next').remove();
//    $('#cardContainer .carousel-indicators').remove();
//}


// Function to handle the class switching based on screen size
function updateGridClass() {
    var element = document.querySelector('.row.my-frame');
    
    if (element) {  // Ensure the element exists
    if (window.innerWidth < 468) {
            //If the screen width is less than 468px, remove g-5 and add g-3
            if (element.classList.contains('g-5')) {
                element.classList.remove('g-5');
                element.classList.add('g-3');
            }
        } else {
            // If the screen width is greater than or equal to 468px, revert to g-5
                if (element.classList.contains('g-3')) {
                element.classList.remove('g-3');
                element.classList.add('g-5');
            }
        }
    }
}
//Listen for resize events and apply the function
window.addEventListener('resize', updateGridClass);

// Call the function once when the script loads to set the initial state
updateGridClass();

// JavaScript function to confirm the reset action

function ConfirmReset() {
    return confirm('Are you sure you want to reset the users? This action cannot be undone.');
}
