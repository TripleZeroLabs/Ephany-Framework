from django.db import models


class Manufacturer(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    unique_id = models.CharField(max_length=100, unique=True, verbose_name="Asset ID")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='assets')
    model = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return f"{self.manufacturer.name} {self.model} ({self.unique_id})"