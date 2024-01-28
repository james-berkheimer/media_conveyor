from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from pages.views import GetParsedItemsView, MediaViewTest, index, media_container

# from testing.views import display_text

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    # path("", index, name="index"),
    # path("main/", MediaViewTest.as_view(), name="main"),
    # path("get_parsed_items/", GetParsedItemsView.as_view(), name="get_parsed_items"),
    # path("media_container/", media_container, name="media_container"),
    ## Testing ##
    path("testing/", include("testing.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
