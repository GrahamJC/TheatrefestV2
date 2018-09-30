from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserCreationForm, UserChangeForm
from .models import SiteInfo, Festival, User

# Register standard admins
admin.site.register(SiteInfo)
admin.site.register(Festival)

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'site', 'festival', 'is_active', 'is_admin', 'is_manager', 'is_box_office', 'is_volunteer')
    list_filter = ('site', 'festival', 'is_active', 'is_admin', 'is_manager', 'is_box_office', 'is_volunteer')
    ordering = ('site', 'festival', 'email')
    fieldsets = (
        (None, {'fields': ('site', 'festival', 'email', 'password', 'first_name', 'last_name', 'is_active')}),
        ('Permissions', {'fields': ('is_admin', 'is_manager', 'is_box_office', 'is_volunteer')}),
    )
    add_fieldsets = (
        (None, {'fields': ('site', 'festival', 'email', 'password1', 'password2', 'first_name', 'last_name')}),
    )
