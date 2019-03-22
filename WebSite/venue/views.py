import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.forms import formset_factory, modelformset_factory
from django.http import JsonResponse

import arrow

from core.models import User
from program.models import Show, ShowPerformance, Venue
from tickets.models import Sale, TicketType, Ticket, Fringer
from tickets.forms import CustomerForm, SaleTicketsForm, SaleTicketSubForm, SaleFringerSubForm, SaleExtrasForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def _create_customer_form(post_data = None):
    # Create form
    form = CustomerForm(post_data)
    return form

def _create_sale_tickets_form(venue, post_data = None):
    # Create form
    form = SaleTicketsForm(Show.objects.filter(venue=venue, is_cancelled = False, venue__is_ticketed = True), post_data)
    return form

def _create_sale_ticket_subforms(festival, post_data = None):
    # Build and populate ticket formset
    TicketFormset = formset_factory(SaleTicketSubForm, extra = 0)
    initial_data = [{'type_id': t.id, 'name': t.name, 'price': t.price, 'quantity': 0} for t in TicketType.objects.filter(festival=festival, is_admin = False)]
    return TicketFormset(post_data, prefix = 'ticket', initial = initial_data)

def _create_sale_fringer_subforms(sale = None, post_data = None):
    # Build and populate fringer formset
    FringerFormset = formset_factory(SaleFringerSubForm, extra = 0)
    initial_data = []
    customer_user = sale and sale.customer_user
    if customer_user:
        initial_data = [{'fringer_id': f.id, 'name': f.name, 'buy': False} for f in customer_user.fringers.all() if f.is_available]
    return FringerFormset(post_data, prefix = 'fringer', initial = initial_data)

def _create_sale_extras_form(sale = None, post_data = None):
    # Create form
    initial_data = {}
    if sale:
        initial_data = {
            'buttons': sale.buttons if sale else 0,
            'fringers': sale.fringers.count() if sale else 0,
        }
    form = SaleExtrasForm(post_data, initial = initial_data)
    return form

def _render_sale(request, venue, sale=None, customer_form=None, tickets_form=None, ticket_subforms=None, fringer_subforms=None, extras_form=None):
    context = {
        'venue': venue,
        'sale_customer_form': customer_form or _create_customer_form(),
        'sale_tickets_form': tickets_form or _create_sale_tickets_form(venue),
        'sale_ticket_subforms': ticket_subforms or _create_sale_ticket_subforms(venue.festival),
        'sale_fringer_subforms': fringer_subforms or _create_sale_fringer_subforms(sale),
        'sale_extras_form': extras_form or _create_sale_extras_form(sale),
        'sale': sale,
    }
    return render(request, "venue/_main_sale.html", context)
    
# View functions
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
def select(request):
    context = {
        'venues': Venue.objects.filter(festival=request.festival, is_ticketed=True),
    }
    return render(request, 'venue/select.html', context)
    
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
def main(request, venue_uuid, tab = 'sale'):

    # Get venue
    venue = get_object_or_404(Venue, uuid = venue_uuid)

    # Cancel any incomplete sales
    for sale in request.user.sales.filter(completed__isnull = True):
        logger.info("Incomplete sale %s cancelled", sale)
        sale.delete();

    # Render main page
    today = datetime.datetime.today()
    report_dates = [today - datetime.timedelta(days = n) for n in range(1, 14)]
    context = {
        'venue': venue,
        'tab': tab,
        'sale_customer_form': _create_customer_form(),
        'sale_tickets_form': _create_sale_tickets_form(venue),
        'sale_ticket_subforms': _create_sale_ticket_subforms(venue.festival),
        'sale_fringer_subforms': _create_sale_fringer_subforms(),
        'sale_extras_form': _create_sale_extras_form(),
        'sale': None,
        'report_today': f'{today:%Y%m%d}',
        'report_dates': [{ 'value': f'{d:%Y%m%d}', 'text': f'{d:%a, %b %d}'} for d in report_dates],
    }
    return render(request, 'venue/main.html', context)

