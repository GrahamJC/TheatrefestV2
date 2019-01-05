from django.urls import path

from . import views

app_name = "venue"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:venue_uuid>', views.main, name = 'main'),
    path('<uuid:venue_uuid>/tab/<str:tab>', views.main, name = 'main'),
    # Sale AJAX support
    path('<uuid:venue_uuid>/sale', views.sale_start, name = 'sale_start'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/performances', views.sale_show_performances, name = 'sale_show_performances'),
    path('sale/<uuid:sale_uuid>/add/tickets', views.sale_add_tickets, name = 'sale_add_tickets'),
    path('sale/<uuid:sale_uuid>/update/extras', views.sale_update_extras, name = 'sale_update_extras'),
    path('sale/<uuid:sale_uuid>/remove/performance/<uuid:performance_uuid>', views.sale_remove_performance, name = 'sale_remove_performance'),
    path('sale/<uuid:sale_uuid>/remove/ticket/<uuid:ticket_uuid>', views.sale_remove_ticket, name = 'sale_remove_ticket'),
    path('sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    # Admission AJAX support
    path('<uuid:venue_uuid>/admission/shows', views.admission_shows, name = 'admission_shows'),
    path('admission/show/<uuid:show_uuid>/performances', views.admission_show_performances, name = 'admission_show_performances'),
    path('admission/performance/<uuid:performance_uuid>/tickets', views.admission_performance_tickets, name = 'admission_performance_tickets'),
    # Report AJAX support
    path('<uuid:venue_uuid>/report/summary/<str:yyyymmdd>', views.report_summary, name = 'report_summary'),
    path('<uuid:venue_uuid>/report/sales/<str:yyyymmdd>', views.report_sales, name = 'report_sales'),
    path('sale/<uuid:sale_uuid>/report', views.report_sale_detail, name = 'report_sale_detail'),
]
