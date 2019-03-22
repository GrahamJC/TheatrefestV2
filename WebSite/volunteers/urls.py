from django.urls import path

from . import views

app_name = 'volunteers'

urlpatterns = [
    # Volunteers
    path('shift/list', views.shift_list, name='shift_list'),
    path('shift/<uuid:slug>/accept', views.shift_accept, name='shift_accept'),
    path('shift/<uuid:slug>/cancel', views.shift_cancel, name='shift_cancel'),
    # Festival admin
    path('admin/home', views.admin, name='admin_home'),
    path('admin/role/list', views.AdminRoleList.as_view(), name='admin_role_list'),
    path('admin/role/create', views.AdminRoleCreate.as_view(), name='admin_role_create'),
    path('admin/role/<uuid:slug>/update', views.AdminRoleUpdate.as_view(), name='admin_role_update'),
    path('admin/role/<uuid:slug>/delete', views.admin_role_delete, name='admin_role_delete'),
    path('admin/location/list', views.AdminLocationList.as_view(), name='admin_location_list'),
    path('admin/location/create', views.AdminLocationCreate.as_view(), name='admin_location_create'),
    path('admin/location/<uuid:slug>/update', views.AdminLocationUpdate.as_view(), name='admin_location_update'),
    path('admin/location/<uuid:slug>/delete', views.admin_location_delete, name='admin_location_delete'),
    path('admin/shift/list', views.AdminShiftList.as_view(), name='admin_shift_list'),
    path('admin/shifts/<uuid:location_uuid>/<str:date>', views.AdminShiftList.as_view(), name='admin_shift_list'),
    path('admin/shift/create', views.AdminShiftCreate.as_view(), name='admin_shift_create'),
    path('admin/shift/create/<uuid:location_uuid>/<str:date>', views.AdminShiftCreate.as_view(), name='admin_shift_create'),
    path('admin/shift/<uuid:slug>/update', views.AdminShiftUpdate.as_view(), name='admin_shift_update'),
    path('admin/shift/<uuid:slug>/delete', views.admin_shift_delete, name='admin_shift_delete'),
    path('admin/volunteers', views.admin_volunteers, name='admin_volunteers'),
    path('admin/volunteer/autocomplete', views.VolunteerAutoComplete.as_view(), name='admin_volunteer_autocomplete'),
    path('admin/volunteer/<uuid:slug>/update', views.AdminVolunteerUpdate.as_view(), name='admin_volunteer_update'),
    path('admin/volunteer/<uuid:slug>/remove', views.admin_volunteer_remove, name='admin_volunteer_remove'),
]
