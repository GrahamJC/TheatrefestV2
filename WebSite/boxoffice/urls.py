from django.urls import path

from . import views

app_name = "boxoffice"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:boxoffice_uuid>', views.main, name = 'main'),
    path('<uuid:boxoffice_uuid>/tab/<str:tab>', views.main, name = 'main_tab'),
    # Sale AJAX support
    path('<uuid:boxoffice_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('sale/show/<uuid:show_uuid>', views.show_performances, name = 'show_performances'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/select', views.sale_show_select, name = 'sale_show_select'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/select', views.sale_performance_select, name = 'sale_performance_select'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/tickets/add', views.sale_tickets_add, name = 'sale_tickets_add'),
    path('sale/<uuid:sale_uuid>/extras/update', views.sale_extras_update, name = 'sale_extras_update'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/remove', views.sale_remove_performance, name = 'sale_remove_performance'),
    path('sale/<uuid:sale_uuid>/ticket/<uuid:ticket_uuid>/remove', views.sale_remove_ticket, name = 'sale_remove_ticket'),
    path('sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    path('sale/<uuid:sale_uuid>/close', views.sale_close, name = 'sale_close'),
    path('sale/<uuid:sale_uuid>/select', views.sale_select, name = 'sale_select'),
    path('sale/<uuid:sale_uuid>/report', views.sale_report, name = 'sale_report'),
    # Refund AJAX support
    path('<uuid:boxoffice_uuid>/refund', views.refund_start, name = 'refund_start'),
    path('refund/<uuid:refund_uuid>/ticket/add', views.refund_add_ticket, name = 'refund_ticket_add'),
    path('refund/<uuid:refund_uuid>/ticket/<uuid:ticket_uuid>/remove', views.refund_remove_ticket, name = 'refund_ticket_remove'),
    path('refund/<uuid:refund_uuid>/complete', views.refund_complete, name = 'refund_complete'),
    path('refund/<uuid:refund_uuid>/cancel', views.refund_cancel, name = 'refund_cancel'),
    path('refund/<uuid:refund_uuid>/update', views.refund_update, name = 'refund_update'),
    path('refund/<uuid:refund_uuid>/close', views.refund_close, name = 'refund_close'),
    path('refund/<uuid:refund_uuid>/select', views.refund_select, name = 'refund_select'),
    path('refund/<uuid:refund_uuid>/report', views.refund_report, name = 'refund_report'),
    # Checkpoints
    path('<uuid:boxoffice_uuid>/checkpoint/add', views.checkpoint_add, name = 'checkpoint_add'),
]
