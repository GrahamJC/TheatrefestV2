from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Festival archive
    path('archive/index', views.archive_index, name='archive_index'),
    path('archive/home', views.archive_home, name='archive_home'),
    path('archive/<festival_name>', views.archive_festival, name='archive_festival'),
    # Festival admin
    path('admin', views.admin, name='admin'),
    path('admin/user/list', views.admin_user_list, name='admin_user_list'),
    path('admin/user/<uuid:user_uuid>/activate', views.admin_user_activate, name='admin_user_activate'),
    path('admin/user/<uuid:user_uuid>/password', views.admin_user_password, name='admin_user_password'),
]
