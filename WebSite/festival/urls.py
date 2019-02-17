from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Festival admin
    path('admin', views.admin, name='admin'),
]
