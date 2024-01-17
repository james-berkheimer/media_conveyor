from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from pages.views import MediaView, MediaViewTest, index, tmp_view
from rest_framework.urlpatterns import format_suffix_patterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),  # Uncommented this line
    path("media/", MediaViewTest.as_view(), name="media"),  # URL pattern for all items
    path(
        "media/<str:key>/", MediaViewTest.as_view(), name="media"
    ),  # URL pattern for individual item
    path("main/", MediaView.as_view(), name="main"),  # URL pattern for all items
    path("main/<str:key>/", MediaView.as_view(), name="main"),  # URL pattern for individual item
    path("tmp/", tmp_view, name="tmp"),
    # path("main_page/", main_page, name="main_page"),
    path("", index, name="index"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# urlpatterns = format_suffix_patterns(urlpatterns)
