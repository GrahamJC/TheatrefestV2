from django.urls import path

from . import views

app_name = "venue"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:venue_uuid>', views.main, name = 'main'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>', views.main, name = 'performance'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/open', views.performance_open, name = 'performance_open'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/close', views.performance_close, name = 'performance_close'),
    # Sale API
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/new', views.sale_new, name = 'sale_new'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>', views.sale_select, name = 'sale_select'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/update', views.sale_update, name = 'sale_update'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    # Tickets API
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/tickets', views.tickets, name = 'tickets'),
]
