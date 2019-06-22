import datetime
from decimal import Decimal

from django.conf import settings
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
from django.http import HttpResponse, JsonResponse

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
from .forms import OpenCheckpointForm, SaleStartForm, SaleForm, CloseCheckpointForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def is_next(performance):

    # Validate parameters
    assert performance

    # Check if this is the next performance at the venue
    if settings.VENUE_SHOW_ALL_PERFORMANCES:
        return performance == performance.show.venue.get_next_performance()
    else:
        return performance == performance.show.venue.get_next_performance(datetime.date.today())


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
        Field('cash'),
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
            Field('cash'),
            Field('buttons'),
            Field('fringers'),
            Field('audience'),
            Field('notes'),
            Submit('update', 'Update') if checkpoint else Submit('close', 'Close Performance'),
    )

    # Return form
    return form


def create_sale_start_form(performance, post_data = None):

    # Validate parameters
    assert performance
    assert is_next(performance)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint

    # Create form
    form = SaleStartForm(data = post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-start-form'
    form.helper.layout = Layout(
        Field('customer'),
        Button('start', 'Start', css_class = 'btn-primary',  onclick = 'saleStart()'),
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
    for ticket_type in sale.festival.ticket_types.order_by('name'):
        ticket_types.append(ticket_type)
        initial_data[SaleForm.ticket_field_name(ticket_type)] = sale.tickets.filter(description = ticket_type.name).count()

    # Get eFringers and add initial values
    efringers = []
    if sale.customer_user:
        for fringer in sale.customer_user.fringers.order_by('name'):
            efringers.append(fringer)
            initial_data[SaleForm.efringer_field_name(fringer)] = sale.tickets.filter(fringer = fringer).exists()

    # Get volunteer shifts (capped at four) and number of complimentary tickets used so far
    volunteer = sale.customer_user and sale.customer_user.volunteer
    if volunteer:
        volunteer_earned = min(volunteer.shifts.count(), 4)
        volunteer_used = Ticket.objects.filter(user = volunteer.user, description = 'Volunteer', sale__completed__isnull = False).count()
        initial_data['volunteer'] = sale.tickets.filter(user = volunteer.user, description = 'Volunteer').exists()

    # Create form
    form = SaleForm(ticket_types, efringers, data = post_data, initial = initial_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-4'
    form.helper.field_class = 'col-8'
    tabs = [Tab('Tickets', *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types), css_class = 'pt-2')]
    if form.efringers:
        fringers_available = []
        fringers_used = []
        fringers_empty = []
        for fringer in form.efringers:
            if fringer.is_available(performance) or sale.tickets.filter(fringer = fringer).exists():
                fringers_available.append(fringer)
            else:
                form.fields[SaleForm.efringer_field_name(fringer)].disabled = True
                if fringer.is_available():
                    fringers_used.append(fringer)
                else:
                    fringers_empty.append(fringer)
        tab_content = []
        if fringers_available:
            tab_content.append(HTML("<p>Available for this performance.</p>"))
            tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_available)
        if fringers_used:
            tab_content.append(HTML("<p>Already used for this performance.</p>"))
            tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_used)
        if fringers_empty:
            tab_content.append(HTML("<p>No tickets remaining.</p>"))
            tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_empty)
        tabs.append(Tab(
            'eFringers',
            *tab_content,
            css_class = 'pt-2',
        ))
    if volunteer:
        status = f"Used {volunteer_used} of {volunteer_earned} volunteer tickets."
        if volunteer_earned > volunteer_used:
            tabs.append(Tab('Volunteer', HTML(f"<p>{status}<p>"), Field('volunteer'), css_class = 'pt-2'))
        else:
            tabs.append(Tab('Volunteer', HTML(f"<p>{status}<p>"), css_class = 'pt-2'))
    tabs.append(Tab('Other', 'buttons', 'fringers', css_class = 'pt-2'))
    form.helper.layout = Layout(
        TabHolder(*tabs),
        Button('update', 'Update', css_class = 'btn-primary',  onclick = f"saleUpdate('{sale.uuid}')"),
    )

    # Return form
    return form


def render_main(request, venue, performance, tab = None, open_form = None, start_form = None, close_form = None):

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
        if not start_form and performance.has_open_checkpoint and not performance.has_close_checkpoint:
            start_form = create_sale_start_form(performance)
        if not close_form and performance.has_open_checkpoint and (performance.has_close_checkpoint or is_next(performance)):
            close_form = create_close_form(performance)

        # Select default tab if not specified
        if not tab:
            if performance.notes:
                tab = 'notes'
            elif not performance.has_open_checkpoint:
                tab = 'open'
            elif performance.has_close_checkpoint:
                tab = 'close'
            else:
                tab = 'sales'

    # Render page
    if settings.VENUE_SHOW_ALL_PERFORMANCES:
        performances = ShowPerformance.objects.filter(show__venue = venue).order_by('date', 'time')
    else:
        performances = ShowPerformance.objects.filter(date = datetime.date.today(), show__venue = venue).order_by('time')
    context = {
        'venue': venue,
        'tab': tab,
        'performances': performances,
        'performance': performance,
        'sales': sales,
        'current_sale': None,
        'open_form': open_form,
        'start_form': start_form,
        'close_form': close_form,
        'tickets': performance.tickets.order_by('id') if performance else None,
    }
    return render(request, 'venue/main.html', context)


