from django.http import HttpResponse
from django.shortcuts import render


def display_text(request):
    # Your logic to generate the content of display_text.html
    text_variable = "Hello, world!"

    # Render the content using the display_text.html template
    content = render(request, "testing/display_text.html", {"text": text_variable})

    # Return the rendered content as plain text (you can modify this as needed)
    return HttpResponse(content, content_type="text/plain")


def main_template(request):
    # Your logic for the main_template view
    return render(request, "testing/main_template.html")
