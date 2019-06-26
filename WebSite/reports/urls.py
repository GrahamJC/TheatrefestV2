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
    path('ajax/performances/<str:date>/<str:venue_id>', views.ajax_performances, name = 'ajax_performances'),
    # Finance reports
    path('finance/venue_summary', finance.venue_summary, name = 'finance_venue_summary'),
    path('finance/boxoffice_summary', finance.boxoffice_summary, name = 'finance_boxoffice_summary'),
    # Sales reports
    path('sales/admission_list', sales.admission_list, name = 'sales_admission_list'),
    path('sales/tickets_by_type', sales.tickets_by_type, name = 'sales_tickets_by_type'),
    path('sales/tickets_by_channel', sales.tickets_by_channel, name = 'sales_tickets_by_channel'),
    # Volunteer reports
    path('volunteer/shifts', volunteer.shifts_pdf, name = 'volunteer_shifts_pdf'),
    path('volunteer/<uuid:volunteer_uuid>/shifts', volunteer.shifts_pdf, name = 'volunteer_shifts_pdf'),
]
