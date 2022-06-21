import datetime
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
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
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

import arrow

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from dal.autocomplete import Select2QuerySetView

from core.models import User
from program.models import Show, ShowPerformance
from tickets.models import BoxOffice, Sale, TicketType, Ticket, Fringer, Checkpoint

from .forms import CheckpointForm, SaleStartForm, SaleTicketsForm, SaleExtrasForm, SaleEMailForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def get_sales(boxoffice):

    # Get last checkpoint for today
    checkpoint = Checkpoint.objects.filter(boxoffice = boxoffice, created__date = timezone.now().date()).order_by('created').last()
    if not checkpoint:
        return Sale.objects.none()

    # Get sales since last checkpoint
    return boxoffice.sales.filter(created__gte = checkpoint.created).order_by('-id')

def get_checkpoints(boxoffice):

    # Get today's checkpoints
    return boxoffice.checkpoints.filter(created__date = timezone.now().date()).order_by('-created')

def create_sale_start_form(post_data = None):

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

def create_sale_tickets_form(festival, sale, performance, post_data = None):

    # Validate parameters
    assert festival
    assert sale
    assert performance

    # Get ticket types and efringers
    ticket_types = []
    for ticket_type in sale.festival.ticket_types.order_by('seqno'):
        ticket_types.append(ticket_type)
    efringers = []
    if sale.customer_user:
        for fringer in sale.customer_user.fringers.order_by('name'):
            efringers.append(fringer)

    # Create form
    form = SaleTicketsForm(ticket_types, efringers, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-tickets-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-6'
    form.helper.field_class = 'col-6'
    tabs = [Tab('Tickets', *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types), css_class = 'pt-2')]
    if sale.customer_user:
        tab_content = []
        if form.efringers:
            fringers_available = []
            fringers_used = []
            fringers_empty = []
            for fringer in form.efringers:
                if fringer.is_available(performance):
                    fringers_available.append(fringer)
                else:
                    form.fields[SaleTicketsForm.efringer_field_name(fringer)].disabled = True
                    if fringer.is_available():
                        fringers_used.append(fringer)
                    else:
                        fringers_empty.append(fringer)
            if fringers_available:
                tab_content.append(HTML("<p>Available for this performance.</p>"))
                tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_available)
            if fringers_used:
                tab_content.append(HTML("<p>Already used for this performance.</p>"))
                tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_used)
            if fringers_empty:
                tab_content.append(HTML("<p>No tickets remaining.</p>"))
                tab_content.extend(Field(form.efringer_field_name(ef)) for ef in fringers_empty)
        else:
            tab_content.append(HTML("<p>None.</p>"))
        tabs.append(Tab(
            'eFringers',
            *tab_content,
            css_class = 'pt-2',
        ))
    form.helper.layout = Layout(
        TabHolder(*tabs),
        Button('add', 'Add', css_class = 'btn-primary',  onclick = 'saleAddTickets()'),
    )

    # Return form
    return form

