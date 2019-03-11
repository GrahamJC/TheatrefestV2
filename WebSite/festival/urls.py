from django.urls import path

from . import views

app_name = 'festival'

urlpatterns = [
    # Festival archive
    path('archive/index', views.archive_index, name='archive_index'),
    path('archive/home', views.archive_home, name='archive_home'),
    path('archive/<festival_name>', views.archive_festival, name='archive_festival'),
    # Festival admin
    path('admin', views.admin, name='admin'),
]
