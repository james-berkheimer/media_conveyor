import json
from pprint import pprint

import redis
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.shortcuts import render
from django.views import View

# Connect to our Redis instance
redis_instance = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def index(request):
    return render(request, "index.html")


def tmp_view(request):
    return render(request, "pages/tmp.html")


# def main_page(request):
#     return render(request, "pages/main_page.html")


class MediaView(View):
    def get(self, request, *args, **kwargs):
        items = {}
        for key in redis_instance.keys("*"):
            key_str = key.decode("utf-8")
            type_of_key = redis_instance.type(key).decode("utf-8")

            if type_of_key == "hash":
                items[key_str] = {
                    k.decode("utf-8"): v.decode("utf-8")
                    for k, v in redis_instance.hgetall(key).items()
                }

                # Parse the episodes field
                if "episodes" in items[key_str]:
                    items[key_str]["episodes"] = json.loads(items[key_str]["episodes"])

                # Fetch the title and year from Redis
                movie_title = redis_instance.hget(key, "title").decode("utf-8")
                movie_year = redis_instance.hget(key, "year").decode("utf-8")
                media_type = key.decode().split(":")[0]
                items[key_str]["title"] = movie_title
                items[key_str]["year"] = movie_year
                items[key_str]["media_type"] = media_type

        sorted_items = sorted(items.items(), key=lambda x: x[0].split(":")[0])
        parsed_items = [
            (
                key.split(":")[1],
                key.split(":")[0],
                value["title"],
                value["year"],
                value.get("episodes", {}),
            )
            for key, value in sorted_items
        ]
        media_types = sorted(
            {key.split(":")[0].replace("_", " ").title() for key, value in sorted_items}
        )
        # print("<---- PARSED ITEMS ---->")
        # pprint(parsed_items)
        # print("<---- MEDIA TYPES ---->")
        # pprint(media_types)
        return render(
            request, "pages/main.html", {"items": parsed_items, "media_types": media_types}
        )


class MediaViewTest(View):
    def get(self, request, *args, **kwargs):
        items = {}
        for key in redis_instance.keys("*"):
            key_str = key.decode("utf-8")
            type_of_key = redis_instance.type(key).decode("utf-8")

            if type_of_key == "hash":
                items[key_str] = {
                    k.decode("utf-8"): v.decode("utf-8")
                    for k, v in redis_instance.hgetall(key).items()
                }

                # Parse the episodes field
                if "episodes" in items[key_str]:
                    items[key_str]["episodes"] = json.loads(items[key_str]["episodes"])

                # Fetch the title and year from Redis
                movie_title = redis_instance.hget(key, "title").decode("utf-8")
                movie_year = redis_instance.hget(key, "year").decode("utf-8")
                media_type = key.decode().split(":")[0]
                items[key_str]["title"] = movie_title
                items[key_str]["year"] = movie_year
                items[key_str]["media_type"] = media_type

        sorted_items = sorted(items.items(), key=lambda x: x[0].split(":")[0])
        parsed_items = [
            (
                key.split(":")[1],
                key.split(":")[0],
                value["title"],
                value["year"],
                value.get("episodes", {}),
            )
            for key, value in sorted_items
        ]
        media_types = {key.split(":")[0] for key, value in sorted_items}
        # print("<---- PARSED ITEMS ---->")
        # pprint(parsed_items)
        # print("<---- MEDIA TYPES ---->")
        # pprint(media_types)
        return render(
            request, "pages/media.html", {"items": parsed_items, "media_types": media_types}
        )
