from django.contrib import admin
from .models import (
    Asset,
    AssetAttribute,
    AssetCategory,
    AssetFile,
    Manufacturer,
    Vendor,
    VendorProduct
)


# --- INLINES ---

class VendorProductInline(admin.TabularInline):
    """
    Allows editing Vendor Products directly inside the Asset or Vendor admin pages.
    """
    model = VendorProduct
    extra = 1
    autocomplete_fields = ['vendor']


class AssetVendorProductInline(admin.TabularInline):
    """
    Inverse inline: View all vendors selling this specific Asset.
    """
    model = VendorProduct
    extra = 1
    autocomplete_fields = ['vendor']


# --- ADMIN REGISTRATIONS ---

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'manufacturer', 'model', 'category')
    search_fields = ('type_id', 'model', 'manufacturer__name', 'name')
    list_filter = ('category', 'manufacturer')
    filter_horizontal = ('files',)

    # Shows which vendors sell this asset directly on the Asset page
    inlines = [AssetVendorProductInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Ensure custom_fields help text is safe HTML
        if 'custom_fields' in form.base_fields:
            form.base_fields['custom_fields'].help_text = (
                "<strong>WARNING:</strong> All length/distance values in this JSON "
                "MUST be entered in <strong>MILLIMETERS</strong>. "
                "The API handles conversion, but this raw editor does not."
            )
        return form


@admin.register(AssetAttribute)
class AssetAttributeAdmin(admin.ModelAdmin):
    # Added 'scope' to visibility
    list_display = ('name', 'scope', 'data_type', 'unit_type')
    list_filter = ('scope', 'data_type', 'unit_type')
    search_fields = ('name',)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(AssetFile)
class AssetFileAdmin(admin.ModelAdmin):
    list_display = ('file', 'category', 'uploaded_at')
    list_filter = ('category', 'uploaded_at')
    search_fields = ('file',)


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')
    search_fields = ('name',)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'contact_email')
    search_fields = ('name',)
    # Allows adding products directly from the Vendor page
    inlines = [VendorProductInline]


@admin.register(VendorProduct)
class VendorProductAdmin(admin.ModelAdmin):
    """
    Standalone admin for the join table, useful for searching prices across the board.
    """
    list_display = ('vendor', 'asset', 'cost', 'lead_time_days', 'sku')
    list_filter = ('vendor',)
    search_fields = ('vendor__name', 'asset__name', 'sku')
    autocomplete_fields = ['asset', 'vendor']