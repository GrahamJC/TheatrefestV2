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
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

from program.models import Venue, Show, ShowPerformance
from tickets.models import TicketType, Ticket

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admission_lists(request):

    # Get selection criteria (date is required)
    selected_date = datetime.datetime.strptime(request.GET['date'], '%Y%m%d')
    selected_venue = None
    if request.GET['venue']:
        selected_venue = Venue.objects.get(id = int(request.GET['venue']))
    selected_performance = None
    if request.GET['performance']:
        selected_performance = ShowPerformance.objects.get(id = int(request.GET['performance']))

    # Get list of performances to include
    if selected_performance:
        performances = [selected_performance,]
    elif selected_venue:
        performances = [performance for performance in ShowPerformance.objects.filter(date = selected_date, show__venue = selected_venue).order_by('time')]
    else:
        performances = [performance for performance in ShowPerformance.objects.filter(date = selected_date, show__venue__is_ticketed = True).order_by('show__venue__name', 'time')]

    # Get tickets for each performance
    admission_lists = []
    for performance in performances:
        admission_lists.append({
            'performance': performance,
            'venue_tickets': performance.tickets.filter(sale__completed__isnull = False, refund__isnull = True, sale__venue__isnull = False).order_by('id'),
            'non_venue_tickets': performance.tickets.filter(sale__completed__isnull = False, refund__isnull = True, sale__venue__isnull = True).order_by('id'),
            'cancelled_tickets': performance.tickets.filter(refund__isnull = False).order_by('id'),
        })

    # Check for HTML
    format = request.GET['format']
    if format.lower() == 'html':

        # Render tickets
        context = {
            'admission_lists': admission_lists,
        }
        return render(request, "reports/sales/admission_lists.html", context)

    # Render as PDF
    response = HttpResponse(content_type = 'application/pdf')
    response['Content-Disposition'] = 'inline'
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

    # Process each admission list
    for admission_list in admission_lists:

        # Get performance
        performance = admission_list['performance']

        # Festival banner
        if request.festival.banner:
            banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
            banner.hAlign = 'CENTER'
            story.append(banner)
            story.append(Spacer(1, 1*cm))

        # Venue and performance
        table = Table(
            (
                (Paragraph('<para><b>Venue:</b></para>', styles['Normal']), performance.show.venue.name),
                (Paragraph('<para><b>Show:</b></para>', styles['Normal']), performance.show.name),
                (Paragraph('<para><b>Performance:</b></para>', styles['Normal']), f"{performance.date:%A, %d %B} at {performance.time:%I:%M%p}"),
            ),
            colWidths = (4*cm, 12*cm),
            hAlign = 'LEFT'
        )
        story.append(table)

        # Box Offixe and Online tickets
        story.append(Paragraph('<para>Box Office and Online Sales</para>', styles['Heading3']))
        table_data = []
        table_data.append((
            Paragraph(f"<para><b>Ticket No</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Name/e-mail</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Type</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Sale</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Token</b></para>", styles['Normal']),
        ))
        for ticket in admission_list['non_venue_tickets']:
            name_email= ticket.user.email if ticket.user else ticket.sale.customer
            sale_type = 'Box office' if ticket.sale.boxoffice else 'Online'
            table_data.append((
                str(ticket.id),
                name_email,
                ticket.description,
                sale_type,
                'Yes' if ticket.token_issued else 'No',
            ))
        table = Table(
            table_data,
            colWidths = (1.5*cm, 8.5*cm, 2*cm, 2*cm, 2*cm),
            hAlign = 'LEFT',
        )
        story.append(table)

        # Venue tickets
        story.append(Paragraph('<para>Venue Sales</para>', styles['Heading3']))
        table_data = []
        table_data.append((
            Paragraph(f"<para><b>Ticket No</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Name/e-mail</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Type</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Sale</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Token</b></para>", styles['Normal']),
        ))
        for ticket in admission_list['venue_tickets']:
            name_email= ticket.user.email if ticket.user else ticket.sale.customer
            table_data.append((
                str(ticket.id),
                name_email,
                ticket.description,
                'Venue',
                'Yes' if ticket.token_issued else 'No',
            ))
        table = Table(
            table_data,
            colWidths = (1.5*cm, 8.5*cm, 2*cm, 2*cm, 2*cm),
            hAlign = 'LEFT',
        )
        story.append(table)

        # Cancelled tickets
        if admission_list['cancelled_tickets']:
            story.append(Paragraph('<para>Cancelled Tickets</para>', styles['Heading3']))
            table_data = []
            table_data.append((
                Paragraph(f"<para><b>Ticket No</b></para>", styles['Normal']),
                Paragraph(f"<para><b>Name/e-mail</b></para>", styles['Normal']),
                Paragraph(f"<para><b>Type</b></para>", styles['Normal']),
                Paragraph(f"<para><b>Sale</b></para>", styles['Normal']),
            ))
            for ticket in admission_list['cancelled_tickets']:
                name_email= ticket.user.email if ticket.user else ticket.sale.customer
                sale_type = 'Venue' if ticket.sale.venue else 'Box office' if ticket.sale.boxoffice else 'Online'
                table_data.append((
                    str(ticket.id),
                    name_email,
                    ticket.description,
                    sale_type,
                ))
            table = Table(
                table_data,
                colWidths = (1.5*cm, 10.5*cm, 2*cm, 2*cm),
                hAlign = 'LEFT',
            )
            story.append(table)

        # New page for next list
        story.append(PageBreak())

    # Render PDF document and return it
    doc.build(story)
    return response

