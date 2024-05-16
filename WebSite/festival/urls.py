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
    path('admin/festival', views.AdminFestival.as_view(), name='admin_festival'),
    path('admin/tickettype/list', views.AdminTicketTypeList.as_view(), name='admin_tickettype_list'),
    path('admin/tickettype/create', views.AdminTicketTypeCreate.as_view(), name='admin_tickettype_create'),
    path('admin/tickettype/<uuid:slug>/update', views.AdminTicketTypeUpdate.as_view(), name='admin_tickettype_update'),
    path('admin/tickettype/<uuid:slug>/delete', views.admin_tickettype_delete, name='admin_tickettype_delete'),
    path('admin/fringertype/list', views.AdminFringerTypeList.as_view(), name='admin_fringertype_list'),
    path('admin/fringertype/create', views.AdminFringerTypeCreate.as_view(), name='admin_fringertype_create'),
    path('admin/fringertype/<uuid:slug>/update', views.AdminFringerTypeUpdate.as_view(), name='admin_fringertype_update'),
    path('admin/fringertype/<uuid:slug>/delete', views.admin_fringertype_delete, name='admin_fringertype_delete'),
    path('admin/user/list', views.admin_user_list, name='admin_user_list'),
    path('admin/user/<uuid:user_uuid>/activate', views.admin_user_activate, name='admin_user_activate'),
    path('admin/user/<uuid:user_uuid>/password', views.admin_user_password, name='admin_user_password'),
    path('admin/user/email', views.admin_user_email, name='admin_user_email'),
    path('admin/user/email/send', views.admin_user_email_send, name='admin_user_email_send'),
    path('admin/sale/list', views.AdminSaleListView.as_view(), name='admin_sale_list'),
    path('admin/sale/<uuid:sale_uuid>/confirmation/', views.admin_sale_confirmation, name='admin_sale_confirmation'),
    path('admin/bucket/list', views.AdminBucketList.as_view(), name='admin_bucket_list'),
    path('admin/bucket/create', views.AdminBucketCreate.as_view(), name='admin_bucket_create'),
    path('admin/bucket/<uuid:slug>/update', views.AdminBucketUpdate.as_view(), name='admin_bucket_update'),
    path('admin/bucket/<uuid:slug>/delete', views.admin_bucket_delete, name='admin_bucket_delete'),
    # AJAX support
    path('ajax/get_shows', views.ajax_get_shows, name='ajax_get_shows'),
    path('ajax/get_performances', views.ajax_get_performances, name='ajax_get_performances'),
]
