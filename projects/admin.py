from django.contrib import admin
from .models import Project, Snapshot

# Register your models here.
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'job_id')
    search_fields = ('name', 'job_id')

@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'date')
    list_filter = ('project', 'date')
    search_fields = ('name', 'project__name')
