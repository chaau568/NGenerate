from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from django.core.files.base import ContentFile
from django.conf import settings
import os

import requests
from pathlib import PurePosixPath
from utils.runpod_storage import delete_runpod_file, delete_runpod_folder


def upload_to_runpod(file, path):

    url = f"{settings.AI_API_URL}/upload"

    files = {"file": (file.name, file, file.content_type)}

    data = {"path": path}

    r = requests.post(url, files=files, data=data)

    r.raise_for_status()

    return r.json()["relative_path"]


def novel_cover_path(instance, filename):

    user_id = instance.user_id
    novel_id = instance.id

    ext = filename.split(".")[-1] if "." in filename else "png"

    filename = f"cover.{ext}"

    return str(
        PurePosixPath(
            "user_data",
            f"user_{user_id}",
            f"novel_{novel_id}",
            "meta",
            filename,
        )
    )


class Novel(models.Model):

    title = models.CharField(max_length=255, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="novels",
    )

    cover = models.CharField(max_length=500, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_cover_url(self):

        if self.cover:
            return self.cover

        return "assets/defaults/default_cover.jpg"

    def set_cover(self, file):

        path = novel_cover_path(self, file.name)

        relative_path = upload_to_runpod(file, path)

        if self.cover:
            delete_runpod_file(self.cover)

        self.cover = relative_path
        self.save(update_fields=["cover"])

    def delete(self, *args, **kwargs):

        folder = f"user_data/user_{self.user_id}/novel_{self.id}"

        try:
            delete_runpod_folder(folder)
        except Exception:
            pass

        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Novel({self.id}): {self.title}"

    def get_total_chapters(self):
        return self.chapters.count()

    def get_total_analyzed_chapters(self):
        return self.chapters.filter(is_analyzed=True).count()

    def add_chapter(self, story: str):
        next_order = self.chapters.count() + 1

        return Chapter.objects.create(novel=self, order=next_order, story=story)

    def get_chapters(self):
        return self.chapters.order_by("order")

    def get_characters(self):
        return self.character_profiles.all()

    def get_chapter_ids(self):
        return list(self.chapters.values_list("id", flat=True))

    @transaction.atomic
    def bulk_add_chapters(self, chapters_data: list):
        last_chapter = self.chapters.order_by("order").last()
        last_order = last_chapter.order if last_chapter else 0

        new_chapters = []
        for item in chapters_data:
            if isinstance(item, dict):
                order_from_file = item.get("order")
                content = item.get("story", "")
            else:
                order_from_file = None
                content = item

            if order_from_file is not None:
                current_order = order_from_file
            else:
                last_order += 1
                current_order = last_order

            if not Chapter.objects.filter(novel=self, order=current_order).exists():
                new_chapters.append(
                    Chapter(
                        novel=self,
                        order=current_order,
                        title=f"{self.title}#{current_order}",
                        story=content,
                    )
                )
            else:
                print(f"[Skip] Chapter order {current_order} already exists")

        if new_chapters:
            created = Chapter.objects.bulk_create(new_chapters)
            self.updated_at = timezone.now()
            self.save(update_fields=["updated_at"])
            return created
        return []


class Chapter(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name="chapters")
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    story = models.TextField(blank=True)
    is_analyzed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]
        unique_together = ("novel", "order")

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = f"{self.novel.title}#{self.order}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Chapter({self.title}) of Novel({self.novel.title})"

    def edit(self, title=None, story=None):
        if title is not None:
            self.title = title
        if story is not None:
            self.story = story

        self.save()
        return self

    def fix_story_with_ai(self):
        url = f"{settings.AI_API_URL}/fix-text/process-chapter"
        payload = {"story": self.story}

        try:
            resp = requests.post(url, json=payload, timeout=600)
            resp.raise_for_status()

            fixed_data = resp.json()
            self.story = fixed_data.get("fixed_story", self.story)
            self.save(update_fields=["story", "updated_at"])
            return True
        except Exception as e:
            print(f"Error in fix_story_with_ai: {e}")
            return False
