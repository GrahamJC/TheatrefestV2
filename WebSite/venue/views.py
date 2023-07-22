import datetime
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
from django.forms import formset_factory, modelformset_factory
from django.utils import timezone

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

from core.models import User
from program.models import Show, ShowPerformance, Venue
from tickets.models import Sale, TicketType, Ticket, Fringer, Checkpoint
from .forms import OpenCheckpointForm, SaleForm, CloseCheckpointForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def is_next(performance):

    # Validate parameters
    assert performance

    # Check if this is the next performance at the venue
    return performance == performance.show.venue.get_next_performance(performance.date)


def create_open_form(performance, post_data = None):

    # Validate parameters
    assert performance

    # Create form
    checkpoint = performance.open_checkpoint if performance.has_open_checkpoint else None
    form = OpenCheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_action = reverse('venue:checkpoint_update_open', args = [checkpoint.uuid]) if checkpoint else reverse('venue:performance_open', args = [performance.uuid])
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-3'
    form.helper.field_class = 'col-9'
    form.helper.layout = Layout(
        Field('buttons'),
        Field('fringers'),
        Field('notes'),
        Submit('update', 'Update') if checkpoint else Submit('open', 'Open Performance'),
    )

    # Return form
    return form


def create_close_form(performance, post_data = None):

    # Validate parameters
    assert performance
    assert performance.has_open_checkpoint

    # Create form
    checkpoint = performance.close_checkpoint if performance.has_close_checkpoint else None
    form = CloseCheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_action = reverse('venue:checkpoint_update_close', args = [checkpoint.uuid]) if checkpoint else reverse('venue:performance_close', args = [performance.uuid])
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-3'
    form.helper.field_class = 'col-9'
    form.helper.layout = Layout(
            Field('buttons'),
            Field('fringers'),
            Field('audience'),
            Field('notes'),
            Submit('update', 'Update') if checkpoint else Submit('close', 'Close Performance'),
    )

    # Return form
    return form


def create_sale_form(performance, sale, post_data = None):

    # Validate parameters
    assert performance
    assert is_next(performance)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    assert sale

    # Get initial values from sale
    initial_data = {
        'buttons': sale.buttons,
        'fringers': sale.fringers.count(),
    }

    # Get ticket types and add initial values
    ticket_types = []
    for ticket_type in sale.festival.ticket_types.order_by('seqno'):
        ticket_types.append(ticket_type)
        initial_data[SaleForm.ticket_field_name(ticket_type)] = sale.tickets.filter(description = ticket_type.name).count()

    # Create form
    form = SaleForm(ticket_types, data = post_data, initial = initial_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-6'
    form.helper.field_class = 'col-6'
    form.helper.layout = Layout(
        HTML('<h5>Tickets</h5>'),
        *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types),
        HTML('<h5>Other</h5>'),
        'buttons',
        'fringers',        
        Button('update', 'Add/Update Sale', css_class = 'btn-primary',  onclick = f"saleUpdate()"),
    )

    # Return form
    return form


