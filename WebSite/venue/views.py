import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.forms import formset_factory, modelformset_factory
from django.http import JsonResponse

import arrow

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from core.models import User
from program.models import Show, ShowPerformance, Venue
from tickets.models import Sale, TicketType, Ticket, Fringer, Checkpoint
from .forms import OpenCheckpointForm, SaleStartForm, SaleForm, CloseCheckpointForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def create_open_form(venue, performance, post_data = None):

    # Create form
    form = OpenCheckpointForm(post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_action = reverse('venue:performance_open', args = [venue.uuid, performance.uuid])
    form.helper.layout = Layout(
        Field('cash'),
        Field('buttons'),
        Field('fringers'),
        Field('notes'),
        Submit('open', 'Open Performance'),
    )

    # Return form
    return form


def create_close_form(venue, performance, post_data = None):

    # Create form
    form = CloseCheckpointForm(post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_action = reverse('venue:performance_close', args = [venue.uuid, performance.uuid])
    form.helper.layout = Layout(
            Field('audience'),
            Field('cash'),
            Field('buttons'),
            Field('fringers'),
            Field('notes'),
            Submit('close', 'Close Performance'),
    )

    # Return form
    return form


def create_sale_start_form(venue, performance, post_data = None):

    # Create form
    form = SaleStartForm(post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-start-form'
    form.helper.layout = Layout(
        Field('customer'),
        Button('start', 'Start', css_class = 'btn-primary',  onclick = 'sale_start()'),
    )

    # Return form
    return form


def create_sale_form(performance, sale, post_data = None):

    # Get initial values from sale
    initial_data = {
        'buttons': sale.buttons,
        'fringers': sale.fringers.count(),
    }

    # Get ticket types and efringers and add initial values
    ticket_types = []
    for ticket_type in sale.festival.ticket_types.order_by('name'):
        ticket_types.append(ticket_type)
        initial_data[SaleForm.ticket_field_name(ticket_type)] = sale.tickets.filter(description = ticket_type.name).count()
    efringers = []
    if sale.customer_user:
        for efringer in sale.customer_user.fringers.order_by('name'):
            is_in_sale = sale.tickets.filter(fringer = efringer).exists()
            if is_in_sale or efringer.is_available(performance):
                efringers.append(efringer)
                initial_data[SaleForm.efringer_field_name(efringer)] = is_in_sale

    # Create form
    form = SaleForm(ticket_types, efringers, post_data, initial = initial_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-8 py-0'
    form.helper.field_class = 'col-4'
    if form.efringers:
        form.helper.layout = Layout(
            Fieldset('Tickets', *(form.ticket_field_name(tt) for tt in form.ticket_types)),
            Fieldset('Use eFringers', *(form.efringer_field_name(ef) for ef in form.efringers)),
            Fieldset('Extras', 'buttons', 'fringers'),
            Button('update', 'Update', css_class = 'btn-primary',  onclick = f"sale_update('{sale.uuid}')"),
        )
    else:
        form.helper.layout = Layout(
            Fieldset('Tickets', *(form.ticket_field_name(tt) for tt in form.ticket_types)),
            Fieldset('Extras', 'buttons', 'fringers'),
            Button('update', 'Update', css_class = 'btn-primary',  onclick = f"sale_update('{sale.uuid}')"),
        )

    # Return form
    return form


def render_main(request, venue, performance, tab, sale, open_form, start_form, close_form):

    # Get sales made between open/close checkpoints
    sales = Sale.objects.none()
    if performance.has_close_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created, created__lte = performance.close_checkpoint.created).order_by('-id')
    elif performance.has_open_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created).order_by('-id')

    # Render page
    context = {
        'venue': venue,
        'tab': tab if tab else 'open',
        'performances': ShowPerformance.objects.filter(show__venue = venue).order_by('date', 'time'),
        'current_performance': performance,
        'sales': sales,
        'current_sale': None,
        'open_form': open_form,
        'start_form': start_form,
        'close_form': close_form,
        'tickets': performance.tickets.order_by('id'),
    }
    return render(request, 'venue/main.html', context)


def render_main_sales(request, venue, performance, sale, start_form, sale_form):

    # Get sales made between open/close checkpoints
    sales = Sale.objects.none()
    if performance.has_close_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created, created__lte = performance.close_checkpoint.created).order_by('-id')
    elif performance.has_open_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created).order_by('-id')

    # Render sales
    context = {
        'venue': venue,
        'current_performance': performance,
        'sales': sales,
        'current_sale': sale,
        'start_form': start_form,
        'sale_form': sale_form,
    }
    return render(request, "venue/_main_sales.html", context)


