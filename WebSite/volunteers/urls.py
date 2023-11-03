from django.urls import path

from . import views

app_name = 'volunteers'

urlpatterns = [
    # Volunteers
    path('shift/list', views.shift_list, name='shift_list'),
    path('shift/<uuid:slug>/accept', views.shift_accept, name='shift_accept'),
    path('shift/<uuid:slug>/cancel', views.shift_cancel, name='shift_cancel'),
    # Admin: Home
    path('admin/home', views.admin, name='admin_home'),
    # Admin: Roles
    path('admin/role/list', views.AdminRoleList.as_view(), name='admin_role_list'),
    path('admin/role/create', views.AdminRoleCreate.as_view(), name='admin_role_create'),
    path('admin/role/<uuid:slug>/update', views.AdminRoleUpdate.as_view(), name='admin_role_update'),
    path('admin/role/<uuid:slug>/delete', views.admin_role_delete, name='admin_role_delete'),
    # Admin: Locations
    path('admin/location/list', views.AdminLocationList.as_view(), name='admin_location_list'),
    path('admin/location/create', views.AdminLocationCreate.as_view(), name='admin_location_create'),
    path('admin/location/<uuid:slug>/update', views.AdminLocationUpdate.as_view(), name='admin_location_update'),
    path('admin/location/<uuid:slug>/delete', views.admin_location_delete, name='admin_location_delete'),
    # Admin: Commitmwents
    path('admin/commitment/list', views.AdminCommitmentList.as_view(), name='admin_commitment_list'),
    path('admin/commitment/create', views.AdminCommitmentCreate.as_view(), name='admin_commitment_create'),
    path('admin/commitment/<uuid:slug>/update', views.AdminCommitmentUpdate.as_view(), name='admin_commitment_update'),
    path('admin/commitment/<uuid:slug>/update/<str:tab>', views.AdminCommitmentUpdate.as_view(), name='admin_commitment_update_tab'),
    path('admin/commitment/<uuid:slug>/delete', views.admin_commitment_delete, name='admin_commitment_delete'),
    path('admin/commitment/<uuid:commitment_uuid>/shift/create', views.AdminCommitmentShiftCreate.as_view(), name='admin_commitment_shift_create'),
    path('admin/commitment/<uuid:commitment_uuid>/shift/<uuid:slug>/update', views.AdminCommitmentShiftUpdate.as_view(), name='admin_commitment_shift_update'),
    path('admin/commitment/<uuid:commitment_uuid>/shift/<uuid:slug>/delete', views.admin_commitment_shift_delete, name='admin_commitment_shift_delete'),
    # Admin: Shifts
    path('admin/shift/list', views.AdminShiftList.as_view(), name='admin_shift_list'),
    path('admin/shift/create', views.AdminShiftCreate.as_view(), name='admin_shift_create'),
    path('admin/shift/<uuid:slug>/update', views.AdminShiftUpdate.as_view(), name='admin_shift_update'),
    path('admin/shift/<uuid:slug>/delete', views.admin_shift_delete, name='admin_shift_delete'),
    # Admin: Volunteers
    path('admin/volunteers', views.admin_volunteers, name='admin_volunteers'),
    path('admin/volunteer/autocomplete', views.AdminVolunteerAutoComplete.as_view(), name='admin_volunteer_autocomplete'),
    path('admin/volunteer/<uuid:slug>/update', views.AdminVolunteerUpdate.as_view(), name='admin_volunteer_update'),
    path('admin/volunteer/<uuid:slug>/remove', views.admin_volunteer_remove, name='admin_volunteer_remove'),
]
