from django.contrib import admin
from .models import Project, Site, Snapshot, AssetInstance, AssetComponentInstance


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('site_id', 'name', 'project_count', 'created_at')
    search_fields = ('site_id', 'name')

    def project_count(self, obj):
        return obj.projects.count()
    project_count.short_description = 'Projects'

class AssetInstanceInline(admin.TabularInline):
    model = AssetInstance
    extra = 0
    fields = ('instance_id', 'asset', 'location', 'custom_fields')


class AssetComponentInstanceInline(admin.TabularInline):
    """
    Allows editing optional AssetComponents directly inside the AssetInstance admin page.
    Note: Only optional components can be added (enforced by model validation).
    """
    model = AssetComponentInstance
    fk_name = 'asset_instance'
    extra = 1
    autocomplete_fields = ['asset_component']
    verbose_name = "Optional Component"
    verbose_name_plural = "Optional Components"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('asset_component', 'asset_component__child_asset')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter asset_component choices to only optional components for the parent asset_instance's asset."""
        if db_field.name == "asset_component":
            # Get the parent asset_instance from the inline
            if hasattr(self, 'parent_instance') and self.parent_instance:
                from assets.models import AssetComponent
                # Filter to only optional components belonging to this asset
                kwargs["queryset"] = AssetComponent.objects.filter(
                    parent_asset=self.parent_instance.asset,
                    can_add_per_instance=True
                )
            else:
                # If no parent instance, show only optional components
                from assets.models import AssetComponent
                kwargs["queryset"] = AssetComponent.objects.filter(can_add_per_instance=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'name', 'site', 'status', 'go_live_date', 'created_at')
    list_filter = ('status', 'site')
    search_fields = ('job_id', 'name', 'site__site_id')
    autocomplete_fields = ['site']

    fieldsets = (
        ('Identity', {
            'fields': ('job_id', 'name', 'description', 'portfolio_img', 'site'),
        }),
        ('Address', {
            'fields': (
                'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country',
                'latitude', 'longitude',
            ),
        }),
        ('Project Details', {
            'fields': ('go_live_date', 'status', 'custom_fields'),
        }),
    )

@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'date', 'created_at')
    list_filter = ('project', 'date')
    search_fields = ('name', 'project__name')
    inlines = [AssetInstanceInline]

@admin.register(AssetInstance)
class AssetInstanceAdmin(admin.ModelAdmin):
    list_display = ('asset', 'location', 'instance_id', 'get_project_name', 'snapshot')
    list_filter = ('snapshot__project', 'snapshot')
    search_fields = ('asset__name', 'instance_id', 'snapshot__name', 'snapshot__project__name')
    inlines = [AssetComponentInstanceInline]

    # Helper method to show project name in the list view
    def get_project_name(self, obj):
        return obj.snapshot.project.name
    get_project_name.short_description = 'Project'


@admin.register(AssetComponentInstance)
class AssetComponentInstanceAdmin(admin.ModelAdmin):
    """
    Standalone admin for asset component instances, useful for managing optional components.
    """
    list_display = ('asset_instance', 'asset_component', 'quantity', 'get_component_name')
    list_filter = ('asset_instance__snapshot__project', 'asset_instance__snapshot', 'asset_component')
    search_fields = (
        'asset_instance__asset__name',
        'asset_instance__instance_id',
        'asset_component__child_asset__name',
        'asset_component__child_asset__type_id'
    )
    autocomplete_fields = ['asset_instance']
    
    def get_component_name(self, obj):
        return obj.asset_component.child_asset.name
    get_component_name.short_description = 'Component'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'asset_instance',
            'asset_instance__asset',
            'asset_instance__snapshot',
            'asset_instance__snapshot__project',
            'asset_component',
            'asset_component__child_asset',
            'asset_component__parent_asset'
        )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter asset_component choices to only optional components for the selected asset_instance."""
        if db_field.name == "asset_component":
            # Try to get the asset_instance from the form data
            asset_instance_id = request.GET.get('asset_instance') or request.POST.get('asset_instance')
            if asset_instance_id:
                try:
                    from .models import AssetInstance
                    from assets.models import AssetComponent
                    asset_instance = AssetInstance.objects.get(pk=asset_instance_id)
                    # Filter to only optional components belonging to this asset
                    kwargs["queryset"] = AssetComponent.objects.filter(
                        parent_asset=asset_instance.asset,
                        can_add_per_instance=True
                    )
                except (AssetInstance.DoesNotExist, ValueError):
                    pass
            else:
                # If no asset_instance selected, show only optional components
                from assets.models import AssetComponent
                kwargs["queryset"] = AssetComponent.objects.filter(can_add_per_instance=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)