def render_main_tickets(request, venue, performance):

    # Get tickets sold at central box office or online
    tickets = performance.tickets.filter(sale__venue__isnull = True).order_by('id')

    # Render tickets
    context = {
        'venue': venue,
        'current_performance': performance,
        'tickets': tickets,
    }
    return render(request, "venue/_main_tickets.html", context)

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
@transaction.atomic
def main(request, venue_uuid, performance_uuid = None):

    # Get venue and performance taking the first of:
    #   The performance specified in the request
    #   The next performance (i.e. the first performance with no close checkpoint)
    #   The last performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = None
    next_performance = ShowPerformance.objects.filter(show__venue = venue, close_checkpoint = None).order_by('date', 'time').first()
    if performance_uuid:
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    elif next_performance:
        performance = next_performance
    else:
        performance = ShowPerformance.objects.filter(show__venue = venue).order_by('date', 'time').last()
    assert performance.show.venue == venue

    # Delete any imcomplete sales for this venue
    for sale in venue.sales.filter(completed__isnull = True):
        logger.info("Sale %s auto-cancelled", sale)
        sale.delete()

    # Initialize forms
    open_form = None
    close_form = None
    start_form = None
    if performance == next_performance:
        if not performance.has_open_checkpoint:
            open_form = create_open_form(venue, performance)
        elif not performance.has_close_checkpoint:
            close_form = create_close_form(venue, performance)
    if performance.has_open_checkpoint and not performance.has_close_checkpoint:
        start_form = create_sale_start_form(venue, performance)

    # Render page
    return render_main(request, venue, performance, 'open', None, open_form, start_form, close_form)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_open(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert not performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Process open form
    start_form = None
    close_form = None
    tab = 'open'
    open_form = create_open_form(venue, performance, request.POST)
    if open_form.is_valid():

        # Create open checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            open_performance = performance,
            cash = open_form.cleaned_data['cash'],
            buttons = open_form.cleaned_data['buttons'],
            fringers = open_form.cleaned_data['fringers'],
            notes = open_form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info("Open checkpoint completed for %s (%s)", performance.show.name, performance)
        messages.success(request, "Open checkpoint completed")

        # Destroy open form and create start_form
        open_form = None
        start_form = create_sale_start_form(venue, performance)
        close_form = create_close_form(venue, performance)
        tab = 'sales'

    # Render page
    return render_main(request, venue, performance, tab, None, open_form, start_form, close_form)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_close(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Process close form
    start_form = create_sale_start_form(venue, performance)
    close_form = create_close_form(venue, performance, request.POST)
    if close_form.is_valid():

        # Record audience tokens
        performance.audience = close_form.cleaned_data['audience']
        performance.save()

        # Create close checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            close_performance = performance,
            cash = close_form.cleaned_data['cash'],
            buttons = close_form.cleaned_data['buttons'],
            fringers = close_form.cleaned_data['fringers'],
            notes = close_form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info("Close checkpoint completed for {%s} on {%s}", performance.show.name, performance)
        messages.success(request, "Close checkpoint completed")

        # Destroy forms
        start_form = None
        close_form = None

    # Render page
    return render_main(request, venue, performance, 'close', None, None, start_form, close_form)


# AJAX sale API
@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_new(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Create start sale form
    start_form = create_sale_start_form(venue, performance)

    # Render sale
    return  render_main_sales(request, venue, performance, None, start_form, None)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_select(request, venue_uuid, performance_uuid, sale_uuid):

    # Get venue, performance and sale
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Create sale form (if the performance is not closed)
    sale_form = create_sale_form(performance, sale) if not performance.has_close_checkpoint else None

    # Render sale
    return  render_main_sales(request, venue, performance, sale, None, sale_form)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_start(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Initialize sale
    sale = None
    sale_form = None

    # Process start sale form
    start_form = create_sale_start_form(venue, performance, request.POST)
    if start_form.is_valid():

        # Create new sale
        customer = start_form.cleaned_data['customer']
        sale = Sale(
            festival = request.festival,
            venue = venue,
            user = request.user,
            customer = customer,
        )
        sale.save()
        logger.info("Sale %s started", sale)

        # Discard start form and create sale form
        start_form = None
        sale_form = create_sale_form(performance, sale)

    # Render sale
    return  render_main_sales(request, venue, performance, sale, start_form, sale_form)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_update(request, venue_uuid, performance_uuid, sale_uuid):

    # Get venue, performance and sale
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Process sale form
    sale_form = create_sale_form(performance, sale, request.POST)
    if sale_form.is_valid():

        # Check if there are sufficient tickets
        sale_tickets = sale.tickets.count()
        form_tickets = sale_form.ticket_count
        available_tickets = performance.tickets_available
        if (form_tickets - sale_tickets) <= available_tickets:

            # Adjust ticket numbers
            for ticket_type in sale_form.ticket_types:
                form_tickets = sale_form.cleaned_data[SaleForm.ticket_field_name(ticket_type)]
                while sale.tickets.filter(description = ticket_type.name).count() > form_tickets:
                    sale_ticket = sale.tickets.filter(description = ticket_type.name).last()
                    logger.info("Sale %s ticket deleted: %s", sale, sale_ticket)
                    sale_ticket.delete()
                while sale.tickets.filter(description = ticket_type.name).count() < form_tickets:
                    new_ticket = Ticket(
                        sale = sale,
                        user = sale.customer_user,
                        performance = performance,
                        description = ticket_type.name,
                        cost = ticket_type.price,
                        payment = ticket_type.payment,
                    )
                    new_ticket.save()
                    logger.info("Sale %s ticket aded: %s", sale, new_ticket)

            # Update eFringers
            for efringer in sale_form.efringers:
                form_is_used = sale_form.cleaned_data[SaleForm.efringer_field_name(efringer)]
                sale_ticket = sale.tickets.filter(fringer = efringer).first()
                if form_is_used and not sale_ticket:
                    new_ticket = Ticket(
                        sale = sale,
                        user = sale.customer_user,
                        performance = performance,
                        fringer = efringer,
                        description = 'eFringer',
                        cost = 0,
                        payment = efringer.payment,
                    )
                    new_ticket.save()
                    logger.info("Sale %s ticket aded: %s", sale, new_ticket)
                elif sale_ticket and not form_is_used:
                    logger.info("Sale %s ticket deleted: %s", sale, sale_ticket)
                    sale_ticket.delete()

            # Update buttons
            sale.buttons = sale_form.cleaned_data['buttons']
            sale.save()

            # Update paper fringers
            form_fringers = sale_form.cleaned_data['fringers']
            while (sale.fringers.count() or 0) > form_fringers:
                sale.fringers.first().delete()
            while (sale.fringers.count() or 0) < form_fringers:
                fringer = Fringer(
                    description = '6 shows for £18',
                    shows = 6,
                    cost = 18,
                    sale = sale,
                )
                fringer.save()

            # If the sale is completed update the amount
            if sale.completed:
                sale.amount = sale.total_cost
                sale.save()

            # Reset sale form
            sale_form = create_sale_form(performance, sale)

        # Insufficient tickets
        else:
            logger.info("Sale %s tickets not available (%d requested, %d available): %s", sale, (form_tickets - sale_tickets), available_tickets, performance)
            sale_form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sale
    return  render_main_sales(request, venue, performance, sale, None, sale_form)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_complete(request, venue_uuid, performance_uuid, sale_uuid):

    # Get venue, performance and sale
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert not sale.completed

    # Complete the sale
    sale.amount = sale.total_cost
    sale.completed = datetime.datetime.now()
    sale.save()
    logger.info("Sale %s completed", sale)

    # Create start sale form
    start_form = create_sale_start_form(venue, performance)

    # Render sale
    return  render_main_sales(request, venue, performance, None, start_form, None)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_cancel(request, venue_uuid, performance_uuid, sale_uuid):

    # Get venue, performance and sale
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert not sale.completed

    # Delete the sale
    logger.info("Sale %s cancelled", sale)
    sale.delete()

    # Create start sale form
    start_form = create_sale_start_form(venue, performance)

    # Render sale
    return  render_main_sales(request, venue, performance, None, start_form, None)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def tickets(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.show.venue == venue
    assert performance.has_open_checkpoint

    # Render tickets
    return  render_main_tickets(request, venue, performance)
