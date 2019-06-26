from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserCreationForm, AdminUserChangeForm
from .models import SiteInfo, Festival, User

# Register standard admins
admin.site.register(SiteInfo)
admin.site.register(Festival)

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('email', 'site', 'festival', 'is_active', 'is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')
    list_filter = ('site', 'festival', 'is_active', 'is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')
    ordering = ('site', 'festival', 'email')
    fieldsets = (
        (None, {'fields': ('site', 'festival', 'email', 'password', 'first_name', 'last_name', 'is_active')}),
        ('Permissions', {'fields': ('is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')}),
    )
    add_fieldsets = (
        (None, {'fields': ('site', 'festival', 'email', 'password1', 'password2', 'first_name', 'last_name')}),
    )
