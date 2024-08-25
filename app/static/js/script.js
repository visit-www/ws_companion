document.addEventListener('DOMContentLoaded', function () {
    var toastElList = [].slice.call(document.querySelectorAll('.toast'));
    var toastList = toastElList.map(function (toastEl) {
        return new bootstrap.Toast(toastEl);
    });
    toastList.forEach(toast => toast.show());
});

/** function that injects embed code into iframeof modal */
function setEmbedCodeFromButton(button) {
 
    // Retrieve the embed code from the data attribute
    var embedCode = button.getAttribute('data-embed-code');
    
    // Set the iframe content with the embed code
    var iframe = document.getElementById('embedIframe');

    iframe.srcdoc = embedCode;
     // Listen for the modal to be hidden (closed)
     embedCodeModal.addEventListener('hidden.bs.modal', function() {
        // Reset the iframe src to stop the video
        var iframe = document.getElementById('embedIframe');
        iframe.srcdoc = "";
    });
  
}