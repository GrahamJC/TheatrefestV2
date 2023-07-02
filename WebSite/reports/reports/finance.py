import os
import io
import datetime
from collections import OrderedDict
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Exists, OuterRef
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.views import View
from django.views.decorators.http import require_http_methods, require_GET
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseNotFound

import arrow

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors

import xlsxwriter as xlsx

from program.models import Company, Venue, Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, Fringer, TicketType, Ticket, Checkpoint, PayAsYouWill, Bucket
from volunteers.models import Volunteer

def date_list(from_date, to_date):

    return [from_date + datetime.timedelta(days = d) for d in range((to_date - from_date).days + 1)]


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def festival_summary(request):

    # General stuff
    venue_list = [v for v in Venue.objects.filter(festival = request.festival, is_ticketed = True).order_by('name')]
    boxoffice_list = [bo for bo in BoxOffice.objects.filter(festival = request.festival).order_by('name')]

    # Sales by channel
    dates = date_list(request.festival.boxoffice_open, request.festival.boxoffice_close)
    online_pre = Sale.objects.filter(festival = request.festival, completed__lt = dates[0], boxoffice__isnull = True, venue__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
    online = {
        'pre': online_pre,
        'dates': [],
        'total': online_pre,
    }
    venues = OrderedDict([(v.name, {'dates': [], 'total': 0}) for v in venue_list])
    boxoffices = OrderedDict([(bo.name, {'cash': {'dates': [], 'total': 0}, 'card': {'dates': [], 'total': 0}}) for bo in boxoffice_list])
    totals = {
        'pre': online_pre,
        'dates': [],
        'total': online_pre,
    }
    for date in dates:
        query = Sale.objects.filter(festival = request.festival, completed__date = date)
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
            date_amount = query.filter(boxoffice = boxoffice, transaction_type = Sale.TRANSACTION_TYPE_CASH).aggregate(Sum('amount'))['amount__sum'] or 0
            boxoffices[boxoffice.name]['cash']['dates'].append(date_amount)
            boxoffices[boxoffice.name]['cash']['total'] += date_amount
            date_total += date_amount
            date_amount = query.filter(boxoffice = boxoffice, transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP).aggregate(Sum('amount'))['amount__sum'] or 0
            boxoffices[boxoffice.name]['card']['dates'].append(date_amount)
            boxoffices[boxoffice.name]['card']['total'] += date_amount
            date_total += date_amount
        totals['dates'].append(date_total)
        totals['total'] += date_total
    sales_by_channel = {
        'dates': dates,
        'online': online,
        'venues': venues,
        'boxoffices': boxoffices,
        'totals': totals,
    }

    # Sales by type
    dates = date_list(request.festival.boxoffice_open, request.festival.boxoffice_close)
    efringers_pre = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__lt = dates[0]).aggregate(Sum('cost'))['cost__sum'] or 0
    tickets_pre = Ticket.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__lt = dates[0]).aggregate(Sum('cost'))['cost__sum'] or 0
    types = OrderedDict([
        ('buttons', {'title': 'Badges', 'pre': 0, 'dates': [], 'total': 0}),
        ('fringers', {'title': 'Paper fringers', 'pre': 0, 'dates': [], 'total': 0}),
        ('efringers', {'title': 'eFringers', 'pre': efringers_pre, 'dates': [], 'total': efringers_pre}),
        ('tickets', {'title': 'Tickets', 'pre': tickets_pre, 'dates': [], 'total': tickets_pre}),
        ('payw', {'title': 'PAYW', 'pre': 0, 'dates': [], 'total': 0}),
        ('donations', {'title': 'Donations', 'pre': 0, 'dates': [], 'total': 0}),
    ])
    totals = {
        'pre': efringers_pre + tickets_pre,
        'dates': [],
        'total': efringers_pre + tickets_pre,
    }
    for date in dates:
        date_total = 0
        date_amount = request.festival.button_price * (Sale.objects.filter(festival = request.festival, completed__date = date).aggregate(Sum('buttons'))['buttons__sum'] or 0)
        types['buttons']['dates'].append(date_amount)
        types['buttons']['total'] += date_amount
        date_total += date_amount
        date_amount = Fringer.objects.filter(user__isnull = True, sale__festival = request.festival, sale__completed__date = date).aggregate(Sum('cost'))['cost__sum'] or 0
        types['fringers']['dates'].append(date_amount)
        types['fringers']['total'] += date_amount
        date_total += date_amount
        date_amount = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__date = date).aggregate(Sum('cost'))['cost__sum'] or 0
        types['efringers']['dates'].append(date_amount)
        types['efringers']['total'] += date_amount
        date_total += date_amount
        date_amount = Ticket.objects.filter(sale__festival = request.festival, sale__completed__date = date).aggregate(Sum('cost'))['cost__sum'] or 0
        types['tickets']['dates'].append(date_amount)
        types['tickets']['total'] += date_amount
        date_total += date_amount
        date_amount = PayAsYouWill.objects.filter(sale__festival = request.festival, sale__completed__date = date, fringer_id__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
        types['payw']['dates'].append(date_amount)
        types['payw']['total'] += date_amount
        date_total += date_amount
        date_amount = Sale.objects.filter(festival = request.festival, completed__date = date).aggregate(Sum('donation'))['donation__sum'] or 0
        types['donations']['dates'].append(date_amount)
        types['donations']['total'] += date_amount
        date_total += date_amount
        totals['dates'].append(date_total)
        totals['total'] += date_total
    sales_by_type = {
        'dates': dates,
        'types': types,
        'totals': totals,
    }

    # Bucket collections
    first_performance = ShowPerformance.objects.filter(show__festival = request.festival, show__venue__is_ticketed = False).order_by('date', 'time').first()
    last_performance = ShowPerformance.objects.filter(show__festival = request.festival, show__venue__is_ticketed = False).order_by('date', 'time').last()
    dates = date_list(first_performance.date, last_performance.date)
    types = OrderedDict([
        ('cash', {'title': 'Cash', 'dates': [], 'post': 0, 'total': 0}),
        ('fringers', {'title': 'Paper fringers', 'dates': [], 'post': 0, 'total': 0}),
        ('boxoffice', {'title': 'Box office', 'dates': [], 'post': 0, 'total': 0}),
        ('efringers', {'title': 'eFringers', 'dates': [], 'post': 0, 'total': 0}),
    ])
    totals = {
        'dates': [],
        'post': 0,
        'total': 0,
    }
    for date in dates:
        date_total = 0
        date_amount = Bucket.objects.filter(company__festival = request.festival, date = date).aggregate(Sum('cash'))['cash__sum'] or 0
        types['cash']['dates'].append(date_amount)
        types['cash']['total'] += date_amount
        date_total += date_amount
        date_amount = 4 * (Bucket.objects.filter(company__festival = request.festival, date = date).aggregate(Sum('fringers'))['fringers__sum'] or 0)
        types['fringers']['dates'].append(date_amount)
        types['fringers']['total'] += date_amount
        date_total += date_amount
        date_amount = PayAsYouWill.objects.filter(sale__festival = request.festival, sale__completed__date = date, fringer_id__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
        types['boxoffice']['dates'].append(date_amount)
        types['boxoffice']['total'] += date_amount
        date_total += date_amount
        date_amount = PayAsYouWill.objects.filter(sale__festival = request.festival, sale__completed__date = date, fringer_id__isnull = False).aggregate(Sum('amount'))['amount__sum'] or 0
        types['efringers']['dates'].append(date_amount)
        types['efringers']['total'] += date_amount
        date_total += date_amount
        totals['dates'].append(date_total)
        totals['total'] += date_total
    efringers_post = PayAsYouWill.objects.filter(sale__festival = request.festival, sale__completed__date__gt = dates[-1], fringer_id__isnull = False).aggregate(Sum('amount'))['amount__sum'] or 0
    types['efringers']['post'] = efringers_post
    types['efringers']['total'] += efringers_post
    totals['post'] = efringers_post
    totals['total'] += efringers_post
    buckets = {
        'dates': dates,
        'types': types,
        'totals': totals
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
    fringer_total = 6 * fringers_sold
    fringer_tickets = Ticket.objects.filter(sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True, description = 'Fringer').count() or 0
    fringer_buckets = Bucket.objects.filter(company__festival = request.festival).aggregate(Sum('fringers'))['fringers__sum'] or 0
    fringer_unused = fringer_total - fringer_tickets - fringer_buckets
    fringers = {
        'sold': fringers_sold,
        'tickets': fringer_tickets,
        'tickets_pcent': ((100 * fringer_tickets) / fringer_total) if fringers_sold else 0,
        'buckets': fringer_buckets,
        'buckets_pcent': ((100 * fringer_buckets) / fringer_total) if fringers_sold else 0,
        'unused': fringer_unused,
        'unused_pcent': ((100 * fringer_unused) / fringer_total) if fringers_sold else 0,
    }

    # eFringers
    efringers_sold = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__isnull = False).count() or 0
    efringer_total = Fringer.objects.filter(user__isnull = False, sale__festival = request.festival, sale__completed__isnull = False).aggregate(Sum('shows'))['shows__sum'] or 0
    efringer_tickets = Ticket.objects.filter(sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True, fringer__isnull = False).count() or 0
    efringer_buckets = PayAsYouWill.objects.filter(show__festival = request.festival, sale__completed__isnull = False, fringer__isnull = False).count() or 0
    efringer_unused = efringer_total - efringer_tickets - efringer_buckets
    efringers = {
        'sold':  efringers_sold,
        'tickets': efringer_tickets,
        'tickets_pcent': ((100 * efringer_tickets) / efringer_total) if efringers_sold else 0,
        'buckets': efringer_buckets,
        'buckets_pcent': ((100 * efringer_buckets) / efringer_total) if efringers_sold else 0,
        'unused': efringer_unused,
        'unused_pcent': ((100 * efringer_unused) / efringer_total) if efringers_sold else 0,
    }

    # Volunteer tickets
    volunteers_earned = 0
    for volunteer in Volunteer.objects.filter(user__festival = request.festival):
        volunteers_earned += volunteer.comps_earned
    volunteer_tickets = Ticket.objects.filter(description = 'Volunteer', sale__festival = request.festival, sale__completed__isnull = False, refund__isnull = True).count() or 0
    volunteer_unused = volunteers_earned - volunteer_tickets
    volunteers = {
        'earned': volunteers_earned,
        'tickets': volunteer_tickets,
        'tickets_pcent': ((100 * volunteer_tickets) / volunteers_earned) if volunteers_earned else 0,
        'buckets': 0,
        'buckets_pcent': 0,
        'unused': volunteer_unused,
        'unused_pcent': ((100 * volunteer_unused) / volunteers_earned) if volunteers_earned else 0,
    }

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'sales_by_channel': sales_by_channel,
            'sales_by_type': sales_by_type,
            'buckets': buckets,
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
        pagesize = landscape(A4),
        leftMargin = 2.5*cm,
        rightMargin = 2.5*cm,
        topMargin = 2.5*cm,
        bottomMargin = 2.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Sales by channel
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))
    story.append(Paragraph('<b>Sales by Channel</b>'))
    story.append(Spacer(1, 0.5*cm))
    table_data = []
    colWidths = [4*cm, 2*cm]
    for date in sales_by_channel['dates']:
        colWidths.append(2*cm)
    colWidths.append(2*cm)
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, (0,0,0)),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, (0,0,0)),
    ]
    row = ['', 'Pre\nSales']
    for date in sales_by_channel['dates']:
        row.append(f'{date:%a\n%d-%b}')
    row.append('Total')
    table_data.append(row)
    row = ['Online', f'£{sales_by_channel["online"]["pre"]:.0f}']
    for amount in sales_by_channel['online']['dates']:
        row.append(f'£{amount:.0f}')
    row.append(f'£{sales_by_channel["online"]["total"]:.0f}')
    table_data.append(row)
    for boxoffice in boxoffice_list:
        row = [boxoffice.name + ' (cash)', '£0']
        for amount in sales_by_channel['boxoffices'][boxoffice.name]['cash']['dates']:
            row.append(f'£{amount:.0f}')
        row.append(f'£{sales_by_channel["boxoffices"][boxoffice.name]["cash"]["total"]:.0f}')
        table_data.append(row)
        row = [boxoffice.name + ' (card)', '£0']
        for amount in sales_by_channel['boxoffices'][boxoffice.name]['card']['dates']:
            row.append(f'£{amount:.0f}')
        row.append(f'£{sales_by_channel["boxoffices"][boxoffice.name]["card"]["total"]:.0f}')
        table_data.append(row)
    for venue in venue_list:
        row = [venue.name, '£0']
        for amount in sales_by_channel['venues'][venue.name]['dates']:
            row.append(f'£{amount:.0f}')
        row.append(f'£{sales_by_channel["venues"][venue.name]["total"]:.0f}')
        table_data.append(row)
    row = ['', f'£{sales_by_channel["totals"]["pre"]:.0f}']
    for amount in sales_by_channel['totals']['dates']:
        row.append(f'£{amount:.0f}')
    row.append(f'£{sales_by_channel["totals"]["total"]:.0f}')
    table_data.append(row)
    table = Table(
        table_data,
        colWidths = colWidths,
        style = table_styles,
    )
    story.append(table)

    # Sales by type
    story.append(PageBreak())
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))
    story.append(Paragraph('<b>Sales by Type</b>'))
    story.append(Spacer(1, 0.5*cm))
    table_data = []
    colWidths = [4*cm, 2*cm]
    for date in sales_by_type['dates']:
        colWidths.append(2*cm)
    colWidths.append(2*cm)
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, (0,0,0)),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, (0,0,0)),
    ]
    row = ['', 'Pre\nSales']
    for date in sales_by_type['dates']:
        row.append(f'{date:%a\n%d-%b}')
    row.append('Total')
    table_data.append(row)
    for type in sales_by_type['types'].values():
        row = [type['title'], f'£{type["pre"]:.0f}']
        for amount in type['dates']:
            row.append(f'£{amount:.0f}')
        row.append(f'£{type["total"]:.0f}')
        table_data.append(row)
    row = ['', f'£{sales_by_type["totals"]["pre"]:.0f}']
    for amount in sales_by_type['totals']['dates']:
        row.append(f'£{amount:.0f}')
    row.append(f'£{sales_by_type["totals"]["total"]:.0f}')
    table_data.append(row)
    table = Table(
        table_data,
        colWidths = colWidths,
        style = table_styles,
    )
    story.append(table)

    # Bucket collections
    story.append(PageBreak())
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))
    story.append(Paragraph('<b>Bucket Collections</b>'))
    story.append(Spacer(1, 0.5*cm))
    table_data = []
    colWidths = [4*cm]
    for date in buckets['dates']:
        colWidths.append(2*cm)
    colWidths.append(2*cm)
    colWidths.append(2*cm)
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, (0,0,0)),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, (0,0,0)),
    ]
    row = ['']
    for date in buckets['dates']:
        row.append(f'{date:%a\n%d-%b}')
    row.append('Post-\nfestival')
    row.append('Total')
    table_data.append(row)
    for type in buckets['types'].values():
        row = [type['title']]
        for amount in type['dates']:
            row.append(f'£{amount:.0f}')
        row.append(f'£{type["post"]:.0f}')
        row.append(f'£{type["total"]:.0f}')
        table_data.append(row)
    row = ['']
    for amount in buckets['totals']['dates']:
        row.append(f'£{amount:.0f}')
    row.append(f'£{buckets["totals"]["post"]:.0f}')
    row.append(f'£{buckets["totals"]["total"]:.0f}')
    table_data.append(row)
    table = Table(
        table_data,
        colWidths = colWidths,
        style = table_styles,
    )
    story.append(table)

    # Tickets by type
    story.append(PageBreak())
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))
    story.append(Paragraph('<b>Tickets by Type</b>'))
    story.append(Spacer(1, 0.5*cm))
    table_data = [('Type', 'Online', 'Box Office', 'Venue', 'Total')]
    colWidths = [4*cm, 3*cm, 3*cm, 3*cm, 3*cm]
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, (0,0,0)),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, (0,0,0)),
    ]
    for type in tickets['types']:
        table_data.append([
            type['description'],
            f'{type["online"]}',
            f'{type["boxoffice"]}',
            f'{type["venue"]}',
            f'{type["total"]}',
        ])
    table_data.append([
        '',
        f'{tickets["totals"]["online"]}',
        f'{tickets["totals"]["boxoffice"]}',
        f'{tickets["totals"]["venue"]}',
        f'{tickets["totals"]["total"]}',
    ])
    table = Table(
        table_data,
        colWidths = colWidths,
        style = table_styles,
    )
    story.append(table)

    # Fringer/Volunteer ticket use
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph('<b>Fringer/Volunteer Tickets Use</b>'))
    story.append(Spacer(1, 0.5*cm))
    table_data = [('', 'Sold/Earned', 'Tickets', 'Buckets', 'Unused')]
    colWidths = [4*cm, 3*cm, 3*cm, 3*cm, 3*cm]
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, (0,0,0)),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
    ]
    table_data.append([
        'Paper fringers',
        f'{fringers["sold"]}',
        f'{fringers["tickets"]} ({fringers["tickets_pcent"]:.1f}%)',
        f'{fringers["buckets"]} ({fringers["buckets_pcent"]:.1f}%)',
        f'{fringers["unused"]} ({fringers["unused_pcent"]:.1f}%)',
    ])
    table_data.append([
        'eFringers',
        f'{efringers["sold"]}',
        f'{efringers["tickets"]} {efringers["tickets_pcent"]:.1f}%)',
        f'{efringers["buckets"]} {efringers["buckets_pcent"]:.1f}%)',
        f'{efringers["unused"]} {efringers["unused_pcent"]:.1f}%)',
    ])
    table_data.append([
        'Volunteers',
        f'{volunteers["earned"]}',
        f'{volunteers["tickets"]} ({volunteers["tickets_pcent"]:.1f}%)',
        f'{volunteers["buckets"]} ({volunteers["buckets_pcent"]:.1f}%)',
        f'{volunteers["unused"]} ({volunteers["unused_pcent"]:.1f}%)',
    ])
    table = Table(
        table_data,
        colWidths = colWidths,
        style = table_styles,
    )
    story.append(table)

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
        sales_cash = Sale.objects.filter(boxoffice = boxoffice, created__date = date, transaction_type = Sale.TRANSACTION_TYPE_CASH).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_card = Sale.objects.filter(boxoffice = boxoffice, created__date = date, transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_fringers = Fringer.objects.filter(sale__boxoffice = boxoffice, sale__created__date = date).count() or 0
        sales_buttons = Sale.objects.filter(boxoffice = boxoffice, created__date = date).aggregate(Sum('buttons'))['buttons__sum'] or 0
        refunds_cash = Refund.objects.filter(boxoffice = boxoffice, created__date = date).aggregate(Sum('amount'))['amount__sum'] or 0
        periods.append({
            'title': f"Daily Summary: {first.created.astimezone():%I:%M%p} to {last.created.astimezone():%I:%M%p}",
            'open': first,
            'close': last,
            'sales': {
                'cash': sales_cash,
                'card': sales_card,
                'fringers': sales_fringers,
                'buttons': sales_buttons,
            },
            'refunds': {
                'cash': refunds_cash,
            },
            'variance': {
                'cash': last.cash - first.cash - sales_cash + refunds_cash,
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
            sales_cash = Sale.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created, transaction_type = Sale.TRANSACTION_TYPE_CASH).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_card = Sale.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created, transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_fringers = Fringer.objects.filter(sale__boxoffice = boxoffice, sale__created__gt = open.created, sale__created__lt = close.created).count() or 0
            sales_buttons = Sale.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum'] or 0
            refunds_cash = Refund.objects.filter(boxoffice = boxoffice, created__gt = open.created, created__lt = close.created).aggregate(Sum('amount'))['amount__sum'] or 0
            periods.append({
                'title': f"{open.created.astimezone():%I:%M%p} to {close.created.astimezone():%I:%M%p}",
                'open': open,
                'close': close,
                'sales': {
                    'cash': sales_cash,
                    'card': sales_card,
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
            'Card',
            '',
            period['sales']['card'] if period.get('sales', None) else '',
            '',
            '',
            '',
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
        sales_cash = Sale.objects.filter(venue = venue, created__date = date, transaction_type = Sale.TRANSACTION_TYPE_CASH).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_card = Sale.objects.filter(venue = venue, created__date = date, transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP).aggregate(Sum('amount'))['amount__sum'] or 0
        sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__date = date).count() or 0
        sales_buttons = Sale.objects.filter(venue = venue, created__date = date).aggregate(Sum('buttons'))['buttons__sum'] or 0
        periods.append({
            'title': f"Daily Summary: {first.created.astimezone():%I:%M%p} to {last.created.astimezone():%I:%M%p}",
            'open': first,
            'close': last,
            'sales': {
                'cash': sales_cash,
                'card': sales_card,
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
            sales_cash = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created, transaction_type = Sale.TRANSACTION_TYPE_CASH).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_card = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created, transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP).aggregate(Sum('amount'))['amount__sum'] or 0
            sales_fringers = Fringer.objects.filter(sale__venue = venue, sale__created__gt = open.created, sale__created__lt = close.created).count() or 0
            sales_buttons = Sale.objects.filter(venue = venue, created__gt = open.created, created__lt = close.created).aggregate(Sum('buttons'))['buttons__sum'] or 0
            periods.append({
                'title': f"{performance.time:%I:%M%p} {performance.show.name}",
                'open': open,
                'close': close,
                'sales': {
                    'cash': sales_cash,
                    'card': sales_card,
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
            'Card',
            '',
            period['sales']['card'] if period.get('sales', None) else '',
            '',
            '',
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

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def refunds(request):

    # Cash rRefunds
    refunds = []
    for refund in Refund.objects.filter(festival = request.festival, completed__isnull = False, amount__gt = 0).order_by('id'):
        refunds.append({
            'id': refund.id,
            'created': refund.created,
            'boxoffice': refund.boxoffice.name,
            'user': refund.user.email,
            'reason': refund.reason,
            'amount': refund.amount,
            'tickets': [ticket for ticket in Ticket.objects.filter(refund = refund, cost__gt = 0).order_by('id')]
        })

    # Performances with refunded/cancelled tickets
    performances = []
    for performance in ShowPerformance.objects.filter(Exists(Ticket.objects.filter(performance_id = OuterRef('id'), refund__completed__isnull = False)), show__festival = request.festival, show__venue__is_ticketed = True).order_by('show__name', 'date', 'time'):
        performances.append({
            'show': performance.show.name,
            'date': performance.date,
            'time': performance.time,
            'tickets': [ticket for ticket in Ticket.objects.filter(performance = performance, refund__completed__isnull = False).order_by('id')]
        })

    # Check for HTML
    format = request.GET['format']
    if format == 'HTML':

        # Render HTML
        context = {
            'performances': performances,
            'refunds': refunds,
        }
        return render(request, 'reports/finance/refunds.html', context)

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


def company_payment_pdf(request, companies, ticket_types):

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

def get_ticket_payment(company, ticket_types, name):

    ticket_type = next(filter(lambda tt: tt['name'] == name, ticket_types), None)
    tickets = 0
    for show in company['shows']:
        for performance in show['performances']:
            tickets += performance['tickets'][ticket_type['name']] 
    return tickets * ticket_type['payment']

def company_payment_xlsx(request, companies, ticket_types):

        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()

        # Even though the final file will be in memory the module uses temp
        # files during assembly for efficiency. To avoid this on servers that
        # don't allow temp files, for example the Google APP Engine, set the
        # 'in_memory' Workbook() constructor option as shown in the docs.
        workbook = xlsx.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Column headers
        worksheet.write(0, 0, 'Company')
        worksheet.write(0, 1, 'Deposit')
        worksheet.write(0, 2, 'Full')
        worksheet.write(0, 3, 'Concession')
        worksheet.write(0, 4, 'Fringers')
        worksheet.write(0, 5, 'eFringers')
        worksheet.write(0, 6, 'Adjustment')
        worksheet.write(0, 7, 'Total')
        worksheet.write(0, 8, 'Notes')

        # Company data
        row = 1
        for company in companies:
            worksheet.write(row, 0, company['name'])
            worksheet.write(row, 2, get_ticket_payment(company, ticket_types, 'Full'))
            worksheet.write(row, 3, get_ticket_payment(company, ticket_types, 'Concession'))
            worksheet.write(row, 4, get_ticket_payment(company, ticket_types, 'Fringer'))
            worksheet.write(row, 5, get_ticket_payment(company, ticket_types, 'eFringer'))
            worksheet.write(row, 6, 0)
            worksheet.write_formula(row, 7, f'=SUM({xlsx.utility.xl_range(row, 1, row, 6)})')
            row += 1

        # Close the workbook before sending the data.
        workbook.close()

        # Rewind the buffer.
        output.seek(0)

        # Set up the Http response.
        filename = 'company_payment.xlsx'
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def company_payment(request):

    # Get selection criteria
    selected_company = None
    if request.GET['company']:
        selected_company = Company.objects.get(id = int(request.GET['company']))

    # Ticketed venues
    ticket_types = [{'name': tt.name, 'payment': tt.payment} for tt in TicketType.objects.filter(festival = request.festival).order_by('name')]
    ticket_types.append({'name': 'eFringer', 'payment': Decimal('4.00')})
    ticket_types.append({'name': 'Volunteer', 'payment': Decimal('0.00')})
    companies = []
    if selected_company:
        companies.append(_get_company_tickets_by_type(selected_company, ticket_types))
    else:
        company_ids = Show.objects.filter(festival = request.festival, venue__is_ticketed = True).values('company_id').distinct()
        for company in Company.objects.filter(id__in = company_ids).order_by('name'):
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

    # PDF
    elif format.lower() == 'pdf':
        return company_payment_pdf(request, companies, ticket_types)

    # Excel
    elif format.lower() == 'xlsx':
        return company_payment_xlsx(request, companies, ticket_types)

    # Unsupported format
    return HttpResponseNotFound()


def _get_performance_buckets(performance):

    cash = Bucket.objects.filter(performance = performance).aggregate(Sum('cash'))['cash__sum'] or 0
    fringers = 4 * (Bucket.objects.filter(performance = performance).aggregate(Sum('fringers'))['fringers__sum'] or 0)
    return {
        'date': performance.date,
        'time': performance.time,
        'cash': cash,
        'fringers': fringers,
        'boxoffice': 0,
        'efringers': 0,
        'total': cash + fringers,
    }

def _get_show_buckets(show):

    performances = [_get_performance_buckets(p) for p in show.performances.order_by('date', 'time')]
    other_cash = Bucket.objects.filter(show = show, performance__isnull = True).aggregate(Sum('cash'))['cash__sum'] or 0
    other_fringers = 4 * (Bucket.objects.filter(show = show, performance__isnull = True).aggregate(Sum('fringers'))['fringers__sum'] or 0)
    other_boxoffice = PayAsYouWill.objects.filter(show = show, sale__completed__isnull = False, fringer__isnull = True).aggregate(Sum('amount'))['amount__sum'] or 0
    other_efringers = PayAsYouWill.objects.filter(show = show, sale__completed__isnull = False, fringer__isnull = False).aggregate(Sum('amount'))['amount__sum'] or 0
    other = {
        'cash': other_cash,
        'fringers': other_fringers,
        'boxoffice': other_boxoffice,
        'efringers': other_efringers,
        'total': other_cash + other_fringers + other_boxoffice + other_efringers,
    }
    return {
        'name': show.name,
        'performances': performances,
        'other': other,
        'total': sum([p['total'] for p in performances]) + other['total'],
    }

def _get_company_buckets(company):

    shows = [_get_show_buckets(s) for s in company.shows.filter(venue__is_ticketed = False).order_by('name')]
    return {
        'name': company.name,
        'shows': shows,
        'total': sum([s['total'] for s in shows]),
    }

def company_buckets_pdf(request, companies, bucket_types):

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
        story.append(Paragraph(f"<para><b>{company['name']}</b>: £{company['total']}</para>", styles['Normal']))
        for show in company['shows']:
            story.append(Spacer(1, 0.2*cm))
            story.append(Paragraph(f"<para>{show['name']}: £{show['total']}</para>", styles['Normal']))
            table_data = []
            table_styles = [
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ]
            row = ['']
            for bucket_type in bucket_types:
                row.append(bucket_type['title'])
            row.append('Total')
            table_data.append(row)

            # Performances
            for performance in show['performances']:
                row = [Paragraph(f"<para>{ performance['date']:%a, %b %d } at { performance['time']:%I:%M%p }</para>", styles['Normal'])]
                for bucket_type in bucket_types:
                    row.append(f'£{performance[bucket_type["name"]]}')
                row.append(f"£{performance['total']}")
                table_data.append(row)

            # Other
            if show['other']['total'] > 0:
                row = [Paragraph(f"<para>Other</para>", styles['Normal'])]
                for bucket_type in bucket_types:
                    row.append(f'£{show["other"][bucket_type["name"]]}')
                row.append(f"£{show['other']['total']}")
                table_data.append(row)

            # Column widths
            colWidths = [5*cm]
            for bucket_type in bucket_types:
                colWidths.append((11 / len(bucket_types))*cm)
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

def get_bucket_total(company, bucket_type):

    total = 0
    for show in company['shows']:
        for performance in show['performances']:
            total += performance[bucket_type] 
        total += show['other'][bucket_type]
    return total

def company_buckets_xlsx(request, companies, ticket_types):

        # Create an in-memory output file for the new workbook.
        output = io.BytesIO()

        # Even though the final file will be in memory the module uses temp
        # files during assembly for efficiency. To avoid this on servers that
        # don't allow temp files, for example the Google APP Engine, set the
        # 'in_memory' Workbook() constructor option as shown in the docs.
        workbook = xlsx.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Column headers
        worksheet.write(0, 0, 'Company')
        worksheet.write(0, 1, 'Cash')
        worksheet.write(0, 2, 'Fringers')
        worksheet.write(0, 3, 'Box office')
        worksheet.write(0, 4, 'eFringers')
        worksheet.write(0, 5, 'Total')
        worksheet.write(0, 6, 'Notes')

        # Company data
        row = 1
        for company in companies:
            worksheet.write(row, 0, company['name'])
            worksheet.write(row, 1, get_bucket_total(company, 'cash'))
            worksheet.write(row, 2, get_bucket_total(company, 'fringers'))
            worksheet.write(row, 3, get_bucket_total(company, 'boxoffice'))
            worksheet.write(row, 4, get_bucket_total(company, 'efringers'))
            worksheet.write_formula(row, 5, f'=SUM({xlsx.utility.xl_range(row, 1, row, 4)})')
            row += 1

        # Close the workbook before sending the data.
        workbook.close()

        # Rewind the buffer.
        output.seek(0)

        # Set up the Http response.
        filename = 'company_buckets.xlsx'
        response = HttpResponse(
            output,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def company_buckets(request):

    # Get selection criteria
    selected_company = None
    if request.GET['company']:
        selected_company = Company.objects.get(id = int(request.GET['company']))

    # Bucket donation types
    bucket_types = [
        {'name': 'cash', 'title': 'Cash' },
        {'name': 'fringers', 'title': 'Paper fringers' },
        {'name': 'boxoffice', 'title': 'Box office' },
        {'name': 'efringers', 'title': 'eFringers' },
    ]

    # Alt space companies
    companies = []
    if selected_company:
        companies.append(_get_company_buckets(selected_company))
    else:
        company_ids = Show.objects.filter(festival = request.festival, venue__is_ticketed = False).values('company_id').distinct()
        for company in Company.objects.filter(id__in = company_ids).order_by('name'):
            companies.append(_get_company_buckets(company))

    # Check for HTML
    format = request.GET['format']
    if format.lower() == 'html':

        # Render tickets
        context = {
            'bucket_types': bucket_types,
            'companies': companies,
        }
        return render(request, "reports/finance/company_buckets.html", context)

    # PDF
    elif format.lower() == 'pdf':
        return company_buckets_pdf(request, companies, bucket_types)

    # Excel
    elif format.lower() == 'xlsx':
        return company_buckets_xlsx(request, companies, bucket_types)

    # Unsupported format
    return HttpResponseNotFound()


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
    for performance in sale.ticket_performances:
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
