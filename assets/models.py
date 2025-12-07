from django.db import models
from django.core.exceptions import ValidationError
import re
import os


def manufacturer_logo_path(instance, filename):
    ext = filename.split('.')[-1]
    pk = instance.pk if instance.pk else "new"
    return os.path.join('manufacturers', f"logo_{pk}.{ext}")


def asset_catalog_img_path(instance, filename):
    ext = filename.split('.')[-1]
    pk = instance.pk if instance.pk else "new"
    return os.path.join('assets', f"catalog_img_{pk}.{ext}")


class Manufacturer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(blank=True, verbose_name="Company Website")
    logo = models.ImageField(upload_to=manufacturer_logo_path, blank=True, null=True)

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


class AssetAttribute(models.Model):
    class AttributeType(models.TextChoices):
        STRING = 'str', 'Text'
        INTEGER = 'int', 'Whole Number'
        FLOAT = 'float', 'Decimal'
        BOOLEAN = 'bool', 'Yes / No'

    class UnitType(models.TextChoices):
        NONE = 'none', 'No Unit (Text/Bool/Int)'
        
        # --- 1D: Linear Dimensions ---
        LENGTH = 'autodesk.spec.aec:length-2.0.0', 'Length'
        DISTANCE = 'autodesk.spec.aec:distance-1.0.0', 'Distance'
        
        # --- 2D: Surfaces ---
        AREA = 'autodesk.spec.aec:area-2.0.0', 'Area'
        
        # --- 3D: Space & Mass ---
        VOLUME = 'autodesk.spec.aec:volume-2.0.0', 'Volume'
        MASS = 'autodesk.spec.aec:mass-2.0.0', 'Mass / Weight'
        DENSITY = 'autodesk.spec.aec:massDensity-2.0.0', 'Density'
        
        # --- Geometry / Orientation ---
        ANGLE = 'autodesk.spec.aec:angle-2.0.0', 'Angle'
        SLOPE = 'autodesk.spec.aec:slope-2.0.0', 'Slope'
        
        # --- Generic Numbers ---
        NUMBER = 'autodesk.spec.aec:number-2.0.0', 'Number (Unitless)'

    name = models.CharField(max_length=50,
                            unique=True,
                            help_text="Key name. Must be lowercase, use underscores, and have no special characters (e.g., 'material_finish').")
    data_type = models.CharField(
        max_length=10,
        choices=AttributeType.choices,
        default=AttributeType.STRING,
        help_text="Enforce a specific data type for this attribute"
    )
    unit_type = models.CharField(
        max_length=100,
        choices=UnitType.choices,
        default=UnitType.NONE,
        help_text="Revit SpecTypeId for unit conversion"
    )

    def clean(self):
        super().clean()
        # Enforce strict naming convention for the schema definition
        if not re.match(r'^[a-z0-9_]+$', self.name):
            raise ValidationError({
                'name': "Invalid format. Use lowercase, underscores, and alphanumeric characters only (e.g., 'asset_weight')."
            })

    def __str__(self):
        return f"{self.name} ({self.get_data_type_display()})"


class Asset(models.Model):
    unique_id = models.CharField(max_length=100, unique=True, verbose_name="Asset ID")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='assets')
    files = models.ManyToManyField(AssetFile, blank=True, related_name='assets')
    model = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(blank=True, verbose_name="Product URL")
    catalog_img = models.ImageField(upload_to=asset_catalog_img_path, blank=True, null=True)

    # Standard dimensions
    overall_height = models.FloatField(blank=True, null=True)
    overall_width = models.FloatField(blank=True, null=True)
    overall_depth = models.FloatField(blank=True, null=True)

    custom_fields = models.JSONField(default=dict, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)


    def clean(self):
        super().clean()
        if self.custom_fields:
            # Get all allowed attributes with their types
            defined_attributes = {attr.name: attr.data_type for attr in AssetAttribute.objects.all()}
            normalized_data = {}
        
            for key, value in self.custom_fields.items():
                # Normalize the key: 
                # 1. Lowercase
                # 2. Spaces to underscores
                # 3. Remove non-alphanumeric/underscore
                new_key = key.lower().strip().replace(' ', '_')
                new_key = re.sub(r'[^a-z0-9_]', '', new_key)

                # Check for collision within the input itself (e.g. "Height" and "height")
                if new_key in normalized_data:
                     raise ValidationError(f"Duplicate custom field detected: '{key}' conflicts with existing '{new_key}'.")

                # 1. Check if normalized key is allowed
                if new_key not in defined_attributes:
                    raise ValidationError(
                        f"Invalid custom field: '{key}' (normalized to '{new_key}'). Allowed fields are: {', '.join(sorted(defined_attributes.keys()))}"
                    )

                # 2. Check if value type matches the definition
                expected_type = defined_attributes[new_key]
                is_valid_type = True

                if expected_type == AssetAttribute.AttributeType.INTEGER:
                    # In Python, bool is a subclass of int, so we must explicitly exclude it
                    if isinstance(value, bool) or not isinstance(value, int):
                        is_valid_type = False
                elif expected_type == AssetAttribute.AttributeType.FLOAT:
                    if isinstance(value, bool) or not isinstance(value, (float, int)):
                        is_valid_type = False
                elif expected_type == AssetAttribute.AttributeType.BOOLEAN:
                    if not isinstance(value, bool):
                        is_valid_type = False
                elif expected_type == AssetAttribute.AttributeType.STRING:
                    if not isinstance(value, str):
                        is_valid_type = False
                
                if not is_valid_type:
                    raise ValidationError(
                        f"Invalid value for '{key}': Expected {expected_type}, got {type(value).__name__}"
                    )
                
                # Add to normalized dict
                normalized_data[new_key] = value
            
            # Replace the raw input with the normalized data
            self.custom_fields = normalized_data

    def __str__(self):
        return f"{self.manufacturer.name} {self.model} ({self.unique_id})"