def render_main(request, venue, performance, sale=None, tab=None, open_form=None, sale_form=None, close_form = None):

    # Validate parameters
    assert venue

    # Get performance details
    sales = None
    if performance:

        # Get sales made between open/close checkpoints
        if performance.has_close_checkpoint:
            sales = venue.sales.filter(created__gte = performance.open_checkpoint.created, created__lte = performance.close_checkpoint.created).order_by('-id')
        elif performance.has_open_checkpoint:
            sales = venue.sales.filter(created__gte = performance.open_checkpoint.created).order_by('-id')
        else:
            sales = Sale.objects.none()

        # Create forms if not specified
        if not open_form and (performance.has_open_checkpoint or is_next(performance)):
            open_form = create_open_form(performance)
        if not sale_form and not performance.has_close_checkpoint and sale and not sale.completed:
            sale_form = create_sale_form(performance, sale)
        if not close_form and performance.has_open_checkpoint and (performance.has_close_checkpoint or is_next(performance)):
            close_form = create_close_form(performance)

        # Select default tab if not specified
        if not tab:
            if not performance.has_open_checkpoint:
                tab = 'open'
            elif performance.has_close_checkpoint:
                tab = 'close'
            else:
                tab = 'sales'

    # Render page
    context = {
        'venue': venue,
        'tab': tab,
        'show': performance.show if performance else None,
        'performances': ShowPerformance.objects.filter(date = request.now.date(), show__venue = venue, show__is_cancelled = False).order_by('time'),
        'next_performance': venue.get_next_performance(),
        'performance': performance,
        'sales': sales,
        'sale': sale,
        'open_form': open_form,
        'sale_form': sale_form,
        'close_form': close_form,
        'tickets': performance.tickets.order_by('id') if performance else None,
        'available': performance.tickets_available + (sale.tickets.count() if sale else 0) if performance else 0,
        'square_appliocation_id': settings.SQUARE_APPLICATION_ID,
        'square_api_version': settings.SQUARE_API_VERSION,
        'square_currency_code': settings.SQUARE_CURRENCY_CODE,
    }
    return render(request, 'venue/main.html', context)


def render_sales(request, performance, sale = None, sale_form = None):

    # Validate parameters
    assert performance
    assert performance.has_open_checkpoint

    # Get sales made between open/close checkpoints
    venue = performance.show.venue
    sales = Sale.objects.none()
    if performance.has_close_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created, created__lte = performance.close_checkpoint.created).order_by('-id')
    elif performance.has_open_checkpoint:
        sales = venue.sales.filter(created__gte = performance.open_checkpoint.created).order_by('-id')

    # Create forms if not specified
    if not performance.has_close_checkpoint:
        if not sale_form and sale:
            sale_form = create_sale_form(performance, sale)

    # Render sales tab content
    context = {
        'venue': venue,
        'performance': performance,
        'sales': sales,
        'sale': sale,
        'sale_form': sale_form,
        'available': performance.tickets_available + (sale.tickets.count() if sale else 0),
        'square_appliocation_id': settings.SQUARE_APPLICATION_ID,
        'square_api_version': settings.SQUARE_API_VERSION,
        'square_currency_code': settings.SQUARE_CURRENCY_CODE,
    }
    return render(request, "venue/_main_sales.html", context)


def render_info(request, performance):

    # Validate parameters
    assert performance

    # Render information tab content
    context = {
        'show': performance.show if performance else None,
        'performance': performance,
    }
    return render(request, "venue/_main_info.html", context)


