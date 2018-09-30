from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Content pages
    path('page/<uuid:page_uuid>', views.content_page, name='page'),
    # Festival admin
    path('admin', views.admin_home, name='admin_home'),
    path('admin/pages', views.admin_pages, name='admin_pages'),
    path('admin/page/create', views.admin_page_create, name='admin_page_create'),
    path('admin/page/update/<uuid:page_uuid>', views.admin_page_update, name='admin_page_update'),
    path('admin/page/delete/<uuid:page_uuid>', views.admin_page_delete, name='admin_page_delete'),
]
