from django.contrib import admin
from .models import (
    Asset,
    AssetAttribute,
    AssetAttributeChoice,
    AssetCategory,
    AssetComponent,
    AssetFile,
    Manufacturer,
    Vendor,
    VendorProduct,
)


# --- INLINES ---

class VendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 1
    autocomplete_fields = ['vendor']


class AssetVendorProductInline(admin.TabularInline):
    model = VendorProduct
    extra = 1
    autocomplete_fields = ['vendor']


class AssetComponentInline(admin.TabularInline):
    model = AssetComponent
    fk_name = 'parent_asset'
    extra = 1
    autocomplete_fields = ['child_asset']
    verbose_name = "Component"
    verbose_name_plural = "Components"


class AssetAttributeChoiceInline(admin.TabularInline):
    model = AssetAttributeChoice
    extra = 3
    fields = ('value', 'order')
    ordering = ('order', 'value')


# --- ADMIN REGISTRATIONS ---

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('type_id', 'manufacturer', 'model', 'category', 'name')
    search_fields = ('type_id', 'model', 'manufacturer__name', 'name')
    list_filter = ('category', 'manufacturer')
    filter_horizontal = ('files',)
    inlines = [AssetComponentInline, AssetVendorProductInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'custom_fields' in form.base_fields:
            form.base_fields['custom_fields'].help_text = (
                "<strong>WARNING:</strong> All length/distance values in this JSON "
                "MUST be entered in <strong>MILLIMETERS</strong>. "
                "The API handles conversion, but this raw editor does not."
            )
        return form


@admin.register(AssetAttribute)
class AssetAttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'scope', 'data_type', 'unit_type', 'choice_count')
    list_filter = ('scope', 'data_type')
    search_fields = ('name',)
    ordering = ('name',)
    inlines = [AssetAttributeChoiceInline]

    def get_inline_instances(self, request, obj=None):
        choice_types = {
            AssetAttribute.AttributeType.CHOICE,
            AssetAttribute.AttributeType.MULTI_CHOICE,
        }
        if obj and obj.data_type in choice_types:
            return super().get_inline_instances(request, obj)
        return []

    def choice_count(self, obj):
        choice_types = {
            AssetAttribute.AttributeType.CHOICE,
            AssetAttribute.AttributeType.MULTI_CHOICE,
        }
        if obj.data_type in choice_types:
            return obj.choices.count()
        return '—'
    choice_count.short_description = 'Choices'


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
    inlines = [VendorProductInline]


@admin.register(AssetComponent)
class AssetComponentAdmin(admin.ModelAdmin):
    list_display = ('parent_asset', 'child_asset', 'quantity_required', 'can_add_per_instance')
    list_filter = ('parent_asset', 'can_add_per_instance')
    search_fields = ('parent_asset__name', 'parent_asset__type_id', 'child_asset__name', 'child_asset__type_id')
    autocomplete_fields = ['parent_asset', 'child_asset']


@admin.register(VendorProduct)
class VendorProductAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'asset', 'cost', 'lead_time_days', 'sku')
    list_filter = ('vendor',)
    search_fields = ('vendor__name', 'asset__name', 'sku')
    autocomplete_fields = ['asset', 'vendor']