# View functions
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
def select(request):
    context = {
        'venues': Venue.objects.filter(festival=request.festival, is_ticketed=True),
    }
    return render(request, 'venue/select.html', context)

   
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
    for sale in venue.sales.filter(user_id = request.user.id, completed__isnull = True):
        logger.info("Incomplete venue sale %s (%s) at %s auto-cancelled", sale.id, sale.customer, venue.name)
        sale.delete()

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
    assert(venue == performance.show.venue)

    # Delete any incomplete sales for this venue
    for sale in venue.sales.filter(completed__isnull = True):
        logger.info(f"Sale {sale.id} auto-cancelled")
        sale.delete()

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
    assert(venue == performance.show.venue)
    sale = get_object_or_404(Sale, uuid = sale_uuid)

    # Render page
    return render_main(request, venue, performance, sale=sale)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_open(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert not performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue

    # Process open form
    open_form = create_open_form(performance, request.POST)
    if open_form.is_valid():

        # Create open checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            open_performance = performance,
            cash = 0,
            buttons = open_form.cleaned_data['buttons'],
            fringers = open_form.cleaned_data['fringers'],
            notes = open_form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info(f"Open checkpoint created at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        open_form = None

    # Render page
    return render_main(request, venue, performance, tab = 'open', open_form = open_form)


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
    assert performance.show.venue == venue

    # Process checkpoint form
    open_form = create_open_form(performance, request.POST)
    if open_form.is_valid():

        # Update checkpoint
        checkpoint.notes = open_form.cleaned_data['notes']
        checkpoint.save()
        logger.info(f"Open checkpoint updated at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, "Checkpoint updated")
        open_form = None

    # Render page
    return render_main(request, venue, performance, tab = 'open', open_form = open_form)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def performance_close(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue

    # Process close form
    close_form = create_close_form(performance, request.POST)
    if close_form.is_valid():

        # Record audience tokens
        performance.audience = close_form.cleaned_data['audience'] or 0
        performance.save()

        # Create close checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            venue = venue,
            close_performance = performance,
            cash = 0,
            buttons = close_form.cleaned_data['buttons'],
            fringers = close_form.cleaned_data['fringers'],
            notes = close_form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info(f"Close checkpoint created at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        close_form = None

    # Render page
    return render_main(request, venue, performance, tab = 'close', close_form = close_form)


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
    assert performance.show.venue == venue

    # Process checkpoint form
    close_form = create_close_form(performance, request.POST)
    if close_form.is_valid():

        # Update audience tokens
        performance.audience = close_form.cleaned_data['audience'] or 0
        performance.save()

        # Update checkpoint
        checkpoint.notes = close_form.cleaned_data['notes']
        checkpoint.save()
        logger.info(f"Close checkpoint updated at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")
        messages.success(request, "Checkpoint updated")
        close_form = None

    # Render page
    return render_main(request, venue, performance, tab = 'close', close_form = close_form)


# AJAX sale API
@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_new(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Render sales tab content
    return  render_sales(request, performance)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
def sale_select(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    venue = performance.show.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Render sales tab content
    return  render_sales(request, performance, sale = sale)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_start(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue

    # Create new sale
    sale = Sale(
        festival = request.festival,
        venue = venue,
        user = request.user,
    )
    sale.save()
    logger.info(f"Sale {sale.id} started at {venue.name} for {performance.show.name} on {performance.date} at {performance.time}")

    # Render sales tab content
    return  render_sales(request, performance, sale = sale)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_update(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue

    # Process sale form
    sale_form = create_sale_form(performance, sale, request.POST)
    if sale_form.is_valid():

        # Check if there are sufficient tickets
        requested_tickets = sale_form.ticket_count
        available_tickets = performance.tickets_available + sale.tickets.count()
        if requested_tickets <= available_tickets:

            # Adjust ticket numbers
            for ticket_type in sale_form.ticket_types:
                quantity = sale_form.cleaned_data[SaleForm.ticket_field_name(ticket_type)]
                while sale.tickets.filter(description = ticket_type.name).count() > quantity:
                    ticket = sale.tickets.filter(description = ticket_type.name).last()
                    logger.info(f"{ticket_type.name} ticket {ticket.id} removed from sale {sale.id}")
                    ticket.delete()
                while sale.tickets.filter(description = ticket_type.name).count() < quantity:
                    ticket = Ticket(
                        sale = sale,
                        user = sale.customer_user,
                        performance = performance,
                        description = ticket_type.name,
                        cost = ticket_type.price,
                        payment = ticket_type.payment,
                    )
                    ticket.save()
                    logger.info(f"{ticket_type.name} ticket {ticket.id} added to sale {sale.id}")

            # Update buttons
            buttons = sale_form.cleaned_data['buttons']
            if sale.buttons != buttons:
                sale.buttons = buttons
                sale.save()
                logger.info(f"Buttons updated to {buttons} for sale {sale.id}")

            # Update paper fringers
            fringers = sale_form.cleaned_data['fringers']
            if sale.fringers != fringers:
                while (sale.fringers.count() or 0) > fringers:
                    fringer = sale.fringers.first()
                    logger.info(f"Fringer {fringer.id} removed from sale {sale.id}")
                    fringer.delete()
                while (sale.fringers.count() or 0) < fringers:
                    fringer = Fringer(
                        description = f'{request.festival.fringer_shows} shows for £{request.festival.fringer_price:.0f}',
                        shows = request.festival.fringer_shows,
                        cost = request.festival.fringer_price,
                        sale = sale,
                    )
                    fringer.save()
                    logger.info(f"Fringer {fringer.id} added to sale {sale.id}")

            # If the sale is completed update the amount
            if sale.completed:
                sale.amount = sale.total_cost
                sale.save()
                logger.warning(f"Completed sale {sale.id} updated")

            # Destroy sale form
            sale_form = None

        # Insufficient tickets
        else:
            logger.info(f"Sale {sale.id} insufficient tickets ({requested_tickets} requested, {available_tickets} available)")
            sale_form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_sales(request, performance, sale = sale, sale_form = sale_form)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_complete(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert not sale.completed

    # Mark tokens issued for tickets
    for ticket in sale.tickets.all():
        ticket.token_issued = True
        ticket.save()
        
    # Complete the sale
    sale.amount = sale.total_cost
    sale.transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP
    sale.transaction_fee = 0
    sale.completed = request.now
    sale.save()
    logger.info("Sale %s completed", sale)

    # Render sales tab content
    return  render_sales(request, performance)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_cancel(request, performance_uuid, sale_uuid):

    # Get performance, venue and sale
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.venue == venue
    assert not sale.completed

    # Delete the sale
    logger.info("Sale %s cancelled", sale)
    sale.delete()

    # Render sales tab content
    return  render_sales(request, performance)

   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def performance_info(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Render information tab
    return render_info(request, performance)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def tickets(request, performance_uuid, format):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert format == 'html' or format == 'pdf'
    venue = performance.show.venue

    # Get tickets
    venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue = venue, refund__isnull = True).order_by('id')
    non_venue_tickets = performance.tickets.filter(sale__completed__isnull = False, sale__venue__isnull = True, refund__isnull = True).order_by('id')
    cancelled_tickets = performance.tickets.filter(refund__isnull = False).order_by('id')

    # Check for HTML
    if format == 'html':

        # Render tickets
        context = {
            'venue': venue,
            'performance': performance,
            'venue_tickets': venue_tickets,
            'non_venue_tickets': non_venue_tickets,
            'cancelled_tickets': cancelled_tickets,
        }
        return render(request, "venue/_main_tickets.html", context)

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


@require_GET
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def ticket_token(request, ticket_uuid):

    # Get ticket and toggle token issued state
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    ticket.token_issued = not ticket.token_issued
    ticket.save()

    # Return token issued state
    return JsonResponse({
        'token_issued': ticket.token_issued
    })


# Square web callback
def square_callback(request):

    # http://localhost:8000/venue/square/callback?com.squareup.pos.REQUEST_METADATA=%7B%22venue_id%22:%20229,%20%22performance_id%22:%20898,%20%22sale_id%22:%207480%7D
    # http://localhost:8000/venue/square/callback?com.squareup.pos.REQUEST_METADATA=%7B%22venue_id%22:%20229,%20%22performance_id%22:%20898,%20%22sale_id%22:%207480%7D&com.squareup.pos.ERROR_CODE=TRANSACTION_CANCELED

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
    if error_code == 'TRANSACTION_CANCELED':
        messages.warning(request, "Payment cancelled")
    elif error_code:
        messages.error(request, f"Payment failed: {error_description}")
    else:
        # Mark tokens issued for tickets
        for ticket in sale.tickets.all():
            ticket.token_issued = True
            ticket.save()
        
        # Complete the sale
        sale.amount = sale.total_cost
        sale.transaction_type = Sale.TRANSACTION_TYPE_SQUAREUP
        sale.transaction_fee = 0
        sale.completed = request.now
        sale.save()
        logger.info("Sale %s completed", sale)
    
    # Render sale
    return render_main(request, venue, performance, sale=sale)
