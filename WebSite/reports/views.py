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

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

from program.models import Venue, Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, Fringer, Ticket

from .forms import SelectForm

# Report definitions
reports = {
    'finance': {
        'venue_summary': {
            'title': 'Venue summary',
            'select_form': SelectForm,
            'select_fields': ['ticketed_venue', 'performance_date'],
            'select_required': ['ticketed_venue', 'performance_date'],
            'report_url': reverse_lazy('reports:finance__venue_summary'),
        }
    }
}


# Helpers
def get_select_form(festival, report, post_data = None):

    # Create form
    form = report['select_form'](festival, report['select_fields'], report['select_required'], data = post_data)

    # Create crispy forms helper
    helper = FormHelper()
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
            seperator = '?'
            for field in report['select_fields']:
                report_url += seperator + field + '=' + select_form.cleaned_data[field]
                seperator = '&'
            report_html_url = report_url + seperator + 'format=HTML'
            report_pdf_url = report_url + seperator + 'format=PDF'

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
    }
    return render(request, 'reports/main.html', context)


# Finance reports
@require_GET
@login_required
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
def venue_summary(request):

    # Get selection criteria
    venue = Venue.objects.get(id = int(request.GET['ticketed_venue']))
    date = datetime.datetime.strptime(request.GET['performance_date'], '%Y%m%d')

    # Fetch data
    performances = []
    for performance in ShowPerformance.objects.filter(show__venue = venue, date = date).order_by('time'):
        open = performance.open_checkpoint if performance.has_open_checkpoint else None
        close = performance.close_checkpoint if performance.has_close_checkpoint else None
        if open and close:
            #sales_cash = sum([sale.total_cost for sale in Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created)])
            sales_cash = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum']
            sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__gt = open.created, sale__created__lt = close.created).count()
            sales_buttons = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum']
            performances.append({
                'show': performance.show.name,
                'time': performance.time, 
                'open': open,
                'close': close,
                'sales': {
                    'cash': sales_cash,
                    'fringers': sales_fringers,
                    'buttons': sales_buttons,
                },
                'variance': {
                    'cash': close.cash - open.cash - sales_cash,
                    'fringers': close.fringers - open.fringers + sales_fringers,
                    'buttons': close.buttons - open.buttons + sales_buttons,
                },
            })
        else:
            performances.append({
                'show': performance.show.name,
                'time': performance.time, 
                'open': open,
                'close': close,
            })

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'venue': venue,
            'date': date,
            'performances': performances,
        }
        return render(request, 'reports/finance/venue_summary.html', context)

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
    #response['Content-Disposition'] = 'venue_summary.pdf'
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 2.5*cm,
        rightMargin = 2.5*cm,
        topMargin = 2.5*cm,
        bottomMargin = 2.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if venue.festival.banner:
        banner = Image(venue.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Venue and date
    table = Table(
        (
            (Paragraph('<para><b>Venue:</b></para>', styles['Normal']), venue.name),
            (Paragraph('<para><b>Date:</b></para>', styles['Normal']), f"{date:%A, %d %B}"),
        ),
        colWidths = (4*cm, 12*cm),
        hAlign = 'LEFT'
    )
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    # Performances
    for performance in performances:
        table_data = []
        table_data.append((
            Paragraph(f"<para><b>{ performance['time']:%I:%M%p } { performance['show'] }</b></para>", styles['Normal']),
            '',
            '',
            '',
            '',
        ))
        table_data.append((
            '',
            'Open',
            'Sales',
            'Close',
            'Variance',
        ))
        table_data.append((
            'Cash',
            f"£{ performance['open'].cash }" if performance.get('open', None) else '',
            f"£{ performance['sales']['cash'] }" if performance.get('sales', None) else '',
            f"£{ performance['close'].cash }" if performance.get('close', None) else '',
            f"£{ performance['variance']['cash'] }" if performance.get('variance', None) else '',
        ))
        table_data.append((
            'Fringers',
            performance['open'].fringers if performance.get('open', None) else '',
            performance['sales']['fringers'] if performance.get('sales', None) else '',
            performance['close'].fringers if performance.get('close', None) else '',
            performance['variance']['fringers'] if performance.get('variance', None) else '',
        ))
        table_data.append((
            'Buttons',
            performance['open'].buttons if performance.get('open', None) else '',
            performance['sales']['buttons'] if performance.get('sales', None) else '',
            performance['close'].buttons if performance.get('close', None) else '',
            performance['variance']['buttons'] if performance.get('variance', None) else '',
        ))
        table = Table(
            table_data,
            colWidths = (3*cm, 3*cm, 3*cm, 3*cm, 3*cm),
            hAlign = 'LEFT',
            style = (
                ('SPAN', (0, 0), (4, 0)),
                ('ALIGN', (0, 1), (4, -1), 'RIGHT'),
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response


@login_required
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
def sale_pdf(request, sale_uuid):

    # Get sale to be printed
    sale = get_object_or_404(Sale, uuid = sale_uuid)

    # Create receipt as a Platypus story
    response = HttpResponse(content_type = "application/pdf")
    response["Content-Disposition"] = f"filename=sale{sale.id}.pdf"
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 2.5*cm,
        rightMargin = 2.5*cm,
        topMargin = 2.5*cm,
        bottomMargin = 2.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if sale.festival.banner:
        banner = Image(sale.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Customer and sale number
    table = Table(
        (
            (Paragraph("<para><b>Customer:</b></para>", styles['Normal']), sale.customer),
            (Paragraph("<para><b>Sale no:</b></para>", styles['Normal']), sale.id),
        ),
        colWidths = (4*cm, 12*cm),
        hAlign = 'LEFT'
    )
    story.append(table)
    story.append(Spacer(1, 1*cm))

    # Buttons and fringers
    if sale.buttons or sale.fringers.count():
        tableData = []
        if sale.buttons:
            tableData.append((Paragraph("<para><b>Buttons</b></para>", styles['Normal']), sale.buttons, f"£{sale.button_cost}"))
        if sale.fringers.count():
            tableData.append((Paragraph("<para><b>Fringers</b></para>", styles['Normal']), sale.fringers.count(), f"£{sale.fringer_cost}"))
        table = Table(
            tableData,
            colWidths = (8*cm, 4*cm, 4*cm),
            hAlign = 'LEFT',
            style = (
                ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Tickets
    is_first = True
    for performance in sale.performances:
        if not is_first:
            story.append(Spacer(1, 0.5*cm))
        is_first = False
        tableData = []
        tableData.append((Paragraph(f"<para>{performance['date']:%a, %e %b} at {performance['time']:%I:%M %p} - <b>{performance['show']}</b></para>", styles['Normal']), "", "", ""))
        for ticket in performance['tickets']:
            tableData.append((f"{ticket['id']}", "", ticket['description'], f"£{ticket['cost']}"))
        table = Table(
            tableData,
            colWidths = (4*cm, 4*cm, 4*cm, 4*cm),
            hAlign = 'LEFT',
            style = (
                ('SPAN', (0, 0), (3, 0)),
                ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            )
        )
        story.append(table)

    # Total
    story.append(Spacer(1, 1*cm))
    table = Table(
        (
            ("", Paragraph("<para><b>Total:</b></para>", styles['Normal']), f"£{sale.total_cost}"),
        ),
        colWidths = (8*cm, 4*cm, 4*cm),
        hAlign = 'LEFT',
        style = (
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        )
    )
    story.append(table)

    # Create PDF document and return it
    doc.build(story)
    return response
    
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
@login_required
def refund_pdf(request, refund_uuid):

    # Get refund to be printed
    refund = get_object_or_404(Refund, uuid = refund_uuid)

    # Create receipt as a Platypus story
    response = HttpResponse(content_type = "application/pdf")
    response["Content-Disposition"] = f"filename=refund{refund.id}.pdf"
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 2.5*cm,
        rightMargin = 2.5*cm,
        topMargin = 2.5*cm,
        bottomMargin = 2.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if refund.festival.banner:
        banner = Image(refund.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Customer, refund number and amount
    table = Table(
        (
            (Paragraph("<para><b>Customer:</b></para>", styles['Normal']), refund.customer),
            (Paragraph("<para><b>Refund no:</b></para>", styles['Normal']), refund.id),
            (Paragraph("<para><b>Amount:</b></para>", styles['Normal']), f"£{refund.amount}"),
        ),
        colWidths = (4*cm, 12*cm),
        hAlign = 'LEFT'
    )
    story.append(table)
    story.append(Spacer(1, 1*cm))

    # Tickets
    is_first = True
    for performance in refund.performances:
        if not is_first:
            story.append(Spacer(1, 0.5*cm))
        is_first = False
        tableData = []
        tableData.append((Paragraph(f"<para>{performance['date']:%a, %e %b} at {performance['time']:%I:%M %p} - <b>{performance['show']}</b></para>", styles['Normal']), "", "", ""))
        for ticket in performance['tickets']:
            tableData.append((f"{ticket['id']}", "", ticket['description'], f"£{ticket['cost']}"))
        table = Table(
            tableData,
            colWidths = (4*cm, 4*cm, 4*cm, 4*cm),
            hAlign = 'LEFT',
            style = (
                ('SPAN', (0, 0), (3, 0)),
                ('ALIGN', (0, 1), (0, -1), 'RIGHT'),
                ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
            )
        )
        story.append(table)

    # Create PDF document and return it
    doc.build(story)
    return response

@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
@login_required
def admission_pdf(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Create admission list as a Platypus story
    response = HttpResponse(content_type = "application/pdf")
    response["Content-Disposition"] = f"filename=admission{performance.id}.pdf"
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 2.5*cm,
        rightMargin = 2.5*cm,
        topMargin = 2.5*cm,
        bottomMargin = 2.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if performance.show.festival.banner:
        banner = Image(os.path.join(settings.MEDIA_ROOT, performance.show.festival.banner.path), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Show and performance
    table = Table(
        (
            (Paragraph("<para><b>Show:</b></para>", styles['Normal']), performance.show),
            (Paragraph("<para><b>ShowPerformance:</b></para>", styles['Normal']), f"{performance.date:%a, %e %b} at {performance.time:%I:%M %p}"),
        ),
        colWidths = (4*cm, 12*cm),
        hAlign = 'LEFT'
    )
    story.append(table)
    story.append(Spacer(1, 1*cm))

    # Tickets
    tableData = []
    tableData.append((
        Paragraph(f"<para><b>Ticket No</b></para>", styles['Normal']),
        Paragraph(f"<para><b>Customer</b></para>", styles['Normal']),
        Paragraph(f"<para><b>Type</b></para>", styles['Normal'])
    ))
    for ticket in performance.tickets.filter(sale__completed__isnull = False).order_by('id'):
        if ticket.refund:
            tableData.append((
                Paragraph(f"<para><strike>{ticket.id}</strike></para>", styles['Normal']),
                Paragraph(f"<para><strike>{ticket.sale.customer}</strike></para>", styles['Normal']),
                Paragraph(f"<para><strike>{ticket.description}</strike></para>", styles['Normal'])
            ))
        else:
            tableData.append((
                Paragraph(f"<para>{ticket.id}</para>", styles['Normal']),
                Paragraph(f"<para>{ticket.sale.customer}</para>", styles['Normal']),
                Paragraph(f"<para>{ticket.description}</para>", styles['Normal'])
            ))
    table = Table(
        tableData,
        colWidths = (4*cm, 8*cm, 4*cm),
        hAlign = 'LEFT',
    )
    story.append(table)

    # Create PDF document and return it
    doc.build(story)
    return response
