from django.db import models


class Manufacturer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(blank=True, verbose_name="Company Website")

    def __str__(self):
        return self.name


class AssetFile(models.Model):
    class Category(models.TextChoices):
        CUT_SHEET = 'PDS', 'Cut Sheet'
        CAD_FILE = 'DWG', 'CAD File'
        REVIT_FAMILY = 'RFA', 'Revit Family'
        OTHER = 'ETC', 'Other'

    file = models.FileField(upload_to='assets/files/')
    category = models.CharField(
        max_length=3,
        choices=Category.choices,
        default=Category.OTHER,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()}: {self.file.name}"


class Asset(models.Model):
    unique_id = models.CharField(max_length=100, unique=True, verbose_name="Asset ID")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='assets')
    files = models.ManyToManyField(AssetFile, blank=True, related_name='assets')
    model = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True, verbose_name="Product URL")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.manufacturer.name} {self.model} ({self.unique_id})"