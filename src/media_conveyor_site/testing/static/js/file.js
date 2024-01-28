// src/media_conveyor_site/testing/static/js/file.js
document.getElementById('clickMeButton').addEventListener('click', function() {
    // Using AJAX to load the content of display_text.html
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/testing/display_text/', true);
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            var displayedText = xhr.responseText;
            document.getElementById('displayedTextContainer').innerHTML = displayedText;
        }
    };
    xhr.send();
});
