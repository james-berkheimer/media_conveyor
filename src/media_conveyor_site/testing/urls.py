from django.urls import path

from .views import display_text, main_template  # Import the main_template view

urlpatterns = [
    path("display_text/", display_text, name="display_text"),
    path("main_template/", main_template, name="main_template"),
    # Other URL patterns
]
