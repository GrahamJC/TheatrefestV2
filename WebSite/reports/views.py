import os
import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.views import View
from django.views.decorators.http import require_http_methods, require_GET
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse

import arrow

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from program.models import Show, ShowPerformance

from .forms import SelectNullForm, SelectVenueForm, SelectBoxOfficeForm, SelectTicketsForm, SelectAdmissionForm, SelectCompanyForm, SelectAudienceForm

# Report definitions
reports = {
    'finance': {
        'festival_summary': {
            'title': 'Festival summary',
            'select_form': SelectNullForm,
            'select_fields': [],
            'select_required': [],
            'report_url': reverse_lazy('reports:finance_festival_summary'),
            'formats': ['HTML', 'PDF'],
        },
        'boxoffice_summary': {
            'title': 'Box Office summary',
            'select_form': SelectBoxOfficeForm,
            'select_fields': ['boxoffice', 'date'],
            'select_required': ['boxoffice', 'date'],
            'report_url': reverse_lazy('reports:finance_boxoffice_summary'),
            'formats': ['HTML', 'PDF'],
        },
        'venue_summary': {
            'title': 'Venue summary',
            'select_form': SelectVenueForm,
            'select_fields': ['venue', 'date'],
            'select_required': ['venue', 'date'],
            'report_url': reverse_lazy('reports:finance_venue_summary'),
            'formats': ['HTML', 'PDF'],
        },
        'refunds': {
            'title': 'Refunds',
            'select_form': SelectNullForm,
            'select_fields': [],
            'select_required': [],
            'report_url': reverse_lazy('reports:finance_refunds'),
            'formats': ['HTML', 'PDF'],
        },
        'company_payment': {
            'title': 'Company payment',
            'select_form': SelectCompanyForm,
            'select_fields': ['company'],
            'select_required': [],
            'report_url': reverse_lazy('reports:finance_company_payment'),
            'formats': ['HTML', 'PDF', 'XLSX'],
        },
    },
    'sales': {
        'audiences': {
            'title': 'Audience',
            'select_form': SelectAudienceForm,
            'select_fields': ['show'],
            'select_required': [],
            'report_url': reverse_lazy('reports:sales_audience'),
            'formats': ['HTML', 'PDF'],
        },
        'admission_lists': {
            'title': 'Admission lists',
            'select_form': SelectAdmissionForm,
            'select_fields': ['date', 'venue', 'performance'],
            'select_required': ['date'],
            'report_url': reverse_lazy('reports:sales_admission_lists'),
            'formats': ['HTML', 'PDF'],
        },
        'tickets_by_type': {
            'title': 'Ticket sales by ticket type',
            'select_form': SelectTicketsForm,
            'select_fields': ['show'],
            'select_required': [],
            'report_url': reverse_lazy('reports:sales_tickets_by_type'),
            'formats': ['HTML', 'PDF'],
        },
        'tickets_by_channel': {
            'title': 'Ticket sales by channel (online, box office or venue)',
            'select_form': SelectTicketsForm,
            'select_fields': ['show'],
            'select_required': [],
            'report_url': reverse_lazy('reports:sales_tickets_by_channel'),
            'formats': ['HTML', 'PDF'],
        },
    },
}


# Helpers
def get_select_form(festival, report, post_data = None):

    # Create form
    form_class = report['select_form']
    form = form_class(festival, report['select_fields'], report['select_required'], data = post_data)

    # Create crispy forms helper
    helper = FormHelper()
    helper.form_class = 'form-horizontal'
    helper.label_class = 'col-2'
    helper.field_class = 'col-10'
    layout_items = []
    for field in report['select_fields']:
        layout_items.append(Field(field))
    layout_items.append(Submit('create', 'Create Report'))
    helper.layout = Layout(*layout_items)
    form.helper = helper

    # Return form
    return form


@require_http_methods(["GET", "POST"])
@login_required
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
def select(request, category, report_name = None):

    # Check parameters
    assert category in reports
    report = None
    if report_name:
        assert report_name in reports[category]
        report = reports[category][report_name]

    # Initialize selection form and report URLs
    select_form = None
    report_title = ''
    report_html_url = ''
    report_pdf_url = ''
    report_xlsx_url = ''

    # Report selection
    if request.method == 'GET':

        # If there is a selected report create the selection form
        if report:
            select_form = get_select_form(request.festival, report)

    # Report creation
    else:

        # Create, bind and validate form
        assert report
        select_form = get_select_form(request.festival, report, request.POST)
        if select_form.is_valid():

            # Get report title and URL with selection parameters
            report_title = report['title']
            report_url = report['report_url']
            seperator = '&' if '?' in report_url else '?'
            if report['select_fields']:
                for field in report['select_fields']:
                    report_url += seperator + field + '=' + select_form.cleaned_data[field]
                    seperator = '&'
            if 'HTML' in report['formats']:
                report_html_url = report_url + seperator + 'format=HTML'
            if 'PDF' in report['formats']:
                report_pdf_url = report_url + seperator + 'format=PDF'
            if 'XLSX' in report['formats']:
                report_xlsx_url = report_url + seperator + 'format=XLSX'

    # Render selection page
    context = {
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': category.capitalize() + ' Reports' },
        ],
        'festival': request.festival,
        'category': category,
        'reports': reports[category],
        'selected_report': report_name,
        'select_form': select_form,
        'report_title': report_title,
        'report_html_url': report_html_url,
        'report_pdf_url': report_pdf_url,
        'report_xlsx_url': report_xlsx_url,
    }
    return render(request, 'reports/main.html', context)

# AJAX support
def ajax_venue_date_performances(request, date = None, venue_id = None):

    html = '<option value="">All performances</option>'
    date = datetime.datetime.strptime(date, '%Y%m%d') if date else None
    venue_id = int(venue_id) if venue_id else None
    if date and venue_id:
        performances = ShowPerformance.objects.filter(date = date, show__venue_id = venue_id).order_by('time')
        for performance in performances:
            html += f"<option value=\"{performance.id}\">{performance.time:%I:%M%p}: {performance.show.name}</option>"
    return HttpResponse(html)
