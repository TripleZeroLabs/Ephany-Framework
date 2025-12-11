from django.db import models
from django.utils import timezone

class Project(models.Model):
    job_id = models.CharField(max_length=100, unique=True, verbose_name="Job ID")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.job_id})"

class Snapshot(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='snapshots')
    name = models.CharField(max_length=255)
    # defaults to now, but can be edited
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} - {self.project.name}"