from django.db import models
from django.conf import settings
from django.db import transaction
from django.utils import timezone

class Novel(models.Model):
    title = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='novels',
    )
    cover = models.ImageField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Novel({self.id}): {self.title}"
    
    def get_total_chapters(self):
        return self.chapters.count()
    
    def get_total_analyzed_chapters(self):
        return self.chapters.filter(is_analyzed=True).count()
    
    def add_chapter(self, story: str):
        next_order = self.chapters.count() + 1
        
        return Chapter.objects.create(
            novel=self,
            order=next_order,
            story=story
        )
        
    def get_chapters(self):
        return self.chapters.order_by('order')
    
    def get_chapter_ids(self):
        return list(self.chapters.values_list('id', flat=True))
    
    @transaction.atomic
    def bulk_add_chapters(self, chapters_data: list):
        last_chapter = self.chapters.order_by('order').last()
        current_order = last_chapter.order if last_chapter else 0
        
        new_chapters = []
        for content in chapters_data:
            current_order += 1
            generate_title = f"{self.title}#{current_order}"
            new_chapters.append(Chapter(
                novel=self,
                order=current_order,
                title=generate_title,
                story=content
            ))
            
        Novel.objects.filter(id=self.id).update(updated_at=timezone.now())

        return Chapter.objects.bulk_create(new_chapters)
    
    def edit(self, title=None, cover=None):
        if title is not None:
            self.title = title
        if cover is not None:
            self.cover = cover
            
        self.save()
        return self
        
    
class Chapter(models.Model):
    novel = models.ForeignKey(Novel, on_delete=models.CASCADE, related_name='chapters')
    order = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255, blank=True)
    story = models.TextField(blank=True)
    is_analyzed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ('novel', 'order')
        
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
    