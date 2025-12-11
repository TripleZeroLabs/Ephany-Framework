from django.contrib import admin
from .models import Asset, AssetAttribute, AssetCategory, AssetFile, Manufacturer


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'manufacturer', 'model')
    search_fields = ('type_id', 'model', 'manufacturer__name')
    filter_horizontal = ('files',)

    # ...
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['custom_fields'].help_text = (
            "<strong>WARNING:</strong> All length/distance values in this JSON "
            "MUST be entered in <strong>MILLIMETERS</strong>. "
            "The API handles conversion, but this raw editor does not."
        )
        return form


@admin.register(AssetAttribute)
class AssetAttributeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AssetCategory)
class AssetAttributeAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(AssetFile)
class AssetFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'category', 'uploaded_at')
    list_filter = ('category', 'uploaded_at')


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)