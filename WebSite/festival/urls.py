from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Festival archive
    path('archive/index', views.archive_index, name='archive_index'),
    path('archive/home', views.archive_home, name='archive_home'),
    path('archive/<festival_name>', views.archive_festival, name='archive_festival'),
    # Festival test
    path('switch', views.switch, name='switch'),
    path('switch/<name>', views.switch, name='switch_name'),
    # Festival admin
    path('admin', views.admin, name='admin'),
    path('admin/setup', views.AdminSetupView.as_view(), name='admin_setup'),
    path('admin/user/list', views.admin_user_list, name='admin_user_list'),
    path('admin/user/<uuid:user_uuid>/activate', views.admin_user_activate, name='admin_user_activate'),
    path('admin/user/<uuid:user_uuid>/password', views.admin_user_password, name='admin_user_password'),
    path('admin/user/email', views.admin_user_email, name='admin_user_email'),
    path('admin/user/email/send', views.admin_user_email_send, name='admin_user_email_send'),
    path('admin/sale/list', views.AdminSaleListView.as_view(), name='admin_sale_list'),
    path('admin/sale/<uuid:sale_uuid>/confirmation/', views.admin_sale_confirmation, name='admin_sale_confirmation'),
]