def _get_performance_tickets_by_type(performance, ticket_types):

    tickets = {}
    for tt in ticket_types:
        tickets[tt] = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True, description = tt).count()
    tickets['Total'] = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True).count()
    return {
        'date': performance.date,
        'time': performance.time,
        'tickets': tickets,
    }

def _get_show_tickets_by_type(show, ticket_types):

    return {
        'name': show.name,
        'performances': [_get_performance_tickets_by_type(p, ticket_types) for p in show.performances.order_by('date', 'time')],
    }

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def tickets_by_type(request):

    # Get selection criteria
    selected_show = Show.objects.get(id = int(request.GET['show'])) if request.GET['show'] else None

    # Fetch data
    ticket_types = [tt.name for tt in TicketType.objects.filter(festival = request.festival).order_by('name')]
    ticket_types.append('eFringer')
    ticket_types.append('Volunteer')
    shows = []
    if selected_show:
        shows.append(_get_show_tickets_by_type(selected_show, ticket_types))
    else:
        for show in Show.objects.filter(festival = request.festival, venue__is_ticketed = True).order_by('name'):
            shows.append(_get_show_tickets_by_type(show, ticket_types))

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'ticket_types': ticket_types,
            'shows': shows,
        }
        return render(request, 'reports/sales/tickets_by_type.html', context)

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 1.5*cm,
        rightMargin = 1.5*cm,
        topMargin = 1.5*cm,
        bottomMargin = 1.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Shows
    for show in shows:

        # Header
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{ show['name'] }</b></para>", styles['Normal']),
        ))
        table_styles.append(('SPAN', (0, 0), (len(ticket_types) + 1, 0)))
        table_styles.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
        row = ['']
        for ticket_type in ticket_types:
            row.append(ticket_type)
        row.append('Total')
        table_data.append(row)

        # Performances
        for performance in show['performances']:
            row = [Paragraph(f"<para>{ performance['date']:%a, %b %d } at { performance['time']:%I:%M%p }</para>", styles['Normal'])]
            for ticket_type in ticket_types:
                row.append(performance['tickets'][ticket_type])
            row.append(performance['tickets']['Total'])
            table_data.append(row)
        colWidths = [5*cm]
        for ticket_type in ticket_types:
            colWidths.append((11 / len(ticket_types))*cm)
        colWidths.append(2*cm)

        # Add to story
        table = Table(
            table_data,
            colWidths = colWidths,
            style = table_styles,
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response


def _get_performance_tickets_by_channel(performance, channels):

    tickets = {}
    for c in channels:
        query = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True)
        if c == 'Online':
            query = query.filter(sale__boxoffice__isnull = True, sale__venue__isnull = True)
        elif c == 'BoxOffice':
            query = query.filter(sale__boxoffice__isnull = False)
        elif c == 'Venue':
            query = query.filter(sale__venue__isnull = False)
        tickets[c] = query.count()
    tickets['Total'] = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True).count()
    return {
        'date': performance.date,
        'time': performance.time,
        'tickets': tickets,
    }

