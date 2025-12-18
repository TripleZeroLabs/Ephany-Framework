from django.contrib import admin
from .models import Project, Snapshot, AssetInstance

class AssetInstanceInline(admin.TabularInline):
    model = AssetInstance
    extra = 0
    # We removed lineage_id, so we only show the core fields here
    fields = ('asset', 'custom_fields')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'name', 'created_at', 'updated_at')
    search_fields = ('job_id', 'name')

@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    # Removed 'is_locked' as it is not in your current model
    list_display = ('name', 'project', 'date', 'created_at')
    list_filter = ('project', 'date')
    search_fields = ('name', 'project__name')
    inlines = [AssetInstanceInline]

@admin.register(AssetInstance)
class AssetInstanceAdmin(admin.ModelAdmin):
    # Removed 'location' because that now lives inside the 'custom_fields' JSON
    list_display = ('asset', 'get_project_name', 'snapshot', 'created_at')
    list_filter = ('snapshot__project', 'snapshot')
    search_fields = ('asset__name', 'snapshot__name', 'snapshot__project__name')

    # Helper method to show project name in the list view
    def get_project_name(self, obj):
        return obj.snapshot.project.name
    get_project_name.short_description = 'Project'