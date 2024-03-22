from django.urls import path

from . import views

app_name = "venue"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:venue_uuid>', views.main, name = 'main'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>', views.main_performance, name = 'main_performance'),
    path('<uuid:venue_uuid>/performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>', views.main_performance_sale, name = 'main_performance_sale'),
    # Open/close checkpoint API
    path('performance/<uuid:performance_uuid>/open', views.performance_open, name = 'performance_open'),
    path('performance/<uuid:performance_uuid>/close', views.performance_close, name = 'performance_close'),
    path('checkpoint/<uuid:checkpoint_uuid>/update_open', views.checkpoint_update_open, name = 'checkpoint_update_open'),
    path('checkpoint/<uuid:checkpoint_uuid>/update_close', views.checkpoint_update_close, name = 'checkpoint_update_close'),
    # Sale API
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/select', views.sale_select, name = 'sale_select'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/close', views.sale_close, name = 'sale_close'),
    path('performance/<uuid:performance_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/items', views.sale_items, name = 'sale_items'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/payment/card', views.sale_payment_card, name = 'sale_payment_card'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/complete/zero', views.sale_complete_zero, name = 'sale_complete_zero'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    path('performance/<uuid:performance_uuid>/sale/<uuid:sale_uuid>/update', views.sale_update, name = 'sale_update'),
    # Tickets API
    path('performance/<uuid:performance_uuid>/tickets/refresh', views.tickets_refresh, name = 'tickets_refresh'),
    path('performance/<uuid:performance_uuid>/ticket/<uuid:ticket_uuid>/token', views.tickets_token, name = 'tickets_token'),
    path('performance/<uuid:performance_uuid>/badges', views.tickets_badges, name = 'tickets_badges'),
    path('performance/<uuid:performance_uuid>/tickets/print', views.tickets_print, name = 'tickets_print'),
    # Info API
    path('performance/<uuid:performance_uuid>/info', views.performance_info, name = 'performance_info'),
    # Square callback
    path('square/callback', views.square_callback, name='square_callback'),
]
