from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Festival admin
    path('admin', views.admin, name='admin'),
    path('admin/pages', views.admin_pages, name='admin_pages'),
    path('admin/page/create', views.admin_page_create, name='admin_page_create'),
    path('admin/page/<uuid:page_uuid>/update', views.admin_page_update, name='admin_page_update'),
    path('admin/page/<uuid:page_uuid>/delete', views.admin_page_delete, name='admin_page_delete'),
    path('admin/navigators', views.admin_navigators, name='admin_navigators'),
    path('admin/navigator/create', views.admin_navigator_create, name='admin_navigator_create'),
    path('admin/navigator/<uuid:navigator_uuid>/update', views.admin_navigator_update, name='admin_navigator_update'),
    path('admin/navigator/<uuid:navigator_uuid>/delete', views.admin_navigator_delete, name='admin_navigator_delete'),
]
