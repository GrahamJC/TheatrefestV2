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

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

from program.models import Venue, Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, Fringer, Ticket, Checkpoint


@require_GET
@login_required
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
def venue_summary(request):

    # Get selection criteria
    venue = Venue.objects.get(id = int(request.GET['venue']))
    date = datetime.datetime.strptime(request.GET['date'], '%Y%m%d')

    # Fetch data
    performances = []
    for performance in ShowPerformance.objects.filter(show__venue = venue, date = date).order_by('time'):
        open = performance.open_checkpoint if performance.has_open_checkpoint else None
        close = performance.close_checkpoint if performance.has_close_checkpoint else None
        if open and close:
            sales_cash = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__gt = open.created, sale__created__lt = close.created).count() or 0
            sales_buttons = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum'] or 0
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
    )
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    # Performances
    for performance in performances:
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{ performance['time']:%I:%M%p } { performance['show'] }</b></para>", styles['Normal']),
        ))
        table_styles.append(('SPAN', (0, 0), (4, 0)))
        table_styles.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
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
        if performance['open'] and performance['open'].notes:
            table_data.append((
                'Open notes',
                Paragraph(performance['open'].notes, styles['Normal']),
            ))
            row = len(table_data) - 1
            table_styles.append(('SPAN', (1, row), (4, row)))
        if performance['close'] and performance['close'].notes:
            table_data.append((
                'Close notes',
                Paragraph(performance['close'].notes, styles['Normal']),
            ))
            row = len(table_data) - 1
            table_styles.append(('SPAN', (1, row), (4, row)))
        table = Table(
            table_data,
            colWidths = (3*cm, 3*cm, 3*cm, 3*cm, 3*cm),
            style = table_styles,
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response


@require_GET
@login_required
@user_passes_test(lambda u: u.is_volunteer or u.is_admin)
def boxoffice_summary(request):

    # Get selection criteria
    boxoffice = BoxOffice.objects.get(id = int(request.GET['boxoffice']))
    date = datetime.datetime.strptime(request.GET['date'], '%Y%m%d')

    # Fetch data
    periods = []
    prev_checkpoint = None
    for checkpoint in boxoffice.checkpoints.filter(created__gte = date, created__lt = (date + datetime.timedelta(days = 1))).order_by('created'):
        open = prev_checkpoint
        close = checkpoint
        if open and close:
            sales_cash = Sale.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_fringers = Fringer.objects.filter(sale__boxoffice = boxoffice, sale__created__gt = open.created, sale__created__lt = close.created).count() or 0
            sales_buttons = Sale.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum'] or 0
            refunds_cash = Refund.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum'] or 0
            periods.append({
                'open': open,
                'close': close,
                'sales': {
                    'cash': sales_cash,
                    'fringers': sales_fringers,
                    'buttons': sales_buttons,
                },
                'refunds': {
                    'cash': refunds_cash,
                },
                'variance': {
                    'cash': close.cash - open.cash - sales_cash + refunds_cash,
                    'fringers': close.fringers - open.fringers + sales_fringers,
                    'buttons': close.buttons - open.buttons + sales_buttons,
                },
            })
        prev_checkpoint = checkpoint

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'boxoffice': boxoffice,
            'date': date,
            'periods': periods,
        }
        return render(request, 'reports/finance/boxoffice_summary.html', context)

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
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
    if boxoffice.festival.banner:
        banner = Image(boxoffice.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Box office and date
    table = Table(
        (
            (Paragraph('<para><b>Box office:</b></para>', styles['Normal']), boxoffice.name),
            (Paragraph('<para><b>Date:</b></para>', styles['Normal']), f"{date:%A, %d %B}"),
        ),
        colWidths = (4*cm, 12*cm),
    )
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    # Periods
    for period in periods:
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{ period['open'].created:%I:%M%p } to { period['close'].created:%I:%M%p }</b></para>", styles['Normal']),
        ))
        table_styles.append(('SPAN', (0, 0), (5, 0)))
        table_styles.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
        table_data.append((
            '',
            'Open',
            'Sales',
            'Refunds',
            'Close',
            'Variance',
        ))
        table_data.append((
            'Cash',
            f"£{ period['open'].cash }" if period.get('open', None) else '',
            f"£{ period['sales']['cash'] }" if period.get('sales', None) else '',
            f"£{ period['refunds']['cash'] }" if period.get('refunds', None) else '',
            f"£{ period['close'].cash }" if period.get('close', None) else '',
            f"£{ period['variance']['cash'] }" if period.get('variance', None) else '',
        ))
        table_data.append((
            'Fringers',
            period['open'].fringers if period.get('open', None) else '',
            period['sales']['fringers'] if period.get('sales', None) else '',
            '',
            period['close'].fringers if period.get('close', None) else '',
            period['variance']['fringers'] if period.get('variance', None) else '',
        ))
        table_data.append((
            'Buttons',
            period['open'].buttons if period.get('open', None) else '',
            period['sales']['buttons'] if period.get('sales', None) else '',
            '',
            period['close'].buttons if period.get('close', None) else '',
            period['variance']['buttons'] if period.get('variance', None) else '',
        ))
        if period['open'] and period['open'].notes:
            table_data.append((
                'Open notes',
                Paragraph(period['open'].notes, styles['Normal']),
            ))
            row = len(table_data) - 1
            table_styles.append(('SPAN', (1, row), (5, row)))
        if period['close'] and period['close'].notes:
            table_data.append((
                'Close notes',
                Paragraph(period['close'].notes, styles['Normal']),
            ))
            row = len(table_data) - 1
            table_styles.append(('SPAN', (1, row), (5, row)))
        table = Table(
            table_data,
            colWidths = (2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm),
            style = table_styles,
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
