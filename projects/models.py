from django.db import models
from django.core.exceptions import ValidationError
from assets.models import Asset, AssetComponent


class Site(models.Model):
    """
    A physical site that one or more Projects belong to.
    site_id is a user-defined identifier (not the database PK).
    """
    site_id = models.CharField(max_length=100, unique=True, verbose_name="Site ID")
    name = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.site_id if not self.name else f"{self.site_id} — {self.name}"

    class Meta:
        ordering = ['site_id']


class Project(models.Model):

    # Status choices
    STATUS_RED = 'red'
    STATUS_YELLOW = 'yellow'
    STATUS_GREEN = 'green'
    STATUS_BLUE = 'blue'

    STATUS_CHOICES = [
        (STATUS_RED,    'Red'),
        (STATUS_YELLOW, 'Yellow'),
        (STATUS_GREEN,  'Green'),
        (STATUS_BLUE,   'Blue'),
    ]

    # Core identity
    job_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    portfolio_img = models.ImageField(upload_to='project_thumbnails/', blank=True, null=True)

    # Site relationship
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name='projects',
        null=True,
        blank=True,
    )

    # Flexible key/value store for additional project metadata
    custom_fields = models.JSONField(default=dict, blank=True)

    # Address — structured for future geocoding / map views
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True, verbose_name="State / Province")
    zip_code = models.CharField(max_length=20, blank=True, verbose_name="ZIP / Postal Code")
    country = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Project metadata
    go_live_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        blank=True,
    )

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
    # Store 'Location', 'System', 'Tag Number', etc., here.'
    instance_id = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=200, blank=True, null=True)
    custom_fields = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.asset.name} in {self.snapshot.project.name}"


class AssetComponentInstance(models.Model):
    """
    Links an optional AssetComponent to a specific AssetInstance.
    Only optional AssetComponents can be added to AssetInstances.
    Allows tracking which optional components are actually included in each instance.
    """
    asset_instance = models.ForeignKey(
        AssetInstance,
        on_delete=models.CASCADE,
        related_name='optional_components',
        verbose_name="Asset Instance"
    )
    asset_component = models.ForeignKey(
        AssetComponent,
        on_delete=models.CASCADE,
        related_name='instances',
        verbose_name="Asset Component"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity of this optional component for this specific instance. Defaults to the component's base quantity."
    )

    class Meta:
        unique_together = ['asset_instance', 'asset_component']
        verbose_name = "Asset Component Instance"
        verbose_name_plural = "Asset Component Instances"
        ordering = ['asset_instance', 'asset_component']

    def clean(self):
        """Validate that only optional components can be added to instances."""
        super().clean()
        if self.asset_component:
            if not self.asset_component.can_add_per_instance:
                raise ValidationError({
                    'asset_component': 'Only optional AssetComponents can be added to AssetInstances. This component is marked as required.'
                })
            # Validate that the component belongs to the asset instance's asset
            if self.asset_instance and self.asset_component.parent_asset != self.asset_instance.asset:
                raise ValidationError({
                    'asset_component': f"This component belongs to '{self.asset_component.parent_asset.name}', but the instance is for '{self.asset_instance.asset.name}'."
                })

    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.asset_instance.asset.name} → {self.asset_component.child_asset.name} (x{self.quantity})"