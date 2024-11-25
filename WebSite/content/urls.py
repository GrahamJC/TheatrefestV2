from django.urls import path

from . import views

app_name = 'content'

urlpatterns = [
    # Pages
    path('page/<uuid:page_uuid>', views.page, name='page'),
    path('page/<uuid:page_uuid>/test', views.page_test, name='page_test'),
    path('page/<str:page_name>', views.page_name, name='page_name'),
    # Documents
    path('document/<uuid:document_uuid>', views.document, name='document'),
    # Resources
    path('resource/<uuid:resource_uuid>', views.resource, name='resource'),
    path('resource/<uuid:resource_uuid>/test', views.resource_test, name='resource_test'),
    # Administration
    path('admin/page/list', views.AdminPageList.as_view(), name='admin_page_list'),
    path('admin/page/create', views.AdminPageCreate.as_view(), name='admin_page_create'),
    path('admin/page/ccopy', views.admin_page_copy, name='admin_page_copy'),
    path('admin/page/<uuid:slug>/update', views.AdminPageUpdate.as_view(), name='admin_page_update'),
    path('admin/page/<uuid:slug>/update/<tab>', views.AdminPageUpdate.as_view(), name='admin_page_update_tab'),
    path('admin/page/<uuid:slug>/delete', views.admin_page_delete, name='admin_page_delete'),
    path('admin/page/<uuid:page_uuid>/image/create', views.AdminPageImageCreate.as_view(), name='admin_page_image_create'),
    path('admin/page/<uuid:page_uuid>/image/<uuid:slug>/update', views.AdminPageImageUpdate.as_view(), name='admin_page_image_update'),
    path('admin/page/<uuid:page_uuid>/image/<uuid:slug>/delete', views.admin_page_image_delete, name='admin_page_image_delete'),
    path('admin/navigator/list', views.AdminNavigatorList.as_view(), name='admin_navigator_list'),
    path('admin/navigator/create', views.AdminNavigatorCreate.as_view(), name='admin_navigator_create'),
    path('admin/navigator/copy', views.admin_navigator_copy, name='admin_navigator_copy'),
    path('admin/navigator/<uuid:slug>/update', views.AdminNavigatorUpdate.as_view(), name='admin_navigator_update'),
    path('admin/navigator/<uuid:slug>/delete', views.admin_navigator_delete, name='admin_navigator_delete'),
    path('admin/image/list', views.AdminImageList.as_view(), name='admin_image_list'),
    path('admin/image/create', views.AdminImageCreate.as_view(), name='admin_image_create'),
    path('admin/image/copy', views.admin_image_copy, name='admin_image_copy'),
    path('admin/image/<uuid:slug>/update', views.AdminImageUpdate.as_view(), name='admin_image_update'),
    path('admin/image/<uuid:slug>/delete', views.admin_image_delete, name='admin_image_delete'),
    path('admin/document/list', views.AdminDocumentList.as_view(), name='admin_document_list'),
    path('admin/document/create', views.AdminDocumentCreate.as_view(), name='admin_document_create'),
    path('admin/document/copy', views.admin_document_copy, name='admin_document_copy'),
    path('admin/document/<uuid:slug>/update', views.AdminDocumentUpdate.as_view(), name='admin_document_update'),
    path('admin/document/<uuid:slug>/delete', views.admin_document_delete, name='admin_document_delete'),
    path('admin/resource/list', views.AdminResourceList.as_view(), name='admin_resource_list'),
    path('admin/resource/create', views.AdminResourceCreate.as_view(), name='admin_resource_create'),
    path('admin/resource/copy', views.admin_resource_copy, name='admin_resource_copy'),
    path('admin/resource/<uuid:slug>/update', views.AdminResourceUpdate.as_view(), name='admin_resource_update'),
    path('admin/resource/<uuid:slug>/delete', views.admin_resource_delete, name='admin_resource_delete'),
]
