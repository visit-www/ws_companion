document.addEventListener('DOMContentLoaded', function () {
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl);
    });
    toastList.forEach(toast => toast.show());
});

/** function that injects embed code into iframe of modal */
function setEmbedCodeFromButton(type, button) {
    var video_container = document.getElementById('videoContainer');
    var video_iframe = document.getElementById('embediframe');
    var webpage_container = document.getElementById('webpageContainer');
    var image_container = document.getElementById('imageContainer');

    // Retrieve the embed code from the data attribute
    var embedCode = button.getAttribute('data-embed-code');
    
    if (type === 'video') {
        video_container.innerHTML = ''; // Clear the container
        video_container.innerHTML = embedCode; // Inject the embed code
        video_container.style.display = 'block';
    } else if (type === 'webpage') {
        webpage_container.innerHTML = '';
        webpage_container.innerHTML = embedCode;
        webpage_container.style.display = 'block';
    } else if (type === 'image') {
        image_container.innerHTML = '';
        image_container.innerHTML = embedCode;

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
        webpage_container.innerHTML = '';
        webpage_container.innerHTML = embedCode;

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
        webpage_container.style.display = 'block';
    } else {
        webpage_container.innerHTML = embedCode;
        webpage_container.style.display = 'block';
    }

    // Close the modal once the embed code is set
    var embedCodeModal = document.getElementById('embedCodeModal'); // Assuming this is the modal element
    embedCodeModal.addEventListener('hidden.bs.modal', function () {
        video_container.innerHTML = '';
        webpage_container.innerHTML = '';
        image_container.innerHTML = '';
    });
}

// Functions to inject carousel when screen size is small.
function initCarousel() {
    $('.card-canvas').removeClass('row')
    $('.card-canvas').addClass('carousel slide').attr('data-bs-ride', 'carousel');
    $('.card-box').addClass('carousel-inner');
    $('#cardContainer .card-item').addClass('carousel-item').first().addClass('active');

    $('#cardContainer').append(`
        <button class="carousel-control-prev" type="button" data-bs-target="#cardContainer" data-bs-slide="prev">
            <span class="carousel-control-prev-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Previous</span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#cardContainer" data-bs-slide="next">
            <span class="carousel-control-next-icon" aria-hidden="true"></span>
            <span class="visually-hidden">Next</span>
        </button>
    `);

    var cards = $('#cardContainer .card-item');
    var indicatorsContainer = $('<div class="carousel-indicators"></div>');

    cards.each(function (index, card) {
        var cardClass = $(card).attr('data-class');
        indicatorsContainer.append(`
            <button type="button" data-bs-target="#cardContainerIndicators" data-bs-slide-to="${index}" aria-label="${cardClass}"></button>
        `);
    });
    $('.carousel').prepend(indicatorsContainer);
}

function destroyCarousel() {
    $('.card-canvas').removeClass('carousel slide').removeAttr('data-bs-ride');
    $('.card-box').removeClass('carousel-inner').addClass('row');
    $('.card-item').removeClass('carousel-item active');
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

$(document).ready(function () {
    checkScreenWidth();
    $(window).on('resize', checkScreenWidth);
});