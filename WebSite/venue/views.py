import json

from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.forms import formset_factory, modelformset_factory
from django.utils import timezone

import arrow

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from django_htmx.http import HttpResponseClientRedirect

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

from core.models import User
from program.models import Show, ShowPerformance, Venue
from tickets.models import Sale, TicketType, Ticket, FringerType,  Fringer, Checkpoint, BadgesIssued
from .forms import OpenCheckpointForm, SaleItemsForm, SaleUpdateForm, CloseCheckpointForm

# Logging
import logging
logger = logging.getLogger(__name__)

# SquareUp interface
def get_square_intent(request, venue, performance, sale):

    # Only create intent if card payment (SquareUp) pending
    if sale and sale.is_payment_pending and sale.is_square:
        metadata = f'{{ "venue_id": {venue.id}, "performance_id": {performance.id}, "sale_id": {sale.id} }}'
        callback_url = request.build_absolute_uri(reverse('venue:square_callback'))
        intent = ';'.join([
            'intent:#Intent',
            'package=com.squareup',
            'action=com.squareup.pos.action.CHARGE',
            f'S.com.squareup.pos.WEB_CALLBACK_URI={callback_url}',
            f'S.com.squareup.pos.CLIENT_ID={settings.SQUARE_APPLICATION_ID}',
            f'S.com.squareup.pos.API_VERSION={settings.SQUARE_API_VERSION}',
            f'i.com.squareup.pos.TOTAL_AMOUNT={sale.total_cost_pence}',
            f'S.com.squareup.pos.CURRENCY_CODE={settings.SQUARE_CURRENCY_CODE}',
            'S.com.squareup.pos.TENDER_TYPES=com.squareup.pos.TENDER_CARD',
            f'S.com.squareup.pos.NOTE={sale.id}',
            f'S.com.squareup.pos.REQUEST_METADATA={metadata}',
            'end'
        ])
    else:
        intent = ''
    return intent

@require_GET
def square_callback(request):

    # Get parameters
    server_transaction_id = request.GET.get('com.squareup.pos.SERVER_TRANSACTION_ID', None)
    client_transaction_id = request.GET.get('com.squareup.pos.CLIENT_TRANSACTION_ID', None)
    request_metadata = request.GET.get('com.squareup.pos.REQUEST_METADATA', None)
    error_code = request.GET.get('com.squareup.pos.ERROR_CODE', None)
    error_description = request.GET.get('com.squareup.pos.ERROR_DESCRIPTION', None)

    # Parse meta-data
    metadata = json.loads(request_metadata)
    venue = get_object_or_404(Venue, pk=metadata['venue_id'])
    performance = get_object_or_404(ShowPerformance, pk=metadata['performance_id'])
    sale = get_object_or_404(Sale, pk=metadata['sale_id'])

    # Check for errors
    if error_code:

        # Reset payment type
        sale.amount = 0
        sale.transaction_type = None
        sale.transaction_fee = 0
        sale.save()
        logger.info(f"Square callback error (sale {sale.id}): {error_description}")
        if error_code == 'com.squareup.pos.ERROR_TRANSACTION_CANCELED':
            messages.warning(request, "Card payment cancelled")
        else:
            messages.error(request, f"Card payment failed: {error_description}")
    
        # Display main page with the sale still selected
        return redirect(reverse('venue:main_performance_sale', args=[venue.uuid, performance.uuid, sale.uuid]))

    # Complete the sale
    sale.transaction_ID = server_transaction_id
    sale.completed = timezone.now()
    sale.save()
    logger.info(f"Sale {sale.id} completed (SQuareUp)")
    messages.success(request, "Card payment completed")

    # Display main page for new sale
    return redirect(reverse('venue:main_performance', args=[venue.uuid, performance.uuid]))


# Helpers
def is_next(performance):

    # Validate parameters
    assert performance

    # Check if this is the next performance at the venue
    return performance == performance.venue.get_next_performance(performance.date)


