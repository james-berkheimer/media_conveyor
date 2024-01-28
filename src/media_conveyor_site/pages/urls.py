from django.urls import path

from .views import GetParsedItemsView, MediaViewTest, index, media_container

# from rest_framework.urlpatterns import format_suffix_patterns

# urlpatterns = {}
# urlpatterns = format_suffix_patterns(urlpatterns)

urlpatterns = [
    path("", index, name="index"),
    path("main/", MediaViewTest.as_view(), name="main"),
    path("get_parsed_items/", GetParsedItemsView.as_view(), name="get_parsed_items"),
    path("media_container/", media_container, name="media_container"),
]
