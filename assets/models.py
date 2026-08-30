import os
import re
from django.db import models
from django.core.exceptions import ValidationError


def manufacturer_logo_path(instance, filename):
    """
    Generates the storage path for manufacturer logos.
    Renames file to: manufacturers/logo_<pk>.<ext>
    """
    ext = filename.split('.')[-1]
    pk = str(instance.pk) if instance.pk else "new"
    return os.path.join('manufacturers', f"logo_{pk}.{ext}")


def asset_catalog_img_path(instance, filename):
    """
    Generates the storage path for asset catalog images.
    Structure: assets/<asset_pk>/<original_filename>

    Preserves the original filename to facilitate scaling and external file management.
    """
    pk = str(instance.pk) if instance.pk else "new"
    return os.path.join('assets', pk, filename)


class Manufacturer(models.Model):
    """
    Represents the manufacturer of an asset.
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.URLField(blank=True, verbose_name="Company Website")
    logo = models.ImageField(upload_to=manufacturer_logo_path, blank=True, null=True)

    class Meta:
        # name is unique, so this is already a total order.
        ordering = ['name']

    def __str__(self):
        return self.name


class AssetFile(models.Model):
    """
    Represents external files associated with an asset, such as datasheets,
    CAD drawings, or BIM families.
    """

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

    class Meta:
        verbose_name_plural = "Asset Files"
        # Ends in a unique field so pagination cannot repeat or drop rows.
        ordering = ['-uploaded_at', 'id']

    def __str__(self):
        return f"{self.get_category_display()}: {self.file.name}"


class AssetCategory(models.Model):
    """
    High-level categorization for organizing assets (e.g., Refrigerators, Ovens, Sinks).
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Asset Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class AssetAttribute(models.Model):
    """
    Defines the schema for dynamic 'custom_fields' on Assets.
    Enforces data types and units for interoperability with external tools like Revit.
    """

    class AttributeType(models.TextChoices):
        STRING = 'str', 'Text'
        INTEGER = 'int', 'Whole Number'
        FLOAT = 'float', 'Decimal'
        BOOLEAN = 'bool', 'Yes / No'
        CHOICE = 'choice', 'Picklist (Single)'
        MULTI_CHOICE = 'multi_choice', 'Picklist (Multiple)'

    class UnitType(models.TextChoices):
        """
        Maps to Autodesk Revit SpecTypeIds for automatic unit conversion.
        """
        NONE = 'none', 'No Unit (Text/Bool/Int)'

        # 1D: Linear Dimensions
        LENGTH = 'autodesk.spec.aec:length-2.0.0', 'Length'
        DISTANCE = 'autodesk.spec.aec:distance-1.0.0', 'Distance'

        # 2D: Surfaces
        AREA = 'autodesk.spec.aec:area-2.0.0', 'Area'

        # 3D: Space & Mass
        VOLUME = 'autodesk.spec.aec:volume-2.0.0', 'Volume'
        MASS = 'autodesk.spec.aec:mass-2.0.0', 'Mass / Weight'
        DENSITY = 'autodesk.spec.aec:massDensity-2.0.0', 'Density'

        # Geometry / Orientation
        ANGLE = 'autodesk.spec.aec:angle-2.0.0', 'Angle'
        SLOPE = 'autodesk.spec.aec:slope-2.0.0', 'Slope'

        # Generic
        NUMBER = 'autodesk.spec.aec:number-2.0.0', 'Number (Unitless)'

    class AttributeScope(models.TextChoices):
        TYPE = 'type', 'Asset Type (Catalog)'  # e.g., Voltage, Manufacturer Warranty
        INSTANCE = 'instance', 'Asset Instance (Project)'  # e.g., Serial Number, Install Date
        BOTH = 'both', 'Both'

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Key name. Must be lowercase, use underscores, and have no special characters (e.g., 'material_finish')."
    )

    scope = models.CharField(
        max_length=20,
        choices=AttributeScope.choices,
        default=AttributeScope.TYPE,
        help_text="Determines if this field appears on the generic Catalog definition or the specific Project Instance."
    )

    data_type = models.CharField(
        max_length=20,
        choices=AttributeType.choices,
        default=AttributeType.STRING,
        help_text="Enforce a specific data type for this attribute."
    )

    unit_type = models.CharField(
        max_length=100,
        choices=UnitType.choices,
        default=UnitType.NONE,
        help_text="Revit SpecTypeId for unit conversion."
    )

    def clean(self):
        super().clean()
        # Enforce strict naming convention for the schema definition to ensure API compatibility
        if not re.match(r'^[a-z0-9_]+$', self.name):
            raise ValidationError({
                'name': "Invalid format. Use lowercase, underscores, and alphanumeric characters only (e.g., 'asset_weight')."
            })

    def save(self, *args, **kwargs):
        if self.pk:
            previous = AssetAttribute.objects.filter(pk=self.pk).values_list('data_type', flat=True).first()
            choice_types = {AssetAttribute.AttributeType.CHOICE, AssetAttribute.AttributeType.MULTI_CHOICE}
            if previous in choice_types and self.data_type not in choice_types:
                self.choices.all().delete()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Asset Attributes"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_scope_display()})"


