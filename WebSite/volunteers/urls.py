from django.urls import path

from . import views

app_name = 'volunteers'

urlpatterns = [
    # Festival admin
    path('admin', views.admin, name='admin'),
    path('admin/roles', views.admin_roles, name='admin_roles'),
    path('admin/role/create', views.admin_role_create, name='admin_role_create'),
    path('admin/role/<uuid:role_uuid>/update', views.admin_role_update, name='admin_role_update'),
    path('admin/role/<uuid:role_uuid>/delete', views.admin_role_delete, name='admin_role_delete'),
    path('admin/locations', views.admin_locations, name='admin_locations'),
    path('admin/location/create', views.admin_location_create, name='admin_location_create'),
    path('admin/location/<uuid:location_uuid>/update', views.admin_location_update, name='admin_location_update'),
    path('admin/location/<uuid:location_uuid>/delete', views.admin_location_delete, name='admin_location_delete'),
    path('admin/volunteers', views.admin_volunteers, name='admin_volunteers'),
    path('admin/volunteer/autocomplete', views.VolunteerAutoComplete.as_view(), name='admin_volunteer_autocomplete'),
    path('admin/volunteer/<uuid:user_uuid>/update', views.admin_volunteer_update, name='admin_volunteer_update'),
    path('admin/volunteer/<uuid:user_uuid>/remove', views.admin_volunteer_remove, name='admin_volunteer_remove'),
    path('admin/shifts', views.admin_shifts, name='admin_shifts'),
    path('admin/shifts/<uuid:location_uuid>/<str:date>', views.admin_shifts, name='admin_shifts'),
    path('admin/shift/create', views.admin_shift_create, name='admin_shift_create'),
    path('admin/shift/create/<uuid:location_uuid>/<str:date>', views.admin_shift_create, name='admin_shift_create'),
    path('admin/shift/<uuid:shift_uuid>/update', views.admin_shift_update, name='admin_shift_update'),
    path('admin/shift/<uuid:shift_uuid>/delete', views.admin_shift_delete, name='admin_shift_delete'),
]
