from django.urls import path

from . import views

app_name = "boxoffice"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:boxoffice_uuid>', views.main, name = 'main'),
    path('<uuid:boxoffice_uuid>/tab/<str:tab>', views.main, name = 'main'),
    # Sale AJAX support
    path('<uuid:boxoffice_uuid>/sale', views.sale_start, name = 'sale_start'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/performances', views.sale_show_performances, name = 'sale_show_performances'),
    path('sale/<uuid:sale_uuid>/add/tickets', views.sale_add_tickets, name = 'sale_add_tickets'),
    path('sale/<uuid:sale_uuid>/update/extras', views.sale_update_extras, name = 'sale_update_extras'),
    path('sale/<uuid:sale_uuid>/remove/performance/<uuid:performance_uuid>', views.sale_remove_performance, name = 'sale_remove_performance'),
    path('sale/<uuid:sale_uuid>/remove/ticket/<uuid:ticket_uuid>', views.sale_remove_ticket, name = 'sale_remove_ticket'),
    path('sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    # Refund AJAX support
    path('<uuid:boxoffice_uuid>/refund', views.refund_start, name = 'refund_start'),
    path('refund/<uuid:refund_uuid>/add/ticket', views.refund_add_ticket, name = 'refund_add_ticket'),
    path('refund/<uuid:refund_uuid>/remove/ticket/<uuid:ticket_uuid>', views.refund_remove_ticket, name = 'refund_remove_ticket'),
    path('refund/<uuid:refund_uuid>/complete', views.refund_complete, name = 'refund_complete'),
    path('refund/<uuid:refund_uuid>/cancel', views.refund_cancel, name = 'refund_cancel'),
    # Report AJAX support
    path('<uuid:boxoffice_uuid>/report/summary/<str:yyyymmdd>', views.report_summary, name = 'report_summary'),
    path('<uuid:boxoffice_uuid>/report/sales/<str:yyyymmdd>', views.report_sales, name = 'report_sales'),
    path('sale/<uuid:sale_uuid>/report', views.report_sale_detail, name = 'report_sale_detail'),
    path('<uuid:boxoffice_uuid>/report/refunds<str:yyyymmdd>', views.report_refunds, name = 'report_refunds'),
    path('refund/<uuid:refund_uuid>/report', views.report_refund_detail, name = 'report_refund_detail'),
]