class AssetAttributeChoice(models.Model):
    """
    Defines allowed choices for an AssetAttribute of type 'choice'.
    """
    attribute = models.ForeignKey(
        AssetAttribute,
        on_delete=models.CASCADE,
        related_name='choices',
        verbose_name="Asset Attribute"
    )
    value = models.CharField(
        max_length=255,
        help_text="Allowed value for this attribute. Must be unique within this attribute.",
        verbose_name="Choice Value"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order of this choice in the picklist (lower numbers appear first)."
    )

    class Meta:
        unique_together = ['attribute', 'value']
        verbose_name = "Asset Attribute Choice"
        verbose_name_plural = "Asset Attribute Choices"
        # unique_together already makes this total; id is here so the rule
        # "ordering ends in a unique field" holds for every model without
        # having to reason about it.
        ordering = ['attribute', 'order', 'value', 'id']

    def clean(self):
        super().clean()
        choice_types = {AssetAttribute.AttributeType.CHOICE, AssetAttribute.AttributeType.MULTI_CHOICE}
        if self.attribute_id and self.attribute.data_type not in choice_types:
            raise ValidationError(
                f"Choices can only be added to attributes with data type 'Picklist (Single)' or 'Picklist (Multiple)'. "
                f"'{self.attribute.name}' is of type '{self.attribute.get_data_type_display()}'."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class AssetComponent(models.Model):
    """
    Through model for Asset assemblies.
    Represents a component (child asset) that is part of an assembly (parent asset).
    Includes quantity to specify how many of each component are needed.
    Components can be marked as optional (e.g., shelves that can be added per AssetInstance)
    or required (e.g., bolts that are always needed).
    """
    parent_asset = models.ForeignKey(
        'Asset',
        on_delete=models.CASCADE,
        related_name='components',
        verbose_name="Parent Asset (Assembly)"
    )
    child_asset = models.ForeignKey(
        'Asset',
        on_delete=models.CASCADE,
        related_name='used_in_assemblies',
        verbose_name="Child Asset (Component)"
    )
    quantity_required = models.PositiveIntegerField(
        default=1,
        help_text="Number of this component needed in the assembly"
    )
    can_add_per_instance = models.BooleanField(
        default=False,
        help_text="If true, this component can have additional quantities added per AssetInstance (project-level)."
    )

    class Meta:
        unique_together = ['parent_asset', 'child_asset']
        verbose_name = "Asset Component"
        verbose_name_plural = "Asset Components"
        ordering = ['parent_asset', 'child_asset']

    def clean(self):
        """Prevent an asset from being a component of itself."""
        super().clean()
        if self.parent_asset and self.child_asset:
            # Check if they're the same object (by pk or by reference)
            if (self.parent_asset.pk and self.child_asset.pk and 
                self.parent_asset.pk == self.child_asset.pk):
                raise ValidationError({
                    'child_asset': 'An asset cannot be a component of itself.'
                })
            # Also check if they're the same object instance (for unsaved objects)
            elif self.parent_asset is self.child_asset:
                raise ValidationError({
                    'child_asset': 'An asset cannot be a component of itself.'
                })

    def save(self, *args, **kwargs):
        """Override save to run clean validation."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        optional_text = " (optional)" if self.can_add_per_instance else ""
        return f"{self.parent_asset.name} → {self.child_asset.name} (x{self.quantity_required}){optional_text}"


class Asset(models.Model):
    """
    The core product entity in the catalog.
    Supports dynamic extensibility via 'custom_fields' validated against AssetAttribute definitions.
    Can be an assembly containing other assets as components.
    """
    type_id = models.CharField(max_length=100, unique=True, verbose_name="Type ID")
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.CASCADE, related_name='assets')
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assets'
    )
    files = models.ManyToManyField(AssetFile, blank=True, related_name='assets')
    # Assembly relationship: assets can contain other assets as components
    component_assets = models.ManyToManyField(
        'self',
        through='AssetComponent',
        through_fields=('parent_asset', 'child_asset'),
        symmetrical=False,
        blank=True,
        related_name='parent_assemblies',
        verbose_name="Component Assets",
        help_text="Assets that are components of this assembly"
    )

    model = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=False)
    description = models.TextField(blank=True, null=True)
    url = models.URLField(blank=True, verbose_name="Product URL")

    # Image storage path uses the asset ID for organization
    catalog_img = models.ImageField(upload_to=asset_catalog_img_path, blank=True, null=True)

    # Standard dimensions (normalized to base units, typically meters or millimeters)
    overall_height = models.FloatField(blank=True, null=True)
    overall_width = models.FloatField(blank=True, null=True)
    overall_depth = models.FloatField(blank=True, null=True)

    custom_fields = models.JSONField(default=dict, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ends in a unique field so pagination cannot repeat or drop rows.
        ordering = ['name', 'type_id']

    def clean(self):
        """
        Validates 'custom_fields' against the defined AssetAttribute schema.
        Normalizes keys to snake_case and ensures value types match definitions.
        """
        super().clean()
        if self.custom_fields:
            # Cache allowed attributes for validation
            defined_attributes = {attr.name: attr.data_type for attr in AssetAttribute.objects.all()}
            normalized_data = {}

            for key, value in self.custom_fields.items():
                # Normalize key: lowercase, snake_case, alphanumeric only
                new_key = key.lower().strip().replace(' ', '_')
                new_key = re.sub(r'[^a-z0-9_]', '', new_key)

                # Prevent duplicates caused by normalization (e.g., "Weight" vs "weight")
                if new_key in normalized_data:
                    raise ValidationError(
                        f"Duplicate custom field detected: '{key}' conflicts with existing '{new_key}'.")

                # Verify key exists in schema
                if new_key not in defined_attributes:
                    raise ValidationError(
                        f"Invalid custom field: '{key}' (normalized to '{new_key}'). Allowed fields are: {', '.join(sorted(defined_attributes.keys()))}"
                    )

                # Verify value type matches schema
                expected_type = defined_attributes[new_key]
                is_valid_type = True

                # Strict type checking (rejecting bools where numbers are expected)
                if expected_type == AssetAttribute.AttributeType.INTEGER:
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
                elif expected_type == AssetAttribute.AttributeType.CHOICE:
                    if not isinstance(value, str):
                        is_valid_type = False
                    else:
                        allowed_values = list(
                            AssetAttributeChoice.objects
                            .filter(attribute__name=new_key)
                            .values_list('value', flat=True)
                        )
                        if value not in allowed_values:
                            raise ValidationError(
                                f"Invalid choice for '{key}': '{value}' is not an allowed value. "
                                f"Allowed values are: {', '.join(sorted(allowed_values))}"
                            )
                elif expected_type == AssetAttribute.AttributeType.MULTI_CHOICE:
                    if not isinstance(value, list):
                        is_valid_type = False
                    else:
                        allowed_values = list(
                            AssetAttributeChoice.objects
                            .filter(attribute__name=new_key)
                            .values_list('value', flat=True)
                        )
                        invalid = [v for v in value if v not in allowed_values]
                        if invalid:
                            raise ValidationError(
                                f"Invalid choices for '{key}': {invalid} are not allowed. "
                                f"Allowed values are: {', '.join(sorted(allowed_values))}"
                            )

                if not is_valid_type:
                    raise ValidationError(
                        f"Invalid value for '{key}': Expected {expected_type}, got {type(value).__name__}"
                    )

                normalized_data[new_key] = value

            self.custom_fields = normalized_data

    def __str__(self):
        return f"{self.manufacturer.name} {self.model} ({self.type_id})"


class Vendor(models.Model):
    """
    Represents a third-party supplier or distributor.
    """
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)

    class Meta:
        # Ends in a unique field so pagination cannot repeat or drop rows.
        ordering = ['name', 'id']

    def __str__(self):
        return self.name


class VendorProduct(models.Model):
    """
    Represents the commercial details of an Asset when sold by a specific Vendor.
    Allows for multiple vendors to sell the same base Asset at different prices/SKUs.
    """
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='vendor_products')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')

    sku = models.CharField(max_length=100, blank=True, help_text="Vendor's internal SKU")
    cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Current market price")
    lead_time_days = models.PositiveIntegerField(default=0, help_text="Estimated lead time in days")

    url = models.URLField(blank=True)

    class Meta:
        unique_together = ['asset', 'vendor']
        verbose_name = "Vendor Product"
        verbose_name_plural = "Vendor Products"
        # No meaningful display order; id keeps it stable without adding joins.
        ordering = ['id']

    def __str__(self):
        return f"{self.vendor.name} - {self.asset.name} (${self.cost})"