def create_sale_extras_form(sale, post_data = None):

    # Validate parameters
    assert sale

    # Get initial values from sale
    initial_data = {
        'buttons': sale.buttons,
        'fringers': sale.fringers.count(),
    }

    # Create form
    form = SaleExtrasForm(data = post_data, initial = initial_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-extras-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-6'
    form.helper.field_class = 'col-6'
    form.helper.layout = Layout(
        Field('buttons'),
        Field('fringers'),
        Button('add', 'Add/Update', css_class = 'btn-primary',  onclick = 'saleUpdateExtras()'),
    )

    # Return form
    return form

def create_sale_email_form(sale, post_data = None):

    # Validate parameters
    assert sale

    # Create form
    initial_data = { 'email': sale.customer }
    form = SaleEMailForm(initial = initial_data, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-email-form'
    form.helper.layout = Layout(
        Field('email'),
        Button('send', 'Send', css_class = 'btn-primary', onclick = 'saleEMailSend()'),
        Button('close', 'Close', css_class = 'btn-secondary',  data_dismiss = 'modal'),
    )

    # Return form
    return form

def create_checkpoint_form(boxoffice, checkpoint, post_data = None):

    # Create form
    form = CheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    if not checkpoint:
        form.helper.form_action = reverse('boxoffice:checkpoint_add', args = [boxoffice.uuid])
    form.helper.form_id = 'checkpoint-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-3'
    form.helper.field_class = 'col-9'
    if checkpoint:
        form.helper.layout = Layout(
            Field('cash'),
            Field('buttons'),
            Field('fringers'),
            Field('notes'),
            Button('update', 'Update', css_class = 'btn-primary', onclick = 'checkpointUpdate()'),
            Button('cancel', 'Cancel', css_class = 'btn-secondary', onclick = 'checkpointCancel()'),
        )
    else:
        form.helper.layout = Layout(
            Field('cash'),
            Field('buttons'),
            Field('fringers'),
            Field('notes'),
            Submit('add', 'Add Checkpoint'),
        )
        
    # Return form
    return form

def render_main(request, boxoffice, tab = None, checkpoint_form = None):

    # Render main page
    today = datetime.datetime.today()
    report_dates = [today - datetime.timedelta(days = n) for n in range(1, 14)]
    context = {
        'boxoffice': boxoffice,
        'tab': tab or 'sales',
        'sale_start_form': create_sale_start_form(),
        'sale_tickets_form': None,
        'sale_extras_form': None,
        'sale': None,
        'sales': get_sales(boxoffice),
        'checkpoint_form': checkpoint_form or create_checkpoint_form(boxoffice, None),
        'checkpoints': get_checkpoints(boxoffice),
    }
    return render(request, 'boxoffice/main.html', context)

def render_sale(request, boxoffice, sale = None, show = None, performance = None, start_form = None, tickets_form = None, extras_form = None):

    # Show and performance must match
    assert not performance or show == performance.show

    # Check if there is an active sale 
    if sale:

        # Box office sales are closed 30 mins before the performance starts
        boxoffice_sales_closed = False
        all_sales_closed = False
        if performance:
            # Ok to use naive datetimes to calculate differenc since both are local
            delta = datetime.datetime.combine(performance.date, performance.time) - datetime.datetime.now()
            boxoffice_sales_closed = delta.days < 0 or delta.total_seconds() <= (30 * 60)
            all_sales_closed = delta.days < 0 or delta.total_seconds() <= 0
        context = {
            'boxoffice': boxoffice,
            'sale': sale,
            'shows': Show.objects.filter(festival = request.festival, is_cancelled = False, venue__is_ticketed = True),
            'selected_show': show,
            'performances': show.performances.order_by('date', 'time') if show else None,
            'selected_performance': performance,
            'boxoffice_sales_closed': boxoffice_sales_closed,
            'all_sales_closed': all_sales_closed,
            'sale_tickets_form': tickets_form or create_sale_tickets_form(request.festival, sale, performance) if performance else None,
            'sale_extras_form': extras_form or create_sale_extras_form(sale),
            'sale_email_form': create_sale_email_form(sale),
            'sales': get_sales(boxoffice),
        }
    else:
        context = {
            'boxoffice': boxoffice,
            'sale_start_form': start_form or create_sale_start_form(),
            'sales': get_sales(boxoffice),
        }
    return render(request, 'boxoffice/_main_sales.html', context)

def render_checkpoint(request, boxoffice, checkpoint, checkpoint_form = None):

    # Render checkpoint tab content
    context = {
        'boxoffice': boxoffice,
        'checkpoint_form': checkpoint_form or create_checkpoint_form(boxoffice, checkpoint),
        'checkpoints': get_checkpoints(boxoffice),
        'checkpoint': checkpoint,
    }
    return render(request, 'boxoffice/_main_checkpoints.html', context)

# View functions
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@login_required
def select(request):
    context = {
        'boxoffices': BoxOffice.objects.filter(festival=request.festival),
    }
    return render(request, 'boxoffice/select.html', context)
    
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@login_required
def main(request, boxoffice_uuid, tab = None):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Cancel any incomplete box-office sales
    for sale in boxoffice.sales.filter(user_id = request.user.id, completed__isnull = True):
        logger.info("Incomplete box office sale %s (%s) at %s auto-cancelled", sale.id, sale.customer, boxoffice.name)
        sale.delete()

    # Render main page
    return render_main(request, boxoffice, tab)
    
# AJAX sale support
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    sale = None
    form = create_sale_start_form(request.POST)
    if form.is_valid():

        # Create new sale
        customer = form.cleaned_data['customer']
        sale = Sale(
            festival = boxoffice.festival,
            boxoffice = boxoffice,
            user = request.user,
            customer = customer,
        )
        sale.save()
        form = None
        logger.info("Sale %s started", sale)

    # Render sales tab content
    return render_sale(request, boxoffice, sale, start_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def show_performances(request, show_uuid):

    show = get_object_or_404(Show, uuid = show_uuid)
    html = '<option value="">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = datetime.datetime.combine(performance.date, performance.time)
        # Ok to use naive datetimes to calculate differenc since both are local
        mins_remaining = (dt - datetime.datetime.now()).total_seconds() / 60
        dt = arrow.get(dt)
        html += f'<option value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available)</option>'
        #if mins_remaining >= -30:
            #html += f'<option disabled value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available - venue only)</option>'
    return HttpResponse(html)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_show_select(request, sale_uuid, show_uuid = None):

    # Get sale, box office and show
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    show = None
    if show_uuid != uuid.UUID('00000000-0000-0000-0000-000000000000'):
        show = get_object_or_404(Show, uuid = show_uuid)

    # Render sales tab content
    return render_sale(request, boxoffice, sale, show = show)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_performance_select(request, sale_uuid, performance_uuid):

    # Get sale, box office, show and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Render sales tab content
    return render_sale(request, boxoffice, sale, show = performance.show, performance = performance)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_tickets_add(request, sale_uuid, performance_uuid):

    # Get sale, box office and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    assert performance

    # Process form
    form = create_sale_tickets_form(request.festival, sale, performance, request.POST)
    if form.is_valid():

        # Check if there are sufficient tickets
        requested_tickets = form.ticket_count
        available_tickets = performance.tickets_available
        if requested_tickets <= available_tickets:

            # Add tickets
            for ticket_type in form.ticket_types:
                for n in range(form.cleaned_data[SaleTicketsForm.ticket_field_name(ticket_type)]):
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
            for efringer in form.efringers:
                if form.cleaned_data[SaleTicketsForm.efringer_field_name(efringer)]:
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

            # If sale is complete then update the total
            if sale.completed:
                sale.amount = sale.total_cost
                sale.save()

            # Prepare for adding more tickets
            form = None
            performance = None

        # Insufficient tickets
        else:
            logger.info("Sale %s tickets not available (%d requested, %d available): %s", sale, requested_tickets, available_tickets, performance)
            form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_sale(request, boxoffice, sale = sale, performance = performance, tickets_form = form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_extras_update(request, sale_uuid):

    # Get sale and box office
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = create_sale_extras_form(sale, request.POST)
    if form.is_valid():

        # Update buttons
        sale.buttons = form.cleaned_data['buttons']
        sale.save()

        # Update paper fringers
        form_fringers = form.cleaned_data['fringers']
        while (sale.fringers.count() or 0) > form_fringers:
            sale.fringers.first().delete()
        while (sale.fringers.count() or 0) < form_fringers:
            fringer = Fringer(
                description = f'{request.festival.fringer_shows} shows for £{request.festival.fringer_price:.0f}',
                shows = request.festival.fringer_shows,
                cost = request.festival.fringer_price,
                sale = sale,
            )
            fringer.save()

        # If sale is complete then update the total
        if sale.completed:
            sale.amount = sale.total_cost
            sale.save()

        # Destroy sale form
        form = None

    # Render sales tab content
    return  render_sale(request, boxoffice, sale = sale, extras_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_remove_performance(request, sale_uuid, performance_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
    tickets = 0
    for ticket in sale.tickets.filter(performance = performance):
        ticket.delete()
        tickets += 1
    if sale.completed:
        logger.warning("Sale %s performance removed (%d tickets) after completed: %s", sale, tickets, performance)
    else:
        logger.info("Sale %s performance removed (%d tickets): %s", sale, tickets, performance)
    return render_sale(request, sale.boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_remove_ticket(request, sale_uuid, ticket_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    assert ticket.sale == sale
    if sale.completed:
        logger.warning("Sale %s ticket removed after completed: %s", sale, ticket)
    else:
        logger.info("Sale %s ticket removed: %s", sale, ticket)
    ticket.delete()
    return render_sale(request, sale.boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_complete(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    if sale.completed:
        logger.error('sale_complete: sale %s completed', sale)
    else:
        sale.amount = sale.total_cost
        sale.completed = timezone.now()
        sale.save()
        logger.info("Sale %s completed", sale)
    return render_sale(request, sale.boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_cancel(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    if sale.completed:
        logger.error('sale_cancel: sale %s completed', sale)
    else:
        logger.info("Sale %s cancelled", sale)
        sale.delete()
        sale = None
    return render_sale(request, boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_close(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    return render_sale(request, sale.boxoffice, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_select(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    return render_sale(request, sale.boxoffice, sale)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_email(request, sale_uuid):

    # Get sale
    sale = get_object_or_404(Sale, uuid = sale_uuid)

    # Process form
    form = create_sale_email_form(sale, request.POST)
    if form.is_valid():
        email = form.cleaned_data['email']
        context = {
            'festival': request.festival,
            'buttons': sale.buttons,
            'fringers': sale.fringers.count(),
            'tickets': sale.tickets.order_by('performance__date', 'performance__time', 'performance__show__name')
        }
        body = render_to_string('boxoffice/sale_email.txt', context)
        send_mail('Tickets for ' + request.festival.title, body, settings.DEFAULT_FROM_EMAIL, [email])
        return HttpResponse('<div class="alert alert-success">e-mail sent.</div>')

    # Return status
    return HttpResponse('<div class="alert alert-danger">Invalid e-mail address.</div>')

# Checkpoints
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def checkpoint_add(request, boxoffice_uuid):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Create form and validate
    form = create_checkpoint_form(boxoffice, None, request.POST)
    if form.is_valid():

        # Create checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            boxoffice = boxoffice,
            cash = form.cleaned_data['cash'],
            buttons = form.cleaned_data['buttons'],
            fringers = form.cleaned_data['fringers'],
            notes = form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info("Boxoffice checkpoint added for %s", boxoffice.name)
        messages.success(request, "Checkpoint added")

        # Clear form
        form = None

    # Render main page and go to sales (unless there was an error)
    return render_main(request, boxoffice, 'checkpoints' if form else 'sales', form)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def checkpoint_select(request, checkpoint_uuid):

    # Get checkpoint and box office
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    boxoffice = checkpoint.boxoffice
    assert boxoffice

    # Render checkpoint tab content
    return render_checkpoint(request, boxoffice, checkpoint)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def checkpoint_update(request, checkpoint_uuid):

    # Get checkpoint and box office
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    boxoffice = checkpoint.boxoffice
    assert boxoffice

    # Process form
    form = create_checkpoint_form(boxoffice, checkpoint, request.POST)
    if form.is_valid():

        # Update checkpoint
        checkpoint.notes = form.cleaned_data['notes']
        checkpoint.save()
        logger.info("Boxoffice checkpoint updated for %s", boxoffice.name)
        checkpoint = None
        form = None

    # Render checkpoint tab content
    return render_checkpoint(request, boxoffice, checkpoint, checkpoint_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def checkpoint_cancel(request, checkpoint_uuid):

    # Get checkpoint and box office
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    boxoffice = checkpoint.boxoffice
    assert boxoffice

    # Render checkpoint tab content
    return render_checkpoint(request, boxoffice, None)
