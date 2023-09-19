from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserCreationForm, AdminUserChangeForm
from .models import Festival, User

# Register standard admins
admin.site.register(Festival)

@admin.register(User)
class UserAdmin(BaseUserAdmin):

    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    search_fields = ['email']
    list_display = ('email', 'festival', 'is_active', 'is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')
    list_filter = ('festival', 'is_active', 'is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')
    ordering = ('festival', 'email')
    fieldsets = (
        (None, {'fields': ('festival', 'email', 'password', 'first_name', 'last_name', 'is_active')}),
        ('Permissions', {'fields': ('is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer')}),
    )
    add_fieldsets = (
        (None, {'fields': ('festival', 'email', 'password1', 'password2', 'first_name', 'last_name')}),
    )

    def get_search_results(self, request, queryset, search_term):
        return super().get_search_results(request, queryset.filter(festival = request.festival), search_term)