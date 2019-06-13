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
from tickets.forms import CustomerForm, SaleTicketsForm, SaleTicketSubForm, SaleFringerSubForm, SaleExtrasForm, RefundTicketForm, RefundForm

from .forms import CheckpointForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Helpers
def _get_todays_sales(boxoffice):

    # Get today's sales
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days = 1)
    return boxoffice.sales.filter(created__gte = today, created__lt = tomorrow).order_by('-id')

def _get_todays_refunds(boxoffice):

    # Get today's sales
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days = 1)
    return boxoffice.refunds.filter(created__gte = today, created__lt = tomorrow).order_by('-id')

def _get_todays_checkpoints(boxoffice):

    # Get today's checkpoints
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days = 1)
    return boxoffice.checkpoints.filter(created__gte = today, created__lt = tomorrow).order_by('-created')

def _render_main(request, boxoffice, tab, checkpoint_form = None):

    # Render main page
    today = datetime.datetime.today()
    report_dates = [today - datetime.timedelta(days = n) for n in range(1, 14)]
    context = {
        'boxoffice': boxoffice,
        'tab': tab,
        'sale_customer_form': _create_customer_form(),
        'sale_tickets_form': _create_sale_tickets_form(boxoffice.festival),
        'sale_ticket_subforms': _create_sale_ticket_subforms(boxoffice.festival),
        'sale_fringer_subforms': _create_sale_fringer_subforms(),
        'sale_extras_form': _create_sale_extras_form(),
        'sale': None,
        'sales': _get_todays_sales(boxoffice),
        'refund_customer_form': _create_customer_form(),
        'refund_ticket_form': _create_refund_ticket_form(),
        'refund_form': _create_refund_form(),
        'refund' : None,
        'refunds': _get_todays_refunds(boxoffice),
        'checkpoint_form': checkpoint_form or _create_checkpoint_form(boxoffice),
        'checkpoints': _get_todays_checkpoints(boxoffice),
        'report_today': f'{today:%Y%m%d}',
        'report_dates': [{ 'value': f'{d:%Y%m%d}', 'text': f'{d:%a, %b %d}'} for d in report_dates],
    }
    return render(request, 'boxoffice/main.html', context)

def _create_customer_form(post_data = None):
    # Create form
    form = CustomerForm(post_data)
    return form

def _create_sale_tickets_form(festival, post_data = None):
    # Create form
    form = SaleTicketsForm(Show.objects.filter(festival=festival, is_cancelled = False, venue__is_ticketed = True), post_data)
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

def _render_sale(request, boxoffice, sale=None, customer_form=None, tickets_form=None, ticket_subforms=None, fringer_subforms=None, extras_form=None):
    context = {
        'boxoffice': boxoffice,
        'sale_customer_form': customer_form or _create_customer_form(),
        'sale_tickets_form': tickets_form or _create_sale_tickets_form(boxoffice.festival),
        'sale_ticket_subforms': ticket_subforms or _create_sale_ticket_subforms(boxoffice.festival),
        'sale_fringer_subforms': fringer_subforms or _create_sale_fringer_subforms(sale),
        'sale_extras_form': extras_form or _create_sale_extras_form(sale),
        'sale': sale,
        'sales': _get_todays_sales(boxoffice),
    }
    return render(request, "boxoffice/_main_sales.html", context)

def _create_refund_ticket_form(refund = None, post_data = None):
    # Create form
    form = RefundTicketForm(post_data)
    return form

def _create_refund_form(refund = None, post_data = None):

    # Create form
    initial_data = []
    if refund:
        initial_data = {
            'amount': refund.total_cost if refund else 0,
        }
    form = RefundForm(post_data, initial = initial_data)
    form.fields['reason'].widget.attrs['rows'] = 4
    return form

def _render_refund(request, boxoffice, refund, customer_form = None, ticket_form = None, refund_form = None):
    context = {
        'boxoffice': boxoffice,
        'refund_customer_form': customer_form or _create_customer_form(),
        'refund_ticket_form': ticket_form or _create_refund_ticket_form(),
        'refund_form': refund_form or _create_refund_form(refund),
        'refund': refund,
        'refunds': _get_todays_refunds(boxoffice),
    }
    return render(request, "boxoffice/_main_refunds.html", context)

