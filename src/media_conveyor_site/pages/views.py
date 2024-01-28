import json
from pprint import pprint

import redis
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

# Connect to our Redis instance
redis_instance = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)


def index(request):
    return render(request, "index.html")


def media_container(request):
    return render(request, "pages/media_container.html")


class MediaView(View):
    def get(self, request, *args, **kwargs):
        items = {}
        for key in redis_instance.keys("*"):
            # print(f"key: {key}")
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
                    print(f"episodes: {items[key_str]['episodes']}")

                # Fetch the title and year from Redis
                # print(f"title: {redis_instance.hget(key, 'title')}")
                # print(f"file path: {redis_instance.hget(key, 'file_path')}")
                # print(f"episodes: {redis_instance.hget(key, 'episodes')}")
                title = redis_instance.hget(key, "title").decode("utf-8")
                year = redis_instance.hget(key, "year").decode("utf-8")
                media_type = key.decode().split(":")[0]
                items[key_str]["title"] = title
                items[key_str]["year"] = year
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
        return render(
            request, "pages/main.html", {"items": parsed_items, "media_types": media_types}
        )


class MediaViewTest(View):
    def get_items_by_media_type(self, media_type):
        items = {}
        media_types = set()
        for key in redis_instance.keys(f"{media_type}:*"):
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

                # Fetch the title, year, and thumb_path from Redis
                title = redis_instance.hget(key, "title").decode("utf-8")
                year = redis_instance.hget(key, "year").decode("utf-8")
                thumb_path = redis_instance.hget(key, "thumb_path")
                if thumb_path is not None:
                    thumb_path = thumb_path.decode("utf-8")
                else:
                    thumb_path = "default_thumb_path"  # Replace with your default thumbnail URL
                print(f"thumb_path: {thumb_path}")
                items[key_str]["title"] = title
                items[key_str]["year"] = year
                items[key_str]["thumb_path"] = thumb_path  # Add this line

            media_types.add(key_str.split(":")[0])

        return items, sorted(
            (
                media_type,  # unformatted media_type
                media_type.replace("_", " ").title(),  # formatted media_type
            )
            for media_type in media_types
        )

    def parse_and_sort_items(self, items):
        sorted_items = sorted(items.items(), key=lambda x: x[0].split(":")[0])
        parsed_items = [
            {
                "id": key.split(":")[1],
                "type": key.split(":")[0],
                "title": value["title"],
                "year": value["year"],
                "episodes": [
                    {
                        "season": season.split(":")[1],
                        "episodes": [
                            {
                                "episode": episode.split(":")[1],
                                "details": details,
                                "episode_files": [
                                    {
                                        "file_path": file_path,
                                        "file_size": round(int(file_size) / (1024**3), 2),
                                    }
                                    for file_path, file_size in json.loads(
                                        details.get("episode_files", "{}")
                                    ).items()
                                ],
                            }
                            for episode, details in episodes.items()
                        ],
                    }
                    for season, episodes in value.get("episodes", {}).items()
                ],
            }
            for key, value in sorted_items
        ]
        return parsed_items

    def get_parsed_items(self, request):
        media_type = request.GET.get("media_type").lower()  # Convert to lowercase
        items = self.get_items_by_media_type(media_type)
        parsed_items = self.parse_and_sort_items(items)
        return JsonResponse(parsed_items, safe=False)

    def get(self, request, *args, **kwargs):
        media_type = request.GET.get("media_type", "*").lower()  # Convert to lowercase
        items, media_types = self.get_items_by_media_type(media_type)
        parsed_items = self.parse_and_sort_items(items)
        print(f"media_types: {media_types}")
        return render(
            request, "pages/main.html", {"media": parsed_items, "media_types": media_types}
        )


class GetParsedItemsView(View):
    def get(self, request):
        media_type = request.GET.get("media_type").lower()  # Convert to lowercase
        items, _ = MediaViewTest().get_items_by_media_type(media_type)  # Ignore media_types
        parsed_items = MediaViewTest().parse_and_sort_items(items)
        # print(f"parsed_items: {parsed_items}")
        return JsonResponse(parsed_items, safe=False)
