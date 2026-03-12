from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    # Admin
    path('admin', views.admin, name='admin'),
    path('admin/festival/list', views.AdminFestivalList.as_view(), name='admin_festival_list'),
    path('admin/festival/<uuid:slug>/live', views.admin_festival_live, name='admin_festival_live'),
    path('admin/festival/<uuid:slug>/enable', views.admin_festival_enable, name='admin_festival_enable'),
    path('admin/festival/disable', views.admin_festival_disable, name='admin_festival_disable'),
    path('admin/festival/create', views.AdminFestivalCreate.as_view(), name='admin_festival_create'),
    path('admin/festival/<uuid:slug>/update', views.AdminFestivalUpdate.as_view(), name='admin_festival_update'),
    path('admin/festival/<uuid:slug>/delete', views.admin_festival_delete, name='admin_festival_delete'),
    # Debug
    path('debug', views.DebugFormView.as_view(), name='debug'),
    path('debug/clean_images', views.debug_clean_images, name='debug_clean_images'),
    path('debug/clean_cocuments', views.debug_clean_documents, name='debug_clean_documents'),
]
