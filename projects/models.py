from django.db import models
from assets.models import Asset


class Project(models.Model):
    job_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    portfolio_img = models.ImageField(upload_to='project_thumbnails/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.job_id} - {self.name}"


class Snapshot(models.Model):
    project = models.ForeignKey(Project, related_name='snapshots', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    date = models.DateField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AssetInstance(models.Model):
    """
    An occurrence of a library Asset within a specific Snapshot of a Project.
    """
    snapshot = models.ForeignKey(Snapshot, related_name='instances', on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, related_name='instances', on_delete=models.PROTECT)

    # This is where the "1995 folders" die.
    # Store 'Location', 'System', 'Tag Number', etc., here.
    custom_fields = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.asset.name} in {self.snapshot.project.name}"