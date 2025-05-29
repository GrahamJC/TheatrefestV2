from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    # Session
    path('debug', views.DebugFormView.as_view(), name='debug'),
    path('debug/clean_images', views.debug_clean_images, name='debug_clean_images'),
    path('debug/clean_cocuments', views.debug_clean_documents, name='debug_clean_documents'),
]
