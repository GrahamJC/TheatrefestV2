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
    # Finance reports
    path('finance/venue_summary', finance.venue_summary, name = 'finance_venue_summary'),
    path('finance/boxoffice_summary', finance.boxoffice_summary, name = 'finance_boxoffice_summary'),
    # Sales reports
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