# Select venue
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
def select(request):
    context = {
        'venues': Venue.objects.filter(festival=request.festival, is_ticketed=True),
    }
    return render(request, 'venue/select.html', context)


# Main page - open tab
def open_form(performance, post_data = None):

    # Validate parameters
    assert performance

    # Create form
    checkpoint = performance.open_checkpoint if performance.has_open_checkpoint else None
    form = OpenCheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'open-form'
    form.helper.layout = Layout(
        Row(
            Column('buttons', css_class='form-group col-md-4 mb-0'),
            Column('fringers', css_class='form-group col-md-4 mb-0'),
        ),
        Field('notes'),
    )

    # Return form
    return form

def open_context(request, venue, performance, form=None):

    # Validate parameters
    assert performance

    # Create context
    return {
        'venue': venue,
        'performance': performance,
        'open_form': form or open_form(performance),
    }

def render_open(request, venue, performance, form=None):

    # Validate parameters
    assert performance

    # Create context and render open tab content
    context = open_context(request, venue, performance, form)
    context['tab'] = 'open'
    return render(request, "venue/_main_open.html", context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_open(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert not performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue

    # Process open form
    form = open_form(performance, request.POST)
    if form.is_valid():

        # Create open checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            open_performance = performance,
            cash = 0,
            buttons = form.cleaned_data['buttons'],
            fringers = form.cleaned_data['fringers'],
            notes = form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info(f"Open checkpoint created at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, 'Performance opened')
        return HttpResponseClientRedirect(reverse('venue:main_performance', args=[venue.uuid, performance.uuid]))
    
    # Form has errors
    return render_open(request, venue, performance, form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def checkpoint_update_open(request, checkpoint_uuid):

    # Get checkpoint, venue and performance
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    venue = checkpoint.venue
    assert venue
    performance = checkpoint.open_performance
    assert performance
    assert performance.venue == venue

    # Process checkpoint form
    form = open_form(performance, request.POST)
    if form.is_valid():

        # Update checkpoint
        checkpoint.notes = form.cleaned_data['notes']
        checkpoint.save()
        logger.info(f"Open checkpoint updated at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, "Checkpoint updated")
        form = None

    # Render page
    return render_open(request, venue, performance, form)

# Main page - sales tab
def sale_items_form(performance, sale, post_data = None):

    # Validate parameters
    assert performance
    assert sale

    # Only create form if sale is in progress
    form = None
    if sale.is_in_progress:

        ## Additional parameter checks
        assert performance.has_open_checkpoint
        assert not performance.has_close_checkpoint
        assert is_next(performance)
        
        # Get initial values from sale
        initial_data = {
            'buttons': sale.buttons,
            'fringers': sale.fringers.count(),
        }

        # Get ticket types and add initial values
        ticket_types = []
        for ticket_type in sale.festival.ticket_types.filter(is_venue=True).order_by('seqno'):
            ticket_types.append(ticket_type)
            initial_data[SaleItemsForm.ticket_field_name(ticket_type)] = sale.tickets.filter(type=ticket_type).count()

        # Create form
        form = SaleItemsForm(ticket_types, data = post_data, initial = initial_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-items-form'
        form.helper.form_class = 'form-horizontal'
        form.helper.label_class = 'col-6'
        form.helper.field_class = 'col-6'
        form.helper.layout = Layout(
            HTML('<h5>Tickets</h5>'),
            *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types),
            HTML('<h5>Other</h5>'),
            'buttons',
            'fringers',        
        )

    # Return form
    return form

def sale_update_form(sale, post_data=None):

    # Validate parameters
    assert sale

    # Only create form if sale is in progress or complete 
    form = None
    if sale.is_in_progress or sale.is_complete:

        # Create the form
        form = SaleUpdateForm(sale, data = post_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-form'
        form.helper.layout = Layout(
            'notes',
        )

    # Return form
    return form

def sales_context(request, performance, sale, items_form=None, update_form=None):

    # Validate parameters
    assert performance
    assert performance.has_open_checkpoint

    # Get sales made between open/close checkpoints
    venue = performance.venue
    sales = Sale.objects.none()
    if performance.has_close_checkpoint:
        sales = venue.sales.filter(created__gte=performance.open_checkpoint.created, created__lte=performance.close_checkpoint.created, completed__isnull=False).order_by('-id')
    elif performance.has_open_checkpoint:
        sales = venue.sales.filter(created__gte=performance.open_checkpoint.created, completed__isnull=False).order_by('-id')

    # Create context
    return {
        'venue': venue,
        'performance': performance,
        'tab': 'sales',
        'sales': sales,
        'sale': sale,
        'sale_items_form': items_form or sale_items_form(performance, sale) if sale else None,
        'sale_form': update_form or sale_update_form(sale) if sale else None,
        'available': performance.tickets_available() + (sale.tickets.count() if sale else 0),
        'square_intent': get_square_intent(request, venue, performance, sale),
    }

def render_sales(request, performance, sale, items_form=None, update_form=None):

    # Create context and render sales tab content
    context = sales_context(request, performance, sale, items_form, update_form)
    context['tab'] = 'sales'
    return render(request, "venue/_main_sales.html", context)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_select(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Render sales tab content
    return  render_sales(request, performance, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_close(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Render sales tab content
    return  render_sales(request, performance, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_start(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue

    # Create new sale
    sale = Sale(
        festival = request.festival,
        venue = venue,
        user = request.user,
    )
    sale.save()
    logger.info(f"Sale {sale.id} started at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")

    # Render sales tab content
    return  render_sales(request, performance, sale)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_items(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_in_progress

    # Process sale form
    form = sale_items_form(performance, sale, request.POST)
    if form.is_valid():

        # Check if there are sufficient tickets
        requested_tickets = form.ticket_count
        available_tickets = performance.tickets_available() + sale.tickets.count()
        if requested_tickets <= available_tickets:

            # Adjust ticket numbers
            for ticket_type in form.ticket_types:
                quantity = form.cleaned_data[SaleItemsForm.ticket_field_name(ticket_type)]
                while sale.tickets.filter(type=ticket_type).count() > quantity:
                    ticket = sale.tickets.filter(type=ticket_type).last()
                    logger.info(f"{ticket_type.name} ticket {ticket.id} removed from sale {sale.id}")
                    ticket.delete()
                while sale.tickets.filter(type=ticket_type).count() < quantity:
                    ticket = Ticket(
                        sale = sale,
                        user = sale.customer_user,
                        performance = performance,
                        type = ticket_type,
                    )
                    ticket.save()
                    logger.info(f"{ticket_type.name} ticket {ticket.id} added to sale {sale.id}")

            # Update buttons
            buttons = form.cleaned_data['buttons']
            if sale.buttons != buttons:
                sale.buttons = buttons
                sale.save()
                logger.info(f"Buttons updated to {buttons} for sale {sale.id}")

            # Update paper fringers
            fringers = form.cleaned_data['fringers']
            if sale.fringers != fringers:
                while (sale.fringers.count() or 0) > fringers:
                    fringer = sale.fringers.first()
                    logger.info(f"Fringer {fringer.id} removed from sale {sale.id}")
                    fringer.delete()
                while (sale.fringers.count() or 0) < fringers:
                    fringer = Fringer(
                        type = request.festival.paper_fringer_type,
                        sale = sale,
                    )
                    fringer.save()
                    logger.info(f"Fringer {fringer.id} added to sale {sale.id}")

            # Clear form
            form = None

        # Insufficient tickets
        else:
            logger.info(f"Sale {sale.id} insufficient tickets ({requested_tickets} requested, {available_tickets} available)")
            form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_sales(request, performance, sale, items_form=form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_payment_card(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_in_progress

    # Process form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Update sale
        sale.notes = form.cleaned_data['notes']
        sale.amount = sale.total_cost
        sale.transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP
        sale.transaction_fee = 0
        sale.save()
        logger.info(f"Payment type {Sale.TRANSACTION_TYPE_SQUAREUP} selected for for sale {sale.id}")
        form = None

    # Form has errors
    return render_sales(request, performance, sale, update_form=form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_payment_cancel(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_payment_pending

    # Cancel payment
    sale.amount = 0
    sale.transaction_type = None
    sale.transaction_fee = 0
    sale.save()
    logger.info(f"Sale {sale.id} payment cancelled")

    # Update sales tab
    return  render_sales(request, performance, sale)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_complete_zero(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_in_progress and sale.total_cost == 0

    # Process form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Complete sale
        sale.notes = form.cleaned_data['notes']
        sale.completed = timezone.now()
        sale.save()
        logger.info(f"Sale {sale.id} completed")
        messages.success(request, 'Sale completed')

        # Clear form
        form = None

    # Update sales tab
    return  render_sales(request, performance, sale, update_form=form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_cancel(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_in_progress

    # Cancel sale (or delete it if empty)
    if sale.is_empty:
        logger.info(f"Sale {sale.id} cancelled (deleted - empty)")
        sale.delete()
        messages.warning(request, 'Sale cancelled')
    else:
        sale.cancelled = timezone.now()
        sale.save()
        logger.info(f"Sale {sale.id} cancelled")
        messages.warning(request, 'Sale cancelled')

    # Update sales tab
    return  render_sales(request, performance, None)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_update(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    venue = performance.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert sale.is_complete

    # Process sale form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Update sale
        sale.notes = form.cleaned_data['notes']
        sale.save();
        logger.info(f'Sale {sale.id} updated')
        messages.success(request, 'Sale updated')
        form = None

    # Update sales tab
    return  render_sales(request, performance, sale, update_form=form)

# Main page - close tab
def close_form(performance, post_data = None):

    # Validate parameters
    assert performance
    assert performance.has_open_checkpoint

    # Create form
    checkpoint = performance.close_checkpoint if performance.has_close_checkpoint else None
    form = CloseCheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'close-form'
    form.helper.layout = Layout(
        Row(
            Column('buttons', css_class='form-group col-md-4 mb-0'),
            Column('fringers', css_class='form-group col-md-4 mb-0'),
            Column('audience', css_class='form-group col-md-4 mb-0'),
        ),
        Field('notes'),
    )

    # Return form
    return form

def close_context(request, venue, performance, form=None):

    # Validate parameters
    assert performance

    # Create context
    return {
        'venue': venue,
        'performance': performance,
        'close_form': form or close_form(performance),
    }

def render_close(request, venue, performance, form=None):

    # Create context and render close tab content
    context = close_context(request, venue, performance, form)
    context['tab'] = 'close'
    return render(request, "venue/_main_close.html", context)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_close(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.venue

    # Process close form
    form = close_form(performance, request.POST)
    if form.is_valid():

        # Record audience tokens
        performance.audience = form.cleaned_data['audience'] or 0
        performance.save()

        # Create close checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            close_performance = performance,
            cash = 0,
            buttons = form.cleaned_data['buttons'],
            fringers = form.cleaned_data['fringers'],
            notes = form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info(f"Close checkpoint created at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, 'Performance closed')
        return HttpResponseClientRedirect(reverse('venue:main_performance', args=[venue.uuid, performance.uuid]))

    # Form has errors
    return render_close(request, venue, performance, form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def checkpoint_update_close(request, checkpoint_uuid):

    # Get checkpoint, venue and performance
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    venue = checkpoint.venue
    assert venue
    performance = checkpoint.close_performance
    assert performance
    assert performance.venue == venue

    # Process checkpoint form
    form = close_form(performance, request.POST)
    if form.is_valid():

        # Update audience tokens
        performance.audience = form.cleaned_data['audience'] or 0
        performance.save()

        # Update checkpoint
        checkpoint.notes = form.cleaned_data['notes']
        checkpoint.save()
        logger.info(f"Close checkpoint updated at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, "Checkpoint updated")
        close_form = None

    # Render page
    return render_close(request, venue, performance, form)


# Main page - tickets tab
def tickets_context(request, venue, performance):

    # Get tickets
    venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue = venue, refund__isnull = True).order_by('sale__customer', 'id')
    non_venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue__isnull = True, refund__isnull = True).order_by('id')
    cancelled_tickets = performance.tickets.filter(refund__isnull = False).order_by('sale__customer', 'id')

    # Render tickets
    return {
        'venue': venue,
        'performance': performance,
        'tab': 'tickets',
        'venue_tickets': venue_tickets,
        'non_venue_tickets': non_venue_tickets,
        'cancelled_tickets': cancelled_tickets,
    }

def render_tickets(request, venue, performance):

    # Create context and render tickets tab content
    context = tickets_context(request, venue, performance)
    context['tab'] = 'tickets'
    return render(request, "venue/_main_tickets.html", context)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def tickets_refresh(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    venue = performance.venue

    # Update tickets tab content
    return render_tickets(request, venue, performance)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def tickets_token(request, performance_uuid, ticket_uuid):

    # Get performance and ticket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    assert ticket.performance == performance

    # Toggle token issued state
    ticket.token_issued = not ticket.token_issued
    ticket.save()
    if ticket.token_issued:
        logger.info(f'Token issued for ticket {ticket.id}')
    else:
        logger.info(f'Token canceled for ticket {ticket.id}')

    # Update checkbox
    url = reverse('venue:tickets_token', args=[performance.uuid, ticket.uuid])
    checked = 'checked' if ticket.token_issued else ''
    return HttpResponse(f'<input id="token_{ticket.uuid}" type="checkbox" name="Issued" hx-get="{url}" hx-target="this" hx-swap="outerHTML" {checked}/>')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@csrf_exempt
@transaction.atomic
def tickets_badges(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    venue = performance.venue

    # Get user and number of badges issued
    user = get_object_or_404(User, uuid = request.POST['user-uuid'])
    issued = request.POST['issued']

    # Issue badges
    badges_issued = BadgesIssued(
        user = user,
        venue = venue,
        badges = issued,
    )
    badges_issued.save()

    # Remove (or update) badges link
    if user.badges_to_collect == 0:
        return HttpResponse(f'<span hx-swap-oob="outerHTML:.badges-{user.uuid}"></span>')
    else:
        return HttpResponse(f'<a class="badges-{user.uuid}" hx-swap-oob="outerHTML:.badges-{user.uuid}" href="#responsive" onclick="show_badges_modal(\'{user.uuid}\', {user.badges_to_collect})">{user.badges_to_collect}</a>')

@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def tickets_print(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    venue = performance.venue

    # Get tickets
    venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue = venue, refund__isnull = True).order_by('id')
    non_venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue__isnull = True, refund__isnull = True).order_by('id')
    cancelled_tickets = performance.tickets.filter(refund__isnull = False).order_by('id')

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

    # Festival banner
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 16*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Venue and performance
    table = Table(
        (
            (Paragraph('<para><b>Venue:</b></para>', styles['Normal']), venue.name),
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
    ))
    for ticket in non_venue_tickets:
        name_email= ticket.user.email if ticket.user else ticket.sale.customer
        sale_type = 'Venue' if ticket.sale.user else 'Box office' if ticket.sale.boxoffice else 'Online'
        table_data.append((
            str(ticket.id),
            name_email,
            ticket.description,
            sale_type,
        ))
    table = Table(
        table_data,
        colWidths = (2.5*cm, 8.5*cm, 2.5*cm, 2.5*cm),
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
    ))
    for ticket in venue_tickets:
        name_email= ticket.user.email if ticket.user else ticket.sale.customer
        sale_type = 'Venue' if ticket.sale.user else 'Box office' if ticket.sale.boxoffice else 'Online'
        table_data.append((
            str(ticket.id),
            name_email,
            ticket.description,
            sale_type,
        ))
    table = Table(
        table_data,
        colWidths = (2.5*cm, 8.5*cm, 2.5*cm, 2.5*cm),
        hAlign = 'LEFT',
    )
    story.append(table)

    # Cancelled tickets
    if cancelled_tickets:
        story.append(Paragraph('<para>Cancelled Tickets</para>', styles['Heading3']))
        table_data = []
        table_data.append((
            Paragraph(f"<para><b>Ticket No</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Name/e-mail</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Type</b></para>", styles['Normal']),
            Paragraph(f"<para><b>Sale</b></para>", styles['Normal']),
        ))
        for ticket in cancelled_tickets:
            name_email= ticket.user.email if ticket.user else ticket.sale.customer
            sale_type = 'Venue' if ticket.sale.user else 'Box office' if ticket.sale.boxoffice else 'Online'
            table_data.append((
                str(ticket.id),
                name_email,
                ticket.description,
                sale_type,
            ))
        table = Table(
            table_data,
            colWidths = (2.5*cm, 8.5*cm, 2.5*cm, 2.5*cm),
            hAlign = 'LEFT',
        )
        story.append(table)

    # Render PDF document and return it
    doc.build(story)
    return response


# Main page - info tab
def info_context(request, performance):

    # Validate parameters
    assert performance

    # Create context
    return {
        'show': performance.show if performance else None,
        'performance': performance,
        'tab': 'info',
    }


def render_info(request, performance):

    # Create context and render info tab content
    context = info_context(request, performance)
    context['tab'] = 'info'
    return render(request, "venue/_main_info.html", context)

@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def performance_info(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Render information tab
    return render_info(request, performance)


# Main page
def render_main(request, venue, performance, sale=None, tab=None):

    # Validate parameters
    assert venue

    # Create context and render page
    context = open_context(request, venue, performance)
    context.update(sales_context(request, performance, sale))
    context.update(close_context(request, venue, performance))
    context.update(tickets_context(request, venue, performance))
    context.update(info_context(request, performance))
    context.update({
        'tab': tab or 'sales' if performance and performance.has_open_checkpoint else 'open',
        'performances': ShowPerformance.objects.filter(date = request.now.date(), venue = venue, show__is_cancelled = False).order_by('time'),
        'next_performance': venue.get_next_performance(),
    })
    return render(request, 'venue/main.html', context)
   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def main(request, venue_uuid):

    # Get venue and performance taking the first of:
    #   The next performance (i.e. the first performance with no close checkpoint)
    #   The last performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = venue.get_next_performance(request.now.date()) or venue.get_last_performance(request.now.date())

    # Delete any imcomplete sales for this venue
    for sale in venue.sales.filter(user_id=request.user.id, completed__isnull=True, cancelled__isnull=True):
        if sale.is_empty:
            logger.info(f"Sale {sale.id} auto-deleted (venue {venue.name})")
            sale.delete()
        else:
            sale.cancelled = timezone.now()
            sale.save()
            logger.info(f"Sale {sale.id} auto-cancelled")

    # Render page
    return render_main(request, venue, performance)
   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def main_performance(request, venue_uuid, performance_uuid):

    # Get venue and performance
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert(venue == performance.venue)

    # Render page
    return render_main(request, venue, performance)
   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def main_performance_sale(request, venue_uuid, performance_uuid, sale_uuid):

    # Get sale, performance and venue
    venue = get_object_or_404(Venue, uuid = venue_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert(venue == performance.venue)
    sale = get_object_or_404(Sale, uuid = sale_uuid)

    # Render page
    return render_main(request, venue, performance, sale=sale)
