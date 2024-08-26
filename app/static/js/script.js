document.addEventListener('DOMContentLoaded', function () {
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl);
    });
    toastList.forEach(toast => toast.show());
});

/** function that injects embed code into iframeof modal */
function setEmbedCodeFromButton(type, button) {
    var video_container=document.getElementById('videoContainer');
    var video_iframe=document.getElementById('embediframe');
    var webpage_container=document.getElementById('webpageContainer');
    var image_container= document.getElementById('imageContainer');

    // Retrieve the embed code from the data attribute
    var embedCode = button.getAttribute('data-embed-code');
    
    if (type === 'video') {
        
        // Clear the container before injecting new content
        video_container.innerHTML = '';
        // Inject the complete embed code into the container
        video_container.innerHTML = embedCode;
        video_container.style.display = 'block';
    } else if (type === 'webpage') {
        webpage_container.innerHTML ='';
        webpage_container.innerHTML = embedCode;
        webpage_container.style.display = 'block';
    } else if (type === 'image') {
        
        image_container.innerHTML ='';
        image_container.innerHTML = embedCode;

        // Extract the script source from the embed code, if it's present
        var scriptSrc = '';
        var scriptTag = image_container.querySelector('script');
    
        if (scriptTag) {
            scriptSrc = scriptTag.src; // Get the script src attribute
            scriptTag.remove(); // Remove the script tag from the container to avoid duplication
        }
    
        // Inject the script tag back into the same container
        if (scriptSrc) {
            var script = document.createElement('script');
            script.src = scriptSrc;
            script.async = true;
    
            // Append the script back into the webpage_container
            image_container.appendChild(script);
        }
    
        // Ensure the container is visible
        image_container.style.display = 'block'; // 'inline' may not be appropriate; 'block' is more general

    }else if (type === 'script') {
        // Clear the existing content in the container
        webpage_container.innerHTML = '';
    
        // Inject the HTML part of the embed code into the container
        webpage_container.innerHTML = embedCode;
    
        // Extract the script source from the embed code, if it's present
        var scriptSrc = '';
        var scriptTag = webpage_container.querySelector('script');
    
        if (scriptTag) {
            scriptSrc = scriptTag.src; // Get the script src attribute
            scriptTag.remove(); // Remove the script tag from the container to avoid duplication
        }
    
        // Inject the script tag back into the same container
        if (scriptSrc) {
            var script = document.createElement('script');
            script.src = scriptSrc;
            script.async = true;
    
            // Append the script back into the webpage_container
            webpage_container.appendChild(script);
        }
    
        // Ensure the container is visible
        webpage_container.style.display = 'block'; // 'block' may not be appropriate; 'block' is more general
    }
    else{
        webpage_container.innerHTML = embedCode;
        webpage_container.style.display='block'
    }

     // Close the modal once the embed code is set
     // Listen for the modal to be hidden (closed)
    embedCodeModal.addEventListener('hidden.bs.modal', function() {
        // Reset 
        video_container.innerHTML='';
        webpage_container.innerHTML = '';
        image_container.innerHTML = "";

    });
}
//Functions to inject carousal when screen size is small.
// This function is used in content categories lay out such as guidline.html
function initCarousel() {
        alert('function activated')
        // Remove row class and add carousel-inner to the .card-box element
        $('.card-box').removeClass('row').addClass('carousel-inner carousel slide');
        $('.card-box').attr('data-ride', 'carousel');
    
        // Add carousel-item class to each card and set the first one as active
        $('#cardContainer .card-item').addClass('carousel-item');
        $('#cardContainer .carousel-item').first().addClass('active');
    
        // Add carousel controls
        $('#cardContainer').append(`
            <a class="carousel-control-prev" href="#cardContainer" role="button" data-slide="prev">
                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                <span class="sr-only">Previous</span>
            </a>
            <a class="carousel-control-next" href="#cardContainer" role="button" data-slide="next">
                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                <span class="sr-only">Next</span>
            </a>
        `);
    }
function destroyCarousel() {
        $('.card-box').removeAttr('data-ride');
    
        // Remove carousel-inner, carousel, and slide classes, and add row back
        $('.card-box').removeClass('carousel-inner carousel slide').addClass('row');
        $('c.card-item').removeClass('carousel-item active');
    
        // Remove carousel controls (HTML elements)
        $('#cardContainer .carousel-control-prev, #cardContainer .carousel-control-next').remove();
    }
function checkScreenWidth() {
        if ($(window).width() <= 468) {
            if (!$('.card-box').hasClass('carousel')) {
                initCarousel();
            }
        } else {
            if ($('.card-box').hasClass('carousel')) {
                destroyCarousel();
            }
        }
    }

$(document).ready(function() {
        checkScreenWidth();
        $(window).on('resize', checkScreenWidth);
    });