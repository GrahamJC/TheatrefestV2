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
from django.views.decorators.http import require_GET, require_POST

import arrow

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from core.models import User
from program.models import Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, TicketType, Ticket, Fringer, Checkpoint

from .forms import CheckpointForm, SaleStartForm, SaleTicketsForm, SaleExtrasForm, RefundStartForm, RefundTicketForm, RefundForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def get_sales(boxoffice):

    # Get last checkpoint for today
    checkpoint = Checkpoint.objects.filter(boxoffice = boxoffice, created__gte = datetime.date.today()).order_by('created').last()
    if not checkpoint:
        return Sale.objects.none()

    # Get sales since last checkpoint
    return boxoffice.sales.filter(created__gte = checkpoint.created).order_by('-id')

def get_refunds(boxoffice):

    # Get last checkpoint for today
    checkpoint = Checkpoint.objects.filter(boxoffice = boxoffice, created__gte = datetime.date.today()).order_by('created').last()
    if not checkpoint:
        return Sale.objects.none()

    # Get refunds since last checkpoint
    return boxoffice.refunds.filter(created__gte = checkpoint.created).order_by('-id')

def get_checkpoints(boxoffice):

    # Get today's checkpoints
    return boxoffice.checkpoints.filter(created__gte = datetime.date.today()).order_by('-created')

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