def _create_checkpoint_form(boxoffice, post_data = None):

    # Create form
    form = CheckpointForm(post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'checkpoint-form'
    form.helper.layout = Layout(
        Field('cash'),
        Field('buttons'),
        Field('fringers'),
        Field('notes'),
        Button('add', 'Add Checkpoint', css_class = 'btn-primary', onclick = 'checkpoint_add()'),
    )

    # Return form
    return form

def _render_checkpoint(request, boxoffice, checkpoint_form = None):

    # Render checkpoint tab content
    context = {
        'boxoffice': boxoffice,
        'checkpoint_form': checkpoint_form or _create_checkpoint_form(boxoffice),
        'checkpoints': _get_todays_checkpoints(boxoffice),
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
    return _render_main(request, boxoffice, tab)


# AJAX sale support
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_show_performances(request, sale_uuid, show_uuid):

    sale = get_object_or_404(Sale, uuid = sale_uuid)
    show = get_object_or_404(Show, uuid = show_uuid)
    html = '<option value="">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = datetime.datetime.combine(performance.date, performance.time)
        mins_remaining = (dt - datetime.datetime.now()).total_seconds() / 60
        if mins_remaining >= -30:
            dt = arrow.get(dt)
            if (mins_remaining > 30) or (sale.boxoffice == show.venue.boxoffice):
                html += f'<option value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available)</option>'
            else:
                html += f'<option disabled value="{performance.uuid}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} available - venue only)</option>'
    return HttpResponse(html)
    
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    sale = None
    form = _create_customer_form(request.POST)
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
    return _render_sale(request, boxoffice, sale, customer_form = form)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
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
        tickets_form = _create_sale_tickets_form(sale.festival, request.POST)
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

    return _render_sale(request, sale.boxoffice, sale, tickets_form = tickets_form, ticket_subforms = ticket_subforms, fringer_subforms = fringer_subforms)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
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
    return _render_sale(request, sale.boxoffice, sale, extras_form = extras_form)

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
    return _render_sale(request, sale.boxoffice, sale)

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
    return _render_sale(request, sale.boxoffice, sale)

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
    return _render_sale(request, sale.boxoffice, sale)

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
    return _render_sale(request, boxoffice, sale)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_close(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    return _render_sale(request, sale.boxoffice, None)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_report(request, sale_uuid):
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    context = {
        'sale': sale,
    }
    return render(request, 'boxoffice/sale_report.html', context)

# AJAX refund support
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    refund = None
    form = _create_customer_form(request.POST)
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
    return _render_refund(request, boxoffice, refund, customer_form = form)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_add_ticket(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if refund.completed:
        logger.error('refund_add_ticket: Refund %s completed', refund)
    else:
        form = _create_refund_ticket_form(refund, request.POST)
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
    return _render_refund(request, refund.boxoffice, refund, ticket_form = form)

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
    return _render_refund(request, refund.boxoffice, refund)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_complete(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if refund.completed:
        logger.error('refund_complete: Refund %s completed', refund)
    else:
        form = _create_refund_form(refund, request.POST)
        if form.is_valid():
            refund.amount = form.cleaned_data['amount']
            refund.reason = form.cleaned_data['reason']
            refund.completed = datetime.datetime.now()
            refund.save()
            logger.info("Refund %s completed", refund)
            form = None
    return _render_refund(request, refund.boxoffice, refund, refund_form = form)

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
    return _render_refund(request, boxoffice, refund)

@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_close(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    return _render_refund(request, refund.boxoffice, None)

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
    form = _create_checkpoint_form(boxoffice, request.POST)
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
        if _get_todays_checkpoints(boxoffice).count() == 1:
            return HttpResponse(f"Redirect: { reverse('boxoffice:main_tab', args = [boxoffice.uuid, 'checkpoints']) }")

        # Clear form
        form = None

    # Rener checkpoint tab content
    return _render_checkpoint(request, boxoffice, form)
