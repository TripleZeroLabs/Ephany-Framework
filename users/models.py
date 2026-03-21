from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserSettings(models.Model):
    """
    Stores global settings and preferences for a user.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings')

    # --- Unit Preferences ---
    class LengthUnit(models.TextChoices):
        MILLIMETER = 'mm', 'Millimeters (mm)'
        CENTIMETER = 'cm', 'Centimeters (cm)'
        METER = 'm', 'Meters (m)'
        INCH = 'in', 'Inches (in)'
        FOOT = 'ft', 'Feet (ft)'

    class AreaUnit(models.TextChoices):
        SQUARE_METER = 'sq_m', 'Square Meters (m²)'
        SQUARE_FOOT = 'sq_ft', 'Square Feet (ft²)'

    class VolumeUnit(models.TextChoices):
        CUBIC_METER = 'cu_m', 'Cubic Meters (m³)'
        CUBIC_FOOT = 'cu_ft', 'Cubic Feet (ft³)'

    class MassUnit(models.TextChoices):
        KILOGRAM = 'kg', 'Kilograms (kg)'
        POUND = 'lb', 'Pounds (lb)'

    length_unit = models.CharField(
        max_length=10, 
        choices=LengthUnit.choices, 
        default=LengthUnit.MILLIMETER
    )
    area_unit = models.CharField(
        max_length=10, 
        choices=AreaUnit.choices, 
        default=AreaUnit.SQUARE_METER
    )
    volume_unit = models.CharField(
        max_length=10, 
        choices=VolumeUnit.choices, 
        default=VolumeUnit.CUBIC_METER
    )
    mass_unit = models.CharField(
        max_length=10, 
        choices=MassUnit.choices, 
        default=MassUnit.KILOGRAM
    )

    def __str__(self):
        return f"Settings for {self.user}"


# Signal to auto-create settings when a User is created
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_settings(sender, instance, created, **kwargs):
    if created:
        # Use get_or_create to prevent race conditions with Admin Inlines
        UserSettings.objects.get_or_create(user=instance)
