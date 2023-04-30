from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    # Session
    path('debug', views.DebugFormView.as_view(), name='debug'),
]
