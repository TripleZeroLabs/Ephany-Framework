from django.contrib import admin
from .models import Asset, AssetFile, Manufacturer


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('unique_id', 'manufacturer', 'model')
    search_fields = ('unique_id', 'model', 'manufacturer__name')
    filter_horizontal = ('files',)

@admin.register(AssetFile)
class AssetFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'category', 'uploaded_at')
    list_filter = ('category', 'uploaded_at')


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)