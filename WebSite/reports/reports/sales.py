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

from program.models import Show, ShowPerformance
from tickets.models import TicketType, Ticket

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
