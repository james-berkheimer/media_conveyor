document.querySelectorAll('a[data-media-type]').forEach(function(element) {
    element.addEventListener('click', function() {
        var mediaType = this.getAttribute('data-media-type');
        console.log(mediaType);

        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/get_parsed_items/?media_type=' + mediaType, true);
        xhr.onreadystatechange = function () {
            if (xhr.readyState === 4 && xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                var xhr2 = new XMLHttpRequest();
                // xhr2.open('GET', '/pages/templates/pages/media_container.html', true);
                xhr2.open('GET', '/media_container/', true);
                xhr2.onreadystatechange = function () {
                    if (xhr2.readyState === 4 && xhr2.status === 200) {
                        document.getElementById('media_container').innerHTML = xhr2.responseText;
                        data.forEach(function(media_item) {
                            console.log('media_item:', media_item);
                            document.querySelector('.list-row .thumbnail img').src = media_item.thumbnail_url;
                            document.querySelector('.list-row .thumbnail img').alt = media_item.title + ' Thumbnail';
                            document.querySelector('.list-row .details .title').textContent = media_item.title;
                            document.querySelector('.list-row .details .year').textContent = 'Year: ' + media_item.year;
                            document.querySelector('.list-row .details .description').textContent = media_item.description;
                        });
                    }
                };
                xhr2.send();
            }
        };
        xhr.send();
    });
});