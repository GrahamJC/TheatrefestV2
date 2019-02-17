from django.urls import path

from . import views

app_name = 'content'

urlpatterns = [
    # Pages
    path('page/<uuid:page_uuid>', views.page, name='page'),
    path('page/<uuid:page_uuid>/test', views.page_test, name='page_test'),
    # Documents
    path('document/<uuid:document_uuid>', views.document, name='document'),
    # Administration
    path('admin/pages', views.AdminPageList.as_view(), name='admin_pages'),
    path('admin/page/create', views.AdminPageCreate.as_view(), name='admin_page_create'),
    path('admin/page/<uuid:slug>/update', views.AdminPageUpdate.as_view(), name='admin_page_update'),
    path('admin/page/<uuid:slug>/update/<tab>', views.AdminPageUpdate.as_view(), name='admin_page_update_tab'),
    path('admin/page/<uuid:slug>/delete', views.admin_page_delete, name='admin_page_delete'),
    path('admin/page/<uuid:page_uuid>/image/create', views.AdminPageImageCreate.as_view(), name='admin_page_image_create'),
    path('admin/page/<uuid:page_uuid>/image/<uuid:slug>/update', views.AdminPageImageUpdate.as_view(), name='admin_page_image_update'),
    path('admin/page/<uuid:page_uuid>/image/<uuid:slug>/delete', views.admin_page_image_delete, name='admin_page_image_delete'),
    path('admin/navigators', views.AdminNavigatorList.as_view(), name='admin_navigators'),
    path('admin/navigator/create', views.AdminNavigatorCreate.as_view(), name='admin_navigator_create'),
    path('admin/navigator/<uuid:slug>/update', views.AdminNavigatorUpdate.as_view(), name='admin_navigator_update'),
    path('admin/navigator/<uuid:slug>/delete', views.admin_navigator_delete, name='admin_navigator_delete'),
    path('admin/images', views.AdminImageList.as_view(), name='admin_images'),
    path('admin/image/create', views.AdminImageCreate.as_view(), name='admin_image_create'),
    path('admin/image/<uuid:slug>/update', views.AdminImageUpdate.as_view(), name='admin_image_update'),
    path('admin/image/<uuid:slug>/delete', views.admin_image_delete, name='admin_image_delete'),
    path('admin/documents', views.AdminDocumentList.as_view(), name='admin_documents'),
    path('admin/document/create', views.AdminDocumentCreate.as_view(), name='admin_document_create'),
    path('admin/document/<uuid:slug>/update', views.AdminDocumentUpdate.as_view(), name='admin_document_update'),
    path('admin/document/<uuid:slug>/delete', views.admin_document_delete, name='admin_document_delete'),
]
