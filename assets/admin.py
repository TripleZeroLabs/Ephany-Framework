from django.contrib import admin

from .models import Asset

# Register your models here.
@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    pass
