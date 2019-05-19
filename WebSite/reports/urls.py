from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    # Selection
    path('select/<str:category>', views.select, name = 'select'),
    path('select/<str:category>/<str:report_name>', views.select, name = 'select_report'),
    # Finance reports
    path('finance/venue_summary', views.venue_summary, name = 'finance__venue_summary'),
    # Sales
    path('sale/<uuid:sale_uuid>/pdf', views.sale_pdf, name = 'sale_pdf'),
    # Refunds
    path('refund/<uuid:refund_uuid>/pdf', views.refund_pdf, name = 'refund_pdf'),
    # Admissions
    path('admission/<uuid:performance_uuid>/pdf', views.admission_pdf, name = 'admission_pdf'),
]
