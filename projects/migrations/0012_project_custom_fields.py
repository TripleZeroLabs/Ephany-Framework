"""
Migration 0012: Move fc_id, ri_model, trackable_area_planned, trackable_area_designed,
vo_percentage, and vertical from dedicated columns into Project.custom_fields (JSONField).

Steps:
  1. Add custom_fields JSONField
  2. Copy existing column values into custom_fields (only non-empty values)
  3. Drop the six columns
"""

from django.db import migrations, models


def migrate_to_custom_fields(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    for project in Project.objects.all():
        cf = project.custom_fields or {}

        if project.fc_id:
            cf['fc_id'] = project.fc_id

        if project.ri_model:
            cf['ri_model'] = project.ri_model

        if project.trackable_area_planned is not None:
            cf['trackable_area_planned'] = float(project.trackable_area_planned)

        if project.trackable_area_designed is not None:
            cf['trackable_area_designed'] = float(project.trackable_area_designed)

        if project.vo_percentage is not None:
            cf['vo_percentage'] = project.vo_percentage

        if project.vertical:
            cf['vertical'] = project.vertical

        project.custom_fields = cf
        project.save(update_fields=['custom_fields'])


def reverse_migrate(apps, schema_editor):
    """Best-effort reverse: copy custom_fields values back into the columns."""
    Project = apps.get_model('projects', 'Project')
    for project in Project.objects.all():
        cf = project.custom_fields or {}
        project.fc_id = cf.get('fc_id', '')
        project.ri_model = cf.get('ri_model', '')
        project.trackable_area_planned = cf.get('trackable_area_planned')
        project.trackable_area_designed = cf.get('trackable_area_designed')
        project.vo_percentage = cf.get('vo_percentage')
        project.vertical = cf.get('vertical', '')
        project.save(update_fields=[
            'fc_id', 'ri_model', 'trackable_area_planned',
            'trackable_area_designed', 'vo_percentage', 'vertical',
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0011_site_project_address_line1_project_address_line2_and_more'),
    ]

    operations = [
        # 1. Add the new JSONField
        migrations.AddField(
            model_name='project',
            name='custom_fields',
            field=models.JSONField(blank=True, default=dict),
        ),

        # 2. Copy column data into custom_fields
        migrations.RunPython(migrate_to_custom_fields, reverse_code=reverse_migrate),

        # 3. Drop the six columns
        migrations.RemoveField(model_name='project', name='fc_id'),
        migrations.RemoveField(model_name='project', name='ri_model'),
        migrations.RemoveField(model_name='project', name='trackable_area_planned'),
        migrations.RemoveField(model_name='project', name='trackable_area_designed'),
        migrations.RemoveField(model_name='project', name='vo_percentage'),
        migrations.RemoveField(model_name='project', name='vertical'),
    ]
