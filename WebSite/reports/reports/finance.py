import os
import datetime
from collections import OrderedDict
from decimal import Decimal

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

from program.models import Company, Venue, Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, Fringer, TicketType, Ticket, Checkpoint
from volunteers.models import Volunteer

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def festival_summary(request):

    # General stuff
    date_list = [datetime.date(2019, 6, 24) + datetime.timedelta(days = d) for d in range(7)]
    venue_list = [v for v in Venue.objects.filter(festival = request.festival, is_ticketed = True).order_by('name')]
    boxoffice_list = [bo for bo in BoxOffice.objects.filter(festival = request.festival).order_by('name')]

    # Sales by channel
    online_pre = Sale.objects.filter(festival = request.festival, created__lt = date_list[0], completed__isnull = False, boxoffice__isnull = True, venue__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
    online = {
        'pre': online_pre,
        'dates': [],
        'total': online_pre,
    }
    venues = OrderedDict([(v.name, {'dates': [], 'total': 0}) for v in venue_list])
    boxoffices = OrderedDict([(bo.name, {'dates': [], 'total': 0}) for bo in boxoffice_list])
    totals = {
        'pre': online_pre,
        'dates': [],
        'total': online_pre,
    }
    for date in date_list:
        query = Sale.objects.filter(festival = request.festival, created__date = date, completed__isnull = False)
        date_total = 0
        date_amount = query.filter(boxoffice__isnull = True, venue__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
        online['dates'].append(date_amount)
        online['total'] += date_amount
        date_total += date_amount
        for venue in venue_list:
            date_amount = query.filter(venue = venue).aggregate(Sum('amount'))['amount__sum'] or 0
            venues[venue.name]['dates'].append(date_amount)
            venues[venue.name]['total'] += date_amount
            date_total += date_amount
        for boxoffice in boxoffice_list:
            date_amount = query.filter(boxoffice = boxoffice).aggregate(Sum('amount'))['amount__sum'] or 0
            boxoffices[boxoffice.name]['dates'].append(date_amount)
            boxoffices[boxoffice.name]['total'] += date_amount
            date_total += date_amount
        totals['dates'].append(date_total)
        totals['total'] += date_total
    sales_by_channel = {
        'dates': date_list,
        'online': online,
        'venues': venues,
        'boxoffices': boxoffices,
        'totals': totals,
    }

    # Sales by type
    efringers_pre = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__created__lt = date_list[0], sale__completed__isnull = False).aggregate(Sum('cost'))['cost__sum'] or 0
    tickets_pre = Ticket.objects.filter(user__isnull = False, sale__festival = request.festival, sale__created__lt = date_list[0], sale__completed__isnull = False).aggregate(Sum('cost'))['cost__sum'] or 0
    types = OrderedDict([
        ('buttons', {'title': 'Badges', 'pre': None, 'dates': [], 'total': 0}),
        ('fringers', {'title': 'Paper fringers', 'pre': None, 'dates': [], 'total': 0}),
        ('efringers', {'title': 'eFringers', 'pre': efringers_pre, 'dates': [], 'total': 0}),
        ('tickets', {'title': 'Tickets', 'pre': tickets_pre, 'dates': [], 'total': 0}),
    ])
    totals = {
        'pre': efringers_pre + tickets_pre,
        'dates': [],
        'total': efringers_pre + tickets_pre,
    }
    for date in date_list:
        date_total = 0
        date_amount = Sale.objects.filter(festival = request.festival, created__date = date, completed__isnull = False).aggregate(Sum('buttons'))['buttons__sum'] or 0
        types['buttons']['dates'].append(date_amount)
        types['buttons']['total'] += date_amount
        date_total += date_amount
        date_amount = Fringer.objects.filter(user__isnull = True, sale__festival = request.festival, sale__created__date = date, sale__completed__isnull = False).aggregate(Sum('cost'))['cost__sum'] or 0
        types['fringers']['dates'].append(date_amount)
        types['fringers']['total'] += date_amount
        date_total += date_amount
        date_amount = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__created__date = date, sale__completed__isnull = False).aggregate(Sum('cost'))['cost__sum'] or 0
        types['efringers']['dates'].append(date_amount)
        types['efringers']['total'] += date_amount
        date_total += date_amount
        date_amount = Ticket.objects.filter(sale__festival = request.festival, sale__created__date = date, sale__completed__isnull = False, refund__isnull = True).aggregate(Sum('cost'))['cost__sum'] or 0
        types['tickets']['dates'].append(date_amount)
        types['tickets']['total'] += date_amount
        date_total += date_amount
        totals['dates'].append(date_total)
        totals['total'] += date_total
    sales_by_type = {
        'dates': date_list,
        'types': types,
        'totals': totals,
    }

    # Tickets
    tickets = {
        'types': [],
        'totals': {
            'online': 0,
            'boxoffice': 0,
            'venue': 0,
            'total': 0,
        }
    }
    ticket_types = [tt.name for tt in TicketType.objects.filter(festival = request.festival).order_by('seqno')]
    ticket_types.append('eFringer')
    ticket_types.append('Volunteer')
    for ticket_type in ticket_types:
        query = Ticket.objects.filter(description = ticket_type, sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True)
        online = query.filter(sale__venue__isnull = True, sale__boxoffice__isnull = True).count() or 0
        boxoffice = query.filter(sale__boxoffice__isnull = False).count() or 0
        venue = query.filter(sale__venue__isnull = False).count() or 0
        tickets['types'].append({
            'description': ticket_type,
            'online': online,
            'boxoffice': boxoffice,
            'venue': venue,
            'total': online + boxoffice + venue,
        })
        tickets['totals']['online'] += online
        tickets['totals']['boxoffice'] += boxoffice
        tickets['totals']['venue'] += venue
        tickets['totals']['total'] += online + boxoffice + venue

    # Paper fringers
    fringers_sold = Fringer.objects.filter(user__isnull = True, sale__festival = request.festival, sale__completed__isnull = False).count() or 0
    fringer_tickets = Ticket.objects.filter(sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True, description = 'Fringer').count() or 0
    fringers = {
        'sold': fringers_sold,
        'used': fringer_tickets,
        'percent': ((100 * fringer_tickets) / (fringers_sold * 6)) if fringers_sold else 0,
    }

    # eFringers
    efringers_sold = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__isnull = False).count() or 0
    efringer_tickets = Ticket.objects.filter(sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True, fringer__isnull = False).count() or 0
    efringers = {
        'sold':  efringers_sold,
        'used':  efringer_tickets,
        'percent': ((100 * efringer_tickets) / (efringers_sold * 6)) if efringers_sold else 0,
    }

    # Volunteer tickets
    volunteers_earned = 0
    for volunteer in Volunteer.objects.filter(user__festival = request.festival):
        shifts = volunteer.shifts.count()
        volunteers_earned += min(shifts, 4)
    volunteer_tickets = Ticket.objects.filter(description = 'Volunteer', sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True).count() or 0
    volunteers = {
        'earned': volunteers_earned,
        'used': volunteer_tickets,
        'percent': ((100 * volunteer_tickets) / volunteers_earned) if volunteers_earned else 0,
    }

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'dates': date_list,
            'sales_by_channel': sales_by_channel,
            'sales_by_type': sales_by_type,
            'tickets': tickets,
            'fringers': fringers,
            'efringers': efringers,
            'volunteers': volunteers,
        }
        return render(request, 'reports/finance/festival_summary.html', context)

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
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Render PDF document and return it
    doc.build(story)
    return response


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def boxoffice_summary(request):

    # Get selection criteria
    boxoffice = BoxOffice.objects.get(id = int(request.GET['boxoffice']))
    date = datetime.datetime.strptime(request.GET['date'], '%Y%m%d')

    # First/last checkpoints
    periods = []
    first = Checkpoint.objects.filter(created__date = date, boxoffice = boxoffice).order_by('created').first()
    last = Checkpoint.objects.filter(created__date = date, boxoffice = boxoffice).order_by('created').last()
    if first and last and first != last:
        sales_cash = Sale.objects.filter(boxoffice = boxoffice, created__date = date).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_fringers = Fringer.objects.filter(sale__boxoffice = boxoffice, sale__created__date = date).count() or 0
        sales_buttons = Sale.objects.filter(boxoffice = boxoffice, created__date = date).aggregate(Sum('buttons'))['buttons__sum'] or 0
        periods.append({
            'title': f"Daily Summary: {first.created:%I:%M%p} to {last.created:%I:%M%p}",
            'open': first,
            'close': last,
            'sales': {
                'cash': sales_cash,
                'fringers': sales_fringers,
                'buttons': sales_buttons,
            },
            'variance': {
                'cash': last.cash - first.cash - sales_cash,
                'fringers': last.fringers - first.fringers + sales_fringers,
                'buttons': last.buttons - first.buttons + sales_buttons,
            },
        })
    else:
        periods.append({
            'title': 'Daily Summary',
            'open': first,
            'close': last,
        })

    # Intermediate checkpoints
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
                'title': f"{open.created:%I:%M%p} to {close.created:%I:%M%p}",
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
            Paragraph(f"<para><b>{period['title']}</b></para>", styles['Normal']),
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


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def venue_summary(request):

    # Get selection criteria
    venue = Venue.objects.get(id = int(request.GET['venue']))
    date = datetime.datetime.strptime(request.GET['date'], '%Y%m%d')

    # First/last checkpoints
    periods = []
    first = Checkpoint.objects.filter(created__date = date, venue = venue).order_by('created').first()
    last = Checkpoint.objects.filter(created__date = date, venue = venue).order_by('created').last()
    if first and last and first != last:
        sales_cash = Sale.objects.filter(venue = venue, created__date = date).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__date = date).count() or 0
        sales_buttons = Sale.objects.filter(venue = venue, created__date = date).aggregate(Sum('buttons'))['buttons__sum'] or 0
        periods.append({
            'title': f"Daily Summary: {first.created:%I:%M%p} to {last.created:%I:%M%p}",
            'open': first,
            'close': last,
            'sales': {
                'cash': sales_cash,
                'fringers': sales_fringers,
                'buttons': sales_buttons,
            },
            'variance': {
                'cash': last.cash - first.cash - sales_cash,
                'fringers': last.fringers - first.fringers + sales_fringers,
                'buttons': last.buttons - first.buttons + sales_buttons,
            },
        })
    else:
        periods.append({
            'title': 'Daily Summary',
            'open': first,
            'close': last,
        })

    # Individual performances
    for performance in ShowPerformance.objects.filter(show__venue = venue, date = date).order_by('time'):
        open = performance.open_checkpoint if performance.has_open_checkpoint else None
        close = performance.close_checkpoint if performance.has_close_checkpoint else None
        if open and close:
            sales_cash = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__gt = open.created, sale__created__lt = close.created).count() or 0
            sales_buttons = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum'] or 0
            periods.append({
                'title': f"{performance.time:%I:%M%p} {performance.show.name}",
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
            periods.append({
                'title': f"{performance.time:%I:%M%p} {performance.show.name}",
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
            'periods': periods,
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

    # Periods
    for period in periods:
        table_data = []
        table_styles = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]
        table_data.append((
            Paragraph(f"<para><b>{period['title']}</b></para>", styles['Normal']),
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
            f"£{ period['open'].cash }" if period.get('open', None) else '',
            f"£{ period['sales']['cash'] }" if period.get('sales', None) else '',
            f"£{ period['close'].cash }" if period.get('close', None) else '',
            f"£{ period['variance']['cash'] }" if period.get('variance', None) else '',
        ))
        table_data.append((
            'Fringers',
            period['open'].fringers if period.get('open', None) else '',
            period['sales']['fringers'] if period.get('sales', None) else '',
            period['close'].fringers if period.get('close', None) else '',
            period['variance']['fringers'] if period.get('variance', None) else '',
        ))
        table_data.append((
            'Buttons',
            period['open'].buttons if period.get('open', None) else '',
            period['sales']['buttons'] if period.get('sales', None) else '',
            period['close'].buttons if period.get('close', None) else '',
            period['variance']['buttons'] if period.get('variance', None) else '',
        ))
        if period['open'] and period['open'].notes:
            table_data.append((
                'Open notes',
                Paragraph(period['open'].notes, styles['Normal']),
            ))
            row = len(table_data) - 1
            table_styles.append(('SPAN', (1, row), (4, row)))
        if period['close'] and period['close'].notes:
            table_data.append((
                'Close notes',
                Paragraph(period['close'].notes, styles['Normal']),
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

def _get_performance_tickets_by_type(performance, ticket_types):

    tickets = {}
    payment = 0
    for tt in ticket_types:
        count = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True, description = tt['name']).count()
        tickets[tt['name']] = count
        payment += count * tt['payment']
    tickets['Total'] = Ticket.objects.filter(performance = performance, sale__completed__isnull = False, refund__isnull = True).count()
    return {
        'date': performance.date,
        'time': performance.time,
        'tickets': tickets,
        'payment': payment,
    }

def _get_show_tickets_by_type(show, ticket_types):

    performances = [_get_performance_tickets_by_type(p, ticket_types) for p in show.performances.order_by('date', 'time')]
    return {
        'name': show.name,
        'performances': performances,
        'payment': sum([p['payment'] for p in performances]),
    }

def _get_company_tickets_by_type(company, ticket_types):

    shows = [_get_show_tickets_by_type(s, ticket_types) for s in company.shows.filter(venue__is_ticketed = True).order_by('name')]
    return {
        'name': company.name,
        'shows': shows,
        'payment': sum([s['payment'] for s in shows]),
    }

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def company_payment(request):

    # Get selection criteria
    selected_company = None
    if request.GET['company']:
        selected_company = Company.objects.get(id = int(request.GET['company']))

    # Fetch data
    ticket_types = [{'name': tt.name, 'payment': tt.payment} for tt in TicketType.objects.filter(festival = request.festival).order_by('name')]
    ticket_types.append({'name': 'eFringer', 'payment': Decimal('3.00')})
    ticket_types.append({'name': 'Volunteer', 'payment': Decimal('0.00')})
    companies = []
    if selected_company:
        shows.append(_get_company_tickets_by_type(selected_company, ticket_types))
    else:
        ticketed_company_ids = Show.objects.filter(festival = request.festival, venue__is_ticketed = True).values('company_id').distinct()
        for company in Company.objects.filter(id__in = ticketed_company_ids).order_by('name'):
            companies.append(_get_company_tickets_by_type(company, ticket_types))

    # Check for HTML
    format = request.GET['format']
    if format.lower() == 'html':

        # Render tickets
        context = {
            'ticket_types': ticket_types,
            'companies': companies,
        }
        return render(request, "reports/finance/company_payment.html", context)

    # Render as PDF
    response = HttpResponse(content_type = 'application/pdf')
    response['Content-Disposition'] = 'inline'
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
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Companies
    for company in companies:

        # Header
        story.append(Paragraph(f"<para><b>{company['name']}</b>: £{company['payment']}</para>", styles['Normal']))
        for show in company['shows']:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"<para>{show['name']}: £{show['payment']}</para>", styles['Normal']))
            table_data = []
            table_styles = [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ]
            row = ['']
            for ticket_type in ticket_types:
                row.append(ticket_type['name'])
            row.append('Payment')
            table_data.append(row)
            #row = ['']
            #for ticket_type in ticket_types:
            #    row.append(f"£{ticket_type['payment']}")
            #row.append('')
            #table_data.append(row)

            # Performances
            for performance in show['performances']:
                row = [Paragraph(f"<para>{ performance['date']:%a, %b %d } at { performance['time']:%I:%M%p }</para>", styles['Normal'])]
                for ticket_type in ticket_types:
                    row.append(performance['tickets'][ticket_type['name']])
                row.append(f"£{performance['payment']}")
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