def _get_show_tickets_by_channel(show, channels):

    return {
        'name': show.name,
        'performances': [_get_performance_tickets_by_channel(p, channels) for p in show.performances.order_by('date', 'time')],
    }


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def tickets_by_channel(request):

    # Get selection criteria
    selected_show = Show.objects.get(id = int(request.GET['show'])) if request.GET['show'] else None

    # Fetch data
    channels = ['Online', 'BoxOffice', 'Venue']
    shows = []
    if selected_show:
        shows.append(_get_show_tickets_by_channel(selected_show, channels))
    else:
        for show in Show.objects.filter(festival = request.festival, venue__is_ticketed = True).order_by('name'):
            shows.append(_get_show_tickets_by_channel(show, channels))

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'channels': channels,
            'shows': shows,
        }
        return render(request, 'reports/sales/tickets_by_channel.html', context)

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 1.5*cm,
        rightMargin = 1.5*cm,
        topMargin = 1.5*cm,
        bottomMargin = 1.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Shows
    for show in shows:

        # Header
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{ show['name'] }</b></para>", styles['Normal']),
        ))
        table_styles.append(('SPAN', (0, 0), (len(channels) + 1, 0)))
        table_styles.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
        row = ['']
        for channel in channels:
            row.append(channel)
        row.append('Total')
        table_data.append(row)

        # Performances
        for performance in show['performances']:
            row = [Paragraph(f"<para>{ performance['date']:%a, %b %d } at { performance['time']:%I:%M%p }</para>", styles['Normal'])]
            for channel in channels:
                row.append(performance['tickets'][channel])
            row.append(performance['tickets']['Total'])
            table_data.append(row)
        colWidths = [5*cm]
        for channel in channels:
            colWidths.append((11 / len(channels))*cm)
        colWidths.append(2*cm)

        # Add to story
        table = Table(
            table_data,
            colWidths = colWidths,
            style = table_styles,
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response

def _get_performance_audience(performance):

    return {
        'date': performance.date,
        'time': performance.time,
        'tickets': Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True).count(),
        'tokens_issued': Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True, token_issued = True).count(),
        'tokens_collected': performance.audience,
    }

def _get_show_audience(show):

    return {
        'name': show.name,
        'performances': [_get_performance_audience(performance) for performance in show.performances.order_by('date', 'time')],
    }

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def audience(request):

    # Get selection criteria
    selected_show = Show.objects.get(id = int(request.GET['show'])) if request.GET['show'] else None

    # Get list of shows
    shows = []
    if selected_show:
        shows.append(_get_show_audience(selected_show))
    else:
        for show in Show.objects.filter(festival = request.festival, venue__is_ticketed = True).order_by('name'):
            shows.append(_get_show_audience(show))

    # Check for HTML
    format = request.GET['format']
    if format.lower() == 'html':

        # Render tickets
        context = {
            'shows': shows,
        }
        return render(request, "reports/sales/audience.html", context)

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 1.5*cm,
        rightMargin = 1.5*cm,
        topMargin = 1.5*cm,
        bottomMargin = 1.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Shows
    for show in shows:

        # Header
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{ show['name'] }</b></para>", styles['Normal']),
        ))
        table_styles.append(('SPAN', (0, 0), (2, 0)))
        table_styles.append(('ALIGN', (0, 0), (0, 0), 'LEFT'))
        table_data.append(['', 'Tickets', 'Tokens Issued', 'Tokens Collected'])

        # Performances
        for performance in show['performances']:
            table_data.append([
                Paragraph(f"<para>{ performance['date']:%a, %b %d } at { performance['time']:%I:%M%p }</para>", styles['Normal']),
                performance['tickets'],
                performance['tokens_issued'],
                performance['tokens_collected']
            ])
        colWidths = [5*cm, 4*cm, 4*cm, 4*cm]

        # Add to story
        table = Table(
            table_data,
            colWidths = colWidths,
            style = table_styles,
        )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response