def create_sale_tickets_form(festival, sale, post_data = None):

    # Validate parameters
    assert festival
    assert sale

    # Get shows
    shows = Show.objects.filter(festival=festival, is_cancelled = False, venue__is_ticketed = True)

    # Get ticket types and efringers
    ticket_types = []
    for ticket_type in sale.festival.ticket_types.order_by('name'):
        ticket_types.append(ticket_type)
    efringers = []
    if sale.customer_user:
        for efringer in sale.customer_user.fringers.order_by('name'):
            is_in_sale = sale.tickets.filter(fringer = efringer).exists()
            if is_in_sale or efringer.is_available():
                efringers.append(efringer)

    # Create form
    form = SaleTicketsForm(shows, ticket_types, efringers, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'sale-tickets-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-4'
    form.helper.field_class = 'col-8'
    if form.efringers:
        form.helper.layout = Layout(
            Field('show', onchange=f"loadPerformances(this.value)"),
            Field('performance'),
            TabHolder(
                Tab('Tickets', *(form.ticket_field_name(tt) for tt in form.ticket_types), css_class = 'pt-2'),
                Tab('eFringers', *(form.efringer_field_name(ef) for ef in form.efringers), css_class = 'pt-2'),
            ),
            Button('add', 'Add', css_class = 'btn-primary',  onclick = f"saleTickets()"),
        )
    else:
        form.helper.layout = Layout(
            Field('show', onchange=f"loadPerformances(this.value)"),
            Field('performance'),
            *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types),
            Button('add', 'Add', css_class = 'btn-primary',  onclick = f"saleTickets()"),
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
    form.helper.label_class = 'col-4'
    form.helper.field_class = 'col-8'
    form.helper.layout = Layout(
        Field('buttons'),
        Field('fringers'),
        Button('add', 'Add/Update', css_class = 'btn-primary',  onclick = f"saleExtras('{sale.uuid}')"),
    )

    # Return form
    return form

def render_main(request, boxoffice, tab, checkpoint_form = None):

    # Render main page
    today = datetime.datetime.today()
    report_dates = [today - datetime.timedelta(days = n) for n in range(1, 14)]
    context = {
        'boxoffice': boxoffice,
        'tab': tab,
        'sale_start_form': create_sale_start_form(),
        'sale_tickets_form': None,
        'sale_extras_form': None,
        'sale': None,
        'sales': get_sales(boxoffice),
        'refund_start_form': create_refund_start_form(),
        'refund_ticket_form': None,
        'refund_form': None,
        'refund' : None,
        'refunds': get_refunds(boxoffice),
        'checkpoint_form': checkpoint_form or create_checkpoint_form(boxoffice),
        'checkpoints': get_checkpoints(boxoffice),
        'report_today': f'{today:%Y%m%d}',
        'report_dates': [{ 'value': f'{d:%Y%m%d}', 'text': f'{d:%a, %b %d}'} for d in report_dates],
    }
    return render(request, 'boxoffice/main.html', context)

def render_sale(request, boxoffice, sale = None, start_form = None, tickets_form = None, extras_form = None):
    if sale:
        context = {
            'boxoffice': boxoffice,
            'sale_tickets_form': tickets_form or create_sale_tickets_form(request.festival, sale),
            'sale_extras_form': extras_form or create_sale_extras_form(sale),
            'sale': sale,
            'sales': get_sales(boxoffice),
        }
    else:
        context = {
            'boxoffice': boxoffice,
            'sale_start_form': start_form or create_sale_start_form(),
            'sale': None,
            'sales': get_sales(boxoffice),
        }
    return render(request, "boxoffice/_main_sales.html", context)

def create_refund_start_form(post_data = None):

    # Create form
    form = RefundStartForm(data = post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'refund-start-form'
    form.helper.layout = Layout(
        Field('customer'),
        Button('start', 'Start', css_class = 'btn-primary',  onclick = 'refundStart()'),
    )

    # Return form
    return form

def create_refund_ticket_form(refund = None, post_data = None):

    # Create form
    form = RefundTicketForm(post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'refund-ticket-form'
    form.helper.layout = Layout(
        Field('ticket_no'),
        Button('add', 'Add', css_class = 'btn-primary',  onclick = 'refundAddTicket()'),
    )

    # Return form
    return form

def create_refund_form(refund = None, post_data = None):

    # Create form
    initial_data = None
    if refund:
        initial_data = {
            'amount': refund.amount,
            'reason': refund.reason,
        }
    form = RefundForm(data = post_data, initial = initial_data)
    form.fields['reason'].widget.attrs['rows'] = 4

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'refund-form'
    form.helper.layout = Layout(
        Field('amount'),
        Field('reason'),
    )

    # Return form
    return form

def render_refund(request, boxoffice, refund = None, start_form = None, ticket_form = None, refund_form = None):
    if refund:
        context = {
            'boxoffice': boxoffice,
            'refund_ticket_form': ticket_form or create_refund_ticket_form(),
            'refund_form': refund_form or create_refund_form(refund = refund),
            'refund': refund,
            'refunds': get_refunds(boxoffice),
        }
    else:
        context = {
            'boxoffice': boxoffice,
            'refund_start_form': start_form or create_refund_start_form(),
            'refund': None,
            'refunds': get_refunds(boxoffice),
        }

    return render(request, "boxoffice/_main_refunds.html", context)

def create_checkpoint_form(boxoffice, post_data = None):

    # Create form
    form = CheckpointForm(post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'checkpoint-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-3'
    form.helper.field_class = 'col-9'
    form.helper.layout = Layout(
        Field('cash'),
        Field('buttons'),
        Field('fringers'),
        Field('notes'),
        Button('add', 'Add Checkpoint', css_class = 'btn-primary', onclick = 'checkpoint_add()'),
    )

    # Return form
    return form

def render_checkpoint(request, boxoffice, checkpoint_form = None):

    # Render checkpoint tab content
    context = {
        'boxoffice': boxoffice,
        'checkpoint_form': checkpoint_form or create_checkpoint_form(boxoffice),
        'checkpoints': get_checkpoints(boxoffice),
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
def main(request, boxoffice_uuid, tab = 'sales'):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Cancel any incomplete sales/refunds
    for sale in request.user.sales.filter(completed__isnull = True):
        logger.info("Incomplete sale %s cancelled", sale)
        sale.delete()
    for refund in request.user.refunds.filter(completed__isnull = True):
        logger.info("Incomplete refund %s cancelled", refund)
        refund.delete()

    # Render main page
    return render_main(request, boxoffice, tab)


# AJAX sale support
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def show_performances(request, show_uuid):

    show = get_object_or_404(Show, uuid = show_uuid)
    html = '<option value="">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = datetime.datetime.combine(performance.date, performance.time)
        mins_remaining = (dt - datetime.datetime.now()).total_seconds() / 60
        dt = arrow.get(dt)
        html += f'<option value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available)</option>'
        #if mins_remaining >= -30:
            #html += f'<option disabled value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available - venue only)</option>'
    return HttpResponse(html)
    
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

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
@transaction.atomic
def sale_tickets_add(request, sale_uuid):

    # Get sale and box office
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = create_sale_tickets_form(request.festival, sale, request.POST)
    if form.is_valid():

        # Get performance
        performance = ShowPerformance.objects.get(uuid = form.cleaned_data['performance'])

        # Check if there are sufficient tickets
        requested_tickets = form.ticket_count
        available_tickets = performance.tickets_available
        if requested_tickets <= available_tickets:

            # Adjust ticket numbers
            for ticket_type in form.ticket_types:
                form_tickets = form.cleaned_data[SaleTicketsForm.ticket_field_name(ticket_type)]
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
            for efringer in form.efringers:
                form_is_used = form.cleaned_data[SaleTicketsForm.efringer_field_name(efringer)]
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

            # If sale is complete then update the total
            if sale.completed:
                sale.amount = sale.total_cost
                sale.save()

            # Destroy form
            form = None

        # Insufficient tickets
        else:
            logger.info("Sale %s tickets not available (%d requested, %d available): %s", sale, requested_tickets, available_tickets, performance)
            form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_sale(request, boxoffice, sale = sale, tickets_form = form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_venue or u.is_admin)
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
                description = '6 shows for £18',
                shows = 6,
                cost = 18,
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
    if sale.completed:
        logger.error('sale_remove_performance: sale %s completed', sale)
    else:
        tickets = sale.tickets.count()
        for ticket in sale.tickets.all():
            if ticket.performance_id == performance.id:
                ticket.delete()
        logger.info("Sale %s performance removed (%d tickets): %s", sale, tickets, performance)
    return render_sale(request, sale.boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
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
        sale.completed = datetime.datetime.now()
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

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_report(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    context = {
        'sale': sale,
    }
    return render(request, 'boxoffice/sale_report.html', context)

# AJAX refund support
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    refund = None
    form = create_refund_start_form(request.POST)
    if form.is_valid():
        customer = form.cleaned_data['customer']
        refund = Refund(
            festival = boxoffice.festival,
            boxoffice = boxoffice,
            user = request.user,
            customer = customer,
        )
        refund.save()
        form = None
        logger.info("Refund %s started", refund)
    return render_refund(request, boxoffice, refund, start_form = form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_add_ticket(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if refund.completed:
        logger.error('refund_add_ticket: Refund %s completed', refund)
    else:
        form = create_refund_ticket_form(refund, request.POST)
        if form.is_valid():
            try:
                ticket = Ticket.objects.get(pk = form.cleaned_data['ticket_no'])
                if ticket.refund:
                    form.add_error('ticket_no', 'Ticket already refunded')
                elif ticket.fringer:
                    form.add_error('ticket_no', 'eFringer tickets cannot be refunded')
                else:
                    ticket.refund = refund
                    ticket.save()
                    logger.info("Refund %s ticket added: %s", refund, ticket)
                    form = None
            except Ticket.DoesNotExist:
                form.add_error('ticket_no', 'Ticket not found')
    return render_refund(request, refund.boxoffice, refund, ticket_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_remove_ticket(request, refund_uuid, ticket_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    if refund.completed:
        logger.error('refund_remove_ticket: Refund %s completed', refund)
    else:
        if ticket.refund == refund:
            ticket.refund = None
            ticket.save()
            logger.info("Refund %s ticket removed: %s", refund, ticket)
        else:
            logger.error('refund_remove_ticket: Ticket %s not part of refund %s', ticket, refund)
    return render_refund(request, refund.boxoffice, refund)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_complete(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if refund.completed:
        logger.error('refund_complete: Refund %s completed', refund)
    else:
        form = create_refund_form(post_data = request.POST)
        if form.is_valid():
            refund.amount = form.cleaned_data['amount']
            refund.reason = form.cleaned_data['reason']
            refund.completed = datetime.datetime.now()
            refund.save()
            logger.info("Refund %s completed", refund)
            form = None
    return render_refund(request, refund.boxoffice, refund, refund_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_cancel(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    boxoffice = refund.boxoffice
    if refund.completed:
        logger.error('refund_cancel: Refund %s completed', refund)
    else:
        refund.delete()
        logger.info("Refund %s cancelled", refund)
        refund = None
    return render_refund(request, boxoffice, refund)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_update(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if not refund.completed:
        logger.error('refund_update: Refund %s not completed', refund)
    else:
        form = create_refund_form(post_data = request.POST)
        if form.is_valid():
            refund.amount = form.cleaned_data['amount']
            refund.reason = form.cleaned_data['reason']
            refund.save()
            logger.info("Refund %s updated", refund)
            form = None
    return render_refund(request, refund.boxoffice, refund, refund_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_close(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    return render_refund(request, refund.boxoffice, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_select(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    return render_refund(request, refund.boxoffice, refund)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def refund_report(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    context = {
        'refund': refund,
    }
    return render(request, 'boxoffice/refund_report.html', context)

# Checkpoints
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def checkpoint_add(request, boxoffice_uuid):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Create form and validate
    form = create_checkpoint_form(boxoffice, request.POST)
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

        # If this was the first checkpoint of the day the whole page needs to be updated
        if get_checkpoints(boxoffice).count() == 1:
            return HttpResponse(f"Redirect: { reverse('boxoffice:main_tab', args = [boxoffice.uuid, 'checkpoints']) }")

        # Clear form
        form = None

    # Rener checkpoint tab content
    return render_checkpoint(request, boxoffice, form)
