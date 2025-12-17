from django.db import models
from django.utils import timezone

class Project(models.Model):
    job_id = models.CharField(max_length=100, unique=True, verbose_name="Job ID")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # Adding timestamps is highly recommended for sorting logic
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['job_id']  # Default ordering for stable pagination

    def __str__(self):
        return f"{self.name} ({self.job_id})"


class Snapshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='snapshots')
    name = models.CharField(max_length=255)
    # defaults to now, but can be edited
    date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']  # Newest snapshots first by default

    def __str__(self):
        return f"{self.name} - {self.project.name}"