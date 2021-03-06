from django.urls import path

from . import views

app_name = "venue"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:venue_uuid>', views.main, name = 'main'),
    path('performance/<uuid:performance_uuid>', views.performance, name = 'performance'),
    # Open/close checkpoint API
    path('performance/<uuid:performance_uuid>/open', views.performance_open, name = 'performance_open'),
    path('performance/<uuid:performance_uuid>/close', views.performance_close, name = 'performance_close'),
    path('checkpoint/<uuid:checkpoint_uuid>/update_open', views.checkpoint_update_open, name = 'checkpoint_update_open'),
    path('checkpoint/<uuid:checkpoint_uuid>/update_close', views.checkpoint_update_close, name = 'checkpoint_update_close'),
    # Sale API
    path('performance/<uuid:performance_uuid>/sale/new', views.sale_new, name = 'sale_new'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>', views.sale_select, name = 'sale_select'),
    path('performance/<uuid:performance_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/update', views.sale_update, name = 'sale_update'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    # Tickets API
    path('performance/<uuid:performance_uuid>/tickets/<str:format>', views.tickets, name = 'tickets'),
    # Info API
    path('performance/<uuid:performance_uuid>/info', views.performance_info, name = 'performance_info'),
]