def render_main_sales(request, performance, sale = None, start_form = None, sale_form = None):

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
        if not start_form and not sale:
            start_form = create_sale_start_form(performance)
        if not sale_form and sale:
            sale_form = create_sale_form(performance, sale)

    # Render sales tab content
    context = {
        'venue': venue,
        'performance': performance,
        'sales': sales,
        'current_sale': sale,
        'start_form': start_form,
        'sale_form': sale_form,
    }
    return render(request, "venue/_main_sales.html", context)


def render_main_notes(request, performance):

    # Validate parameters
    assert performance

    # Render notes tab content
    context = {
        'performance': performance,
    }
    return render(request, "venue/_main_notes.html", context)


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
    if settings.VENUE_SHOW_ALL_PERFORMANCES:
        performance = venue.get_next_performance() or venue.get_last_performance()
    else:
        performance = venue.get_next_performance(datetime.date.today()) or venue.get_last_performance(datetime.date.today())

    # Delete any imcomplete sales for this venue
    for sale in venue.sales.filter(completed__isnull = True):
        logger.info("Sale %s auto-cancelled", sale)
        sale.delete()

    # Render page
    return render_main(request, venue, performance)

   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def performance(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    venue = performance.show.venue

    # Delete any imcomplete sales for this venue
    for sale in venue.sales.filter(completed__isnull = True):
        logger.info("Sale %s auto-cancelled", sale)
        sale.delete()

    # Render page
    return render_main(request, venue, performance)

   
@require_GET
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@login_required
@transaction.atomic
def performance_notes(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Render notes
    return render_main_notes(request, performance)


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
            cash = open_form.cleaned_data['cash'],
            buttons = open_form.cleaned_data['buttons'],
            fringers = open_form.cleaned_data['fringers'],
            notes = open_form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info("Open checkpoint completed for %s (%s)", performance.show.name, performance)
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
        logger.info("Open checkpoint updated for {%s} on {%s}", performance.show.name, performance)
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
        performance.audience = close_form.cleaned_data['audience']
        performance.save()

        # Update checkpoint
        checkpoint.notes = close_form.cleaned_data['notes']
        checkpoint.save()
        logger.info("Close checkpoint updated for {%s} on {%s}", performance.show.name, performance)
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
    return  render_main_sales(request, performance)


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
    return  render_main_sales(request, performance, sale = sale)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_start(request, performance_uuid):

    # Get performance and venue
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance.has_open_checkpoint
    assert not performance.has_close_checkpoint
    venue = performance.show.venue

    # Process start sale form
    sale = None
    start_form = create_sale_start_form(performance, request.POST)
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
        start_form = None

    # Render sales tab content
    return  render_main_sales(request, performance, sale = sale, start_form = start_form)


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


            # Update volunteer complimentary tickets
            if sale.customer_user and sale.customer_user.is_volunteer:
                sale_ticket = sale.tickets.filter(user = sale.customer_user, description = 'Volunteer').first()
                use_volunteer = sale_form.cleaned_data['volunteer']
                if use_volunteer and not sale_ticket:
                    new_ticket = Ticket(
                        sale = sale,
                        user = sale.customer_user,
                        performance = performance,
                        description = 'Volunteer',
                        cost = 0,
                        payment = 0,
                    )
                    new_ticket.save()
                    logger.info("Sale %s ticket aded: %s", sale, new_ticket)
                elif sale_ticket and not use_volunteer:
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

            # Destroy sale form
            sale_form = None

        # Insufficient tickets
        else:
            logger.info("Sale %s tickets not available (%d requested, %d available): %s", sale, (form_tickets - sale_tickets), available_tickets, performance)
            sale_form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_main_sales(request, performance, sale = sale, sale_form = sale_form)


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

    # Complete the sale
    sale.amount = sale.total_cost
    sale.completed = datetime.datetime.now()
    sale.save()
    logger.info("Sale %s completed", sale)

    # Render sales tab content
    return  render_main_sales(request, performance)


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
    return  render_main_sales(request, performance)


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
    venue_tickets = performance.tickets.filter(sale__venue__isnull = False, refund__isnull = True).order_by('id')
    non_venue_tickets = performance.tickets.filter(sale__venue__isnull = True, refund__isnull = True).order_by('id')
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
