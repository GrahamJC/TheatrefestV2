from django.urls import path

from . import views
from .reports import finance
from .reports import sales
from .reports import volunteer

app_name = "reports"

urlpatterns = [
    # Selection
    path('select/<str:category>', views.select, name = 'select'),
    path('select/<str:category>/<str:report_name>', views.select, name = 'select_report'),
    # AJAX
    path('ajax/venue/<str:venue_id>/date/<str:date>/performances', views.ajax_venue_date_performances, name = 'ajax_venue_date_performances'),
    # Finance reports
    path('finance/festival_summary', finance.festival_summary, name = 'finance_festival_summary'),
    path('finance/boxoffice_summary', finance.boxoffice_summary, name = 'finance_boxoffice_summary'),
    path('finance/venue_summary', finance.venue_summary, name = 'finance_venue_summary'),
    path('finance/refunds', finance.refunds, name = 'finance_refunds'),
    path('finance/company_payment', finance.company_payment, name = 'finance_company_payment'),
    path('finance/company_buckets', finance.company_buckets, name = 'finance_company_buckets'),
    # Sales reports
    path('sales/audience', sales.audience, name = 'sales_audience'),
    path('sales/admission_lists', sales.admission_lists, name = 'sales_admission_lists'),
    path('sales/tickets_by_type', sales.tickets_by_type, name = 'sales_tickets_by_type'),
    path('sales/tickets_by_channel', sales.tickets_by_channel, name = 'sales_tickets_by_channel'),
    # Volunteer reports
    path('volunteer/shifts', volunteer.shifts_pdf, name = 'volunteer_shifts_pdf'),
    path('volunteer/<uuid:volunteer_uuid>/shifts', volunteer.shifts_pdf, name = 'volunteer_shifts_pdf'),
    # Old reports
    path('sale/<uuid:sale_uuid>/pdf', finance.sale_pdf, name = 'sale_pdf'),
    path('refund/<uuid:refund_uuid>/pdf', finance.refund_pdf, name = 'refund_pdf'),
    path('admission/<uuid:performance_uuid>/pdf', finance.admission_pdf, name = 'admission_pdf'),
]