# AJAX sale support
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_show_performances(request, sale_uuid, show_uuid):

    sale = get_object_or_404(Sale, uuid = sale_uuid)
    show = get_object_or_404(Show, uuid = show_uuid)
    html = '<option value="">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = datetime.datetime.combine(performance.date, performance.time)
        mins_remaining = (dt - datetime.datetime.now()).total_seconds() / 60
        dt = arrow.get(dt)
        if mins_remaining >= -30:
            html += f'<option value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available)</option>'
        else:
            html += f'<option disabled value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a}</option>'
    return HttpResponse(html)
    
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_start(request, venue_uuid):
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    sale = None
    form = _create_customer_form(request.POST)
    if form.is_valid():

        # Create new sale
        customer = form.cleaned_data['customer']
        sale = Sale(
            festival = venue.festival,
            venue = venue,
            user = request.user,
            customer = customer,
        )
        sale.save()
        form = None
        logger.info("Sale %s started", sale)
    return _render_sale(request, venue, sale, customer_form = form)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_add_tickets(request, sale_uuid):

    # Initialize forms
    tickets_form = None
    ticket_subforms = None
    fringer_subforms = None

    # Get sale
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    if sale.completed:
        logger.error('sale_add_tickets: sale %s completed', sale)
    else:
        # Get performance
        tickets_form = _create_sale_tickets_form(sale, request.POST)
        ticket_subforms = _create_sale_ticket_subforms(sale.festival, request.POST)
        fringer_subforms = _create_sale_fringer_subforms(sale, request.POST)
        if tickets_form.is_valid():
            performance = tickets_form.cleaned_data['performance']

            # Validate ticket and fringer subforms
            for form in fringer_subforms:
                form.performance = performance
            if ticket_subforms.is_valid() and fringer_subforms.is_valid():

                # Get total number of tickets
                tickets_requested = sum([f.cleaned_data['quantity'] for f in ticket_subforms]) + sum([1 for f in fringer_subforms if f.cleaned_data['buy']])

                # Check if there are enought tickets available
                if tickets_requested <= performance.tickets_available:

                    # Add tickets
                    for form in ticket_subforms:

                        # Get ticket type and quantity                
                        ticket_type = get_object_or_404(TicketType, pk =  form.cleaned_data['type_id'])
                        quantity = form.cleaned_data['quantity']

                        # Add tickets to sale
                        if quantity > 0:
                            for i in range(0, quantity):
                                ticket = Ticket(
                                    sale = sale,
                                    user = sale.customer_user,
                                    performance = performance,
                                    description = ticket_type.name,
                                    cost = ticket_type.price,
                                    payment = ticket_type.payment,
                                )
                                ticket.save()
                                logger.info("Sale %s ticket added: %s", sale, ticket)

                    # Add fringer tickets
                    for form in fringer_subforms:
                        if form.cleaned_data['buy']:
                            fringer = get_object_or_404(Fringer, pk =  form.cleaned_data['fringer_id'])
                            ticket = Ticket(
                                sale = sale,
                                user = sale.customer_user,
                                performance = performance,
                                fringer = fringer,
                                description = 'eFringer',
                                cost = 0,
                                payment = fringer.payment,
                            )
                            ticket.save()
                            logger.info("Sale %s ticket added: %s", sale, ticket)

                    # Reset ticket form/formset
                    tickets_form = None
                    ticket_subforms = None
                    fringer_subforms = None

                # Insufficient tickets available
                else:
                    logger.info("Sale %s tickets not available (%d requested, %d available): %s", sale, tickets_requested, performance.tickets_available, performance)
                    tickets_form.add_error(None, f"There are only {performance.tickets_available} tickets available for this perfromance.")

    return _render_sale(request, sale.venue, sale, tickets_form = tickets_form, ticket_subforms = ticket_subforms, fringer_subforms = fringer_subforms)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_update_extras(request, sale_uuid):

    # Initialize forms
    extras_form = None

    # Get sale
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    if sale.completed:
        logger.error('sale_update_extras: sale completed')
    else:
        extras_form = _create_sale_extras_form(sale, request.POST)
        if extras_form.is_valid():
            sale.buttons = extras_form.cleaned_data['buttons']
            sale.save()
            fringers = extras_form.cleaned_data['fringers']
            while (sale.fringers.count() or 0) > fringers:
                sale.fringers.first().delete()
            while (sale.fringers.count() or 0) < fringers:
                fringer = Fringer(
                    description = '6 shows for £18',
                    shows = 6,
                    cost = 18,
                    sale = sale,
                )
                fringer.save()
            logger.info("Sale %s extras updated: %d buttons, %d fringers", sale, sale.buttons, sale.fringers.count())
            extras_form = None
    return _render_sale(request, sale.venue, sale, extras_form = extras_form)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_remove_performance(request, sale_uuid, performance_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    if sale.completed:
        logger.error('sale_remove_performance: sale %s completed', sale)
    else:
        tickets = sale.tickets.count()
        for ticket in sale.tickets.all():
            if ticket.performance_id == performance.id:
                ticket.delete()
        logger.info("Sale %s performance removed (%d tickets): %s", sale, tickets, performance)
    return _render_sale(request, sale.venue, sale)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_remove_ticket(request, sale_uuid, ticket_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    if sale.completed:
        logger.error('sale_remove_ticket: sale %s completed', sale)
    elif ticket.sale != sale:
        logger.error('sale_remove_ticket: ticket %s not part of sale %s', ticket, sale)
    else:
        logger.info("Sale %s ticket removed: %s", sale, ticket)
        ticket.delete()
    return _render_sale(request, sale.venue, sale)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_complete(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    if sale.completed:
        logger.error('sale_complete: sale %s completed', sale)
    else:
        sale.amount = sale.total_cost
        sale.completed = datetime.datetime.now()
        sale.save()
        logger.info("Sale %s completed", sale)
    return _render_sale(request, sale.venue, sale)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_cancel(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    venue = sale.venue
    if sale.completed:
        logger.error('sale_cancel: sale %s completed', sale)
    else:
        logger.info("Sale %s cancelled", sale)
        sale.delete()
        sale = None
    return _render_sale(request, venue, sale)

# AJAX admission support
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def admission_shows(request, venue_uuid):
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    html = '<option value="">-- Select show --</option>'
    for show in Show.objects.filter(venue=venue):
        html += f'<option value="{show.uuid}">{show.name}</option>'
    return HttpResponse(html)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
def admission_show_performances(request, show_uuid):
    show = get_object_or_404(Show, uuid = show_uuid)
    html = '<option value="0">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = arrow.get(datetime.datetime.combine(performance.date, performance.time))
        html += f'<option value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} tickets available)</option>'
    return HttpResponse(html)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
def admission_performance_tickets(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Get tickets for this performance (exclude tickets where the sale is incomplete)
    tickets = performance.tickets.filter(sale__completed__isnull = False).order_by('id')

    # Render report
    context = {
        'performance': performance,
        'tickets': tickets,
    }
    return render(request, 'venue/admission_tickets.html', context)

# Report AJAX support
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def report_summary(request, venue_uuid, yyyymmdd):

    # Get sales and refunds for this box office
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    date = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    sales = Sale.objects.filter(venue = venue, completed__date = date).order_by('id')

    # Get aggregated figures
    sales_count = sales.count()
    sales_buttons = sales.aggregate(buttons = Coalesce(Sum('buttons'), 0))['buttons']
    sales_fringers = sales.aggregate(fringers = Coalesce(Sum('fringers__cost'), 0))['fringers']
    sales_tickets = sales.aggregate(tickets = Coalesce(Sum('tickets__cost'), 0))['tickets']
    sales_total = sales.aggregate(total = Coalesce(Sum('amount'), 0))['total']

    # Render report
    context = {
        'sales_count': sales_count,
        'sales_buttons': sales_buttons,
        'sales_fringers': sales_fringers,
        'sales_tickets': sales_tickets,
        'sales_total': sales_total,
        'balance': sales_total - refunds_total,
    }
    return render(request, 'venue/report_summary.html', context)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
def report_sales(request, venue_uuid, yyyymmdd):

    # Get completed sales for this venue
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    date = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    sales = Sale.objects.filter(venue = venue, completed__date = date).order_by('id')

    # Render report
    context = {
        'venue': venue,
        'sales': sales,
    }
    return render(request, 'venue/report_sales.html', context)

@user_passes_test(lambda u: u.is_venue or u.is_admin)
def report_sale_detail(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    context = {
        'sale': sale,
    }
    return render(request, 'venue/report_sale_detail.html', context)
