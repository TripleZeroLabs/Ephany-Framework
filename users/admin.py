from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserSettings

# Define an inline admin descriptor for UserSettings model
class UserSettingsInline(admin.StackedInline):
    model = UserSettings
    can_delete = False
    verbose_name_plural = 'User Settings'
    fk_name = 'user'

# Define a new User admin that just adds the inline
class UserAdmin(BaseUserAdmin):
    inlines = (UserSettingsInline,)
    
    # Optional: Keep the helpful column in the list view
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_length_unit')
    
    def get_length_unit(self, instance):
        if hasattr(instance, 'settings'):
            return instance.settings.get_length_unit_display()
        return '-'
    get_length_unit.short_description = 'Length Unit'

# Re-register UserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
    
admin.site.register(User, UserAdmin)


# Also register UserSettings separately if you want direct access
@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'length_unit', 'area_unit', 'mass_unit')
    search_fields = ('user__username', 'user__email')
