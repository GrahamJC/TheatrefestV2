import uuid
import json
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce, Lower
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.forms import formset_factory, modelformset_factory
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from dal.autocomplete import Select2QuerySetView

from django_htmx.http import HttpResponseClientRedirect

from core.models import User
from program.models import Show, ShowPerformance
from tickets.models import BoxOffice, Sale, Refund, TicketType, Ticket, PayAsYouWill, FringerType, Fringer, Checkpoint, BadgesIssued

from .forms import CheckpointForm, SaleTicketsForm, SalePAYWForm, SaleExtrasForm, SaleForm, SaleEMailForm, RefundStartForm, UserSearchForm, UserBadgesForm

# Logging
import logging
logger = logging.getLogger(__name__)

# Square interface
def get_square_intent(request, boxoffice, sale):

    # Only create intent if card payment (SquareUp) pending
    if sale and sale.is_payment_pending and sale.is_square:
        metadata = f'{{ "boxoffice_id": {boxoffice.id}, "sale_id": {sale.id} }}'
        callback_url = request.build_absolute_uri(reverse('boxoffice:square_callback'))
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
    boxoffice = get_object_or_404(BoxOffice, pk=metadata['boxoffice_id'])
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
        return redirect(reverse('boxoffice:main_sale', args=[boxoffice.uuid, sale.uuid]))

    # Complete the sale
    sale.transaction_ID = server_transaction_id
    sale.completed = timezone.now()
    sale.save()
    logger.info(f"Sale {sale.id} completed (SquareUp)")
    messages.success(request, "Card payment completed")

    # Send e-mail receipt
    if sale.customer:
        send_email_receipt(sale, sale.customer)

    # Display main page for new sale
    return redirect(reverse('boxoffice:main', args=[boxoffice.uuid]))

# Helpers
def get_sales(boxoffice, date):

    # Get last checkpoint for today
    checkpoint = Checkpoint.objects.filter(boxoffice = boxoffice, created__date = date).order_by('created').last()
    if not checkpoint:
        return Sale.objects.none()

    # Get sales since last checkpoint
    return boxoffice.sales.filter(cancelled__isnull=True, created__gte = checkpoint.created).order_by('-id')

def get_refunds(boxoffice, date):

    # Get last checkpoint for today
    checkpoint = Checkpoint.objects.filter(boxoffice = boxoffice, created__date = date).order_by('created').last()
    if not checkpoint:
        return Refund.objects.none()

    # Get refunds since last checkpoint
    return boxoffice.refunds.filter(created__gte = checkpoint.created).order_by('-id')

def get_checkpoints(boxoffice, date):

    # Get today's checkpoints
    return boxoffice.checkpoints.filter(created__date = date).order_by('-created')

def send_email_receipt(sale, email):

    context = {
        'festival': sale.festival,
        'buttons': sale.buttons,
        'fringers': sale.fringers.count(),
        'tickets': sale.tickets.order_by('performance__date', 'performance__time', 'performance__show__name')
    }
    body = render_to_string('boxoffice/sale_email.txt', context)
    send_mail('Tickets for ' + sale.festival.title, body, settings.DEFAULT_FROM_EMAIL, [email])

# Forms
def sale_tickets_form(festival, sale, performance, post_data = None):

    # Validate parameters
    assert festival
    assert sale
    assert performance

    # Only create form if sale is in progress
    form = None
    if sale.is_in_progress:

        # Get ticket types
        ticket_types = []
        for ticket_type in sale.festival.ticket_types.filter(is_boxoffice=True).order_by('seqno'):
            ticket_types.append(ticket_type)

        # Create form
        form = SaleTicketsForm(ticket_types, data = post_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-tickets-form'
        form.helper.form_class = 'form-horizontal'
        form.helper.label_class = 'col-6'
        form.helper.field_class = 'col-6'
        form.helper.layout = Layout(
            *(Field(form.ticket_field_name(tt)) for tt in form.ticket_types),
        )

    # Return form
    return form

def sale_payw_form(sale, show, post_data = None):

    # Validate parameters
    assert sale
    assert show

    # Only create form if sale is in progress
    form = None
    if sale.is_in_progress:

        # Create form
        form = SalePAYWForm(data = post_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-payw-form'
        form.helper.form_class = 'form-horizontal'
        form.helper.label_class = 'col-6'
        form.helper.field_class = 'col-6'
        form.helper.layout = Layout(
            Field('amount'),
        )

    # Return form
    return form

def sale_extras_form(sale, post_data = None):

    # Validate parameters
    assert sale

    # Only create form if sale is in progress
    form = None
    if sale.is_in_progress:

        # Get initial values from sale
        initial_data = {
            'buttons': sale.buttons,
            'fringers': sale.fringers.count(),
            'donation': sale.donation,
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
            Field('donation'),
        )

    # Return form
    return form

def sale_update_form(sale, post_data = None):

    # Validate parameters
    assert sale

    # Only create form if sale is in progress or complete
    form = None
    if sale.is_in_progress or sale.is_complete:
        
        # Create form
        form = SaleForm(sale, data=post_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-form'
        form.helper.layout = Layout(
            Field('email'),
            Field('notes'),
        )

    # Return form
    return form

def sale_email_form(sale, post_data = None):

    # Validate parameters
    assert sale

    # Only create form if sale is complete
    form = None
    if sale.is_complete:

        # Create form
        form = SaleEMailForm(sale, data = post_data)

        # Add crispy form helper
        form.helper = FormHelper()
        form.helper.form_id = 'sale-email-form'
        form.helper.layout = Layout(
            Field('email'),
        )

    # Return form
    return form

def refund_start_form(post_data = None):

    # Create form
    form = RefundStartForm(data = post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'refund-start-form'
    form.helper.layout = Layout(
        Field('customer'),
        Field('reason'),
    )

    # Return form
    return form

def checkpoint_form(boxoffice, checkpoint, post_data = None):

    # Create form
    form = CheckpointForm(checkpoint, data = post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'checkpoint-form'
    form.helper.layout = Layout(
        Row(
            Column('cash', css_class='form-group col-md-4 mb-0'),
            Column('buttons', css_class='form-group col-md-4 mb-0'),
            Column('fringers', css_class='form-group col-md-4 mb-0'),
        ),
        Field('notes'),
    )
        
    # Return form
    return form

def user_search_form(email=None, post_data = None):

    # Create form
    form = UserSearchForm(email, data = post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'search-form'
    form.helper.layout = Layout(
        Field('email'),
    )

    # Return form
    return form

def user_badges_form(user, post_data = None):

    # Don't create form if there is no user
    if not user:
        return None
    
    # Create form
    form = UserBadgesForm(user, data = post_data)

    # Add crispy forms helper
    form.helper = FormHelper()
    form.helper.form_id = 'badges-form'
    form.helper.layout = Layout(
        Field('issued'),
    )

    # Return form
    return form

# Rendering
def sales_context(request, boxoffice, sale = None, accordion='tickets', show = None, performance = None, tickets_form = None, show_payw = None, payw_form = None, extras_form = None, sale_form = None):

    # Check if there is an active sale 
    if sale:

        # Box office sales are closed once a venue has opened a show
        boxoffice_sales_closed = False
        all_sales_closed = False
        if performance:
            # Ok to use naive datetimes to calculate differenc since both are local
            boxoffice_sales_closed = performance.has_open_checkpoint
            all_sales_closed = performance.has_close_checkpoint
        context = {
            'boxoffice': boxoffice,
            'sale': sale,
            'accordion': accordion,
            'shows': Show.objects.filter(festival = request.festival, is_cancelled = False, is_ticketed = True),
            'selected_show': show,
            'performances': show.performances.order_by('date', 'time') if show else None,
            'selected_performance': performance,
            'boxoffice_sales_closed': boxoffice_sales_closed,
            'all_sales_closed': all_sales_closed,
            'sale_tickets_form': tickets_form or sale_tickets_form(request.festival, sale, performance) if performance else None,
            'shows_payw': Show.objects.filter(festival = request.festival, is_cancelled = False, is_ticketed = False),
            'selected_show_payw': show_payw,
            'sale_payw_form': payw_form or sale_payw_form(sale, show_payw) if show_payw else None,
            'sale_extras_form': extras_form or sale_extras_form(sale),
            'sale_form': (sale_form or sale_update_form(sale)),
            'sale_email_form': sale_email_form(sale),
            'sales': get_sales(boxoffice, timezone.now().date()),
            'square_intent': get_square_intent(request, boxoffice, sale),
        }
    else:
        context = {
            'boxoffice': boxoffice,
            'sales': get_sales(boxoffice, timezone.now().date()),
        }
    return context

def render_sales(request, boxoffice, sale = None, accordion='tickets', show = None, performance = None, tickets_form = None, show_payw = None, payw_form = None, extras_form = None, sale_form = None):

    # Show and performance must match
    assert not performance or show == performance.show

    # Create context and render sales tab content
    context = sales_context(request, boxoffice, sale, accordion, show, performance, tickets_form, show_payw, payw_form, extras_form, sale_form)
    context['tab'] = 'sales'
    return render(request, 'boxoffice/_main_sales.html', context)

def refunds_context(request, boxoffice, refund = None, show = None, performance = None, start_form = None):

    # Check if there is an active refund 
    if refund:

        # Get refundable tickets
        refund_tickets = None
        if performance:
            refund_tickets = performance.tickets.filter(sale__completed__isnull = False, refund__isnull = True).order_by('id')
        context = {
            'boxoffice': boxoffice,
            'refund': refund,
            'shows': Show.objects.filter(festival = request.festival, is_ticketed = True),
            'selected_show': show,
            'performances': show.performances.order_by('date', 'time') if show else None,
            'selected_performance': performance,
            'refund_tickets': refund_tickets,
            'refunds': get_refunds(boxoffice, timezone.now().date()),
        }
    else:
        context = {
            'boxoffice': boxoffice,
            'refund_start_form': start_form or refund_start_form(),
            'refunds': get_refunds(boxoffice, timezone.now().date()),
        }
    return context

def render_refunds(request, boxoffice, refund = None, show = None, performance = None, start_form = None):

    # Show and performance must match
    assert not performance or show == performance.show

    # Create context and render refunds tab content
    context = refunds_context(request, boxoffice, refund, show, performance, start_form)
    context['tab'] = 'refunds'
    return render(request, 'boxoffice/_main_refunds.html', context)

def checkpoints_context(request, boxoffice, checkpoint=None, form=None):

    # Create checkpoints context
    return {
        'boxoffice': boxoffice,
        'checkpoint_form': form or checkpoint_form(boxoffice, checkpoint),
        'checkpoints': get_checkpoints(boxoffice, timezone.now().date()),
        'checkpoint': checkpoint,
    }

def render_checkpoint(request, boxoffice, checkpoint=None, form=None):

    # Render checkpoint tab content
    context = checkpoints_context(request, boxoffice, checkpoint, form)
    context['tab'] = 'checkpoints'
    return render(request, 'boxoffice/_main_checkpoints.html', context)

def users_context(request, boxoffice, search_form=None, email=None, user=None, badges_form=None):

    # Get ticket info (if any)
    performances = []
    if email:

        # Lookup tickets by customer e-mail (this is automatically set when a registered user buys
        # tickets online so it will capture both online and box office purchases linked to the e-mail
        # address)
        tickets = Ticket.objects.filter(sale__festival=request.festival, sale__customer=email, sale__completed__isnull=False)

        # Group tickets by performance for display
        performances = []
        if tickets:
            performance = None
            for t in tickets.order_by(Lower('performance__show__name'), 'performance__date', 'performance__time', 'id'):
                if not performance or performance['show'] != t.performance.show.name or performance['date'] != t.performance.date or performance['time'] != t.performance.time:
                    if performance:
                        performances.append(performance)
                    performance = {
                        'show': t.performance.show.name,
                        'date': t.performance.date,
                        'time': t.performance.time,
                        'tickets': []
                    }
                performance['tickets'].append(t)
            performances.append(performance)

    # If there is a registered user get detaiuls of badges purchased and collected
    badges = []
    if user:

        # Purchased
        for s in user.sales.filter(completed__isnull=False, buttons__gt=0).order_by('completed'):
            badges.append({
                'date': s.completed.date,
                'location': 'Online',
                'purchased': s.buttons,
                'collected': 0,
            })

        # Collected
        for bi in user.badges_issued.order_by('created'):
            badges.append({
                'date': s.completed.date,
                'location': bi.boxoffice.name if bi.boxoffice else bi.venue.name,
                'purchased': 0,
                'collected': bi.badges,
            })

    # Create users context
    return {
        'boxoffice': boxoffice,
        'search_form': search_form or user_search_form(email),
        'user': user,
        'badges_form': badges_form or user_badges_form(user),
        'badges': badges,
        'performances': performances,
    }

def render_users(request, boxoffice, search_form=None, email=None, user=None, badges_form=None):

    # Render users tab content
    context = users_context(request, boxoffice, search_form, email, user, badges_form)
    context['tab'] = 'users'
    return render(request, 'boxoffice/_main_users.html', context)

def render_main(request, boxoffice, tab, sale=None):

    # Create context and render main boxoffice page
    context = sales_context(request, boxoffice, sale)
    context.update(refunds_context(request, boxoffice))
    context.update(checkpoints_context(request, boxoffice))
    context.update(users_context(request, boxoffice))
    context['tab'] = tab
    return render(request, 'boxoffice/main.html', context)

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
def main(request, boxoffice_uuid, tab='sales'):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Cancel any incomplete box-office sales and refunds
    for sale in boxoffice.sales.filter(user_id=request.user.id, completed__isnull=True, cancelled__isnull=True):
        if sale.is_empty:
            logger.info(f"Sale {sale.id} auto-deleted (boxoffice {boxoffice.name})")
            sale.delete()
        else:
            sale.cancelled = timezone.now()
            sale.save()
            logger.info(f"Sale {sale.id} auto-cancelled")
    for refund in boxoffice.refunds.filter(user_id = request.user.id, completed__isnull = True):
        logger.info(f"Refund {refund.id} auto-deleted (boxoffice {boxoffice.name})")
        refund.delete()

    # Render main page
    return render_main(request, boxoffice, tab)
    
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@login_required
def main_sale(request, boxoffice_uuid, sale_uuid):

    # Get box office and sale
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    sale = get_object_or_404(Sale, uuid = sale_uuid)

    # Render main page
    return render_main(request, boxoffice, 'sales', sale)
    
# AJAX sale support
@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    sale = None

    # Create new sale
    sale = Sale(
        festival = boxoffice.festival,
        boxoffice = boxoffice,
        user = request.user,
    )
    sale.save()
    logger.info(f"Sale {sale.id} started at {boxoffice.name}")

    # Render sales tab content
    return render_sales(request, boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_show_select(request, sale_uuid):

    # Get sale, box office and show
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    show_uuid = request.GET['ShowUUID']
    if show_uuid:
        show = get_object_or_404(Show, uuid = show_uuid)
    else:
        show = None

    # Render sales tab content
    return render_sales(request, boxoffice, sale, accordion='tickets', show = show)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_performance_select(request, sale_uuid, show_uuid):

    # Get sale, box office, show and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    show = get_object_or_404(Show, uuid = show_uuid)
    performance_uuid = request.GET['PerformanceUUID']
    if performance_uuid:
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
        assert (show == performance.show)
    else:
        performance = None

    # Render sales tab content
    return render_sales(request, boxoffice, sale, accordion='tickets', show = show, performance = performance)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_tickets_add(request, sale_uuid, performance_uuid):

    # Get sale, box office and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    boxoffice = sale.boxoffice
    assert boxoffice
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Process form
    form = sale_tickets_form(request.festival, sale, performance, request.POST)
    if form.is_valid():

        # Check if there are sufficient tickets
        requested_tickets = form.ticket_count
        available_tickets = performance.tickets_available()
        if requested_tickets <= available_tickets:

            # Add tickets
            for ticket_type in form.ticket_types:
                quantity = form.cleaned_data[SaleTicketsForm.ticket_field_name(ticket_type)]
                if quantity > 0:
                    for n in range(quantity):
                        ticket = Ticket(
                            sale = sale,
                            user = sale.customer_user,
                            performance = performance,
                            type = ticket_type,
                        )
                        ticket.save()
                        logger.info(f"{ticket_type.name} ticket {ticket.id} for {performance.show.name} on {performance.date} at {performance.time} added to sale {sale.id}")

            # Prepare for adding more tickets
            form = None
            performance = None

        # Insufficient tickets
        else:
            logger.info(f"Sale {sale.id} insufficient tickets ({requested_tickets} requested, {available_tickets} available) for {performance.show.name} on {performance.date} at {performance.time}")
            form.add_error(None, f"There are only {available_tickets} tickets available for this performance.")

    # Render sales tab content
    return  render_sales(request, boxoffice, sale = sale, accordion='tickets', performance = performance, tickets_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_remove_performance(request, sale_uuid, performance_uuid):

    # Get the sale and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Remove all tickets for this performance
    for ticket in sale.tickets.filter(performance = performance):
        logger.info(f"{ticket.description} ticket {ticket.id} for {performance.show.name} on {performance.date} at {performance.time} removed from sale {sale.id}")
        ticket.delete()

    # Render updated sale
    return render_sales(request, sale.boxoffice, sale, accordion='tickets')

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_remove_ticket(request, sale_uuid, ticket_uuid):

    # Get sale and ticket
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    assert ticket.sale == sale

    # Remove ticket
    performance = ticket.performance
    logger.info(f"{ticket.description} ticket {ticket.id} for {performance.show.name} on {performance.date} at {performance.time} removed from sale {sale.id}")
    ticket.delete()

    # Render updated sale
    return render_sales(request, sale.boxoffice, sale, accordion='tickets')

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_show_select_payw(request, sale_uuid):

    # Get sale, box office and show
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    boxoffice = sale.boxoffice
    assert boxoffice
    show_uuid = request.GET['ShowUUID']
    if show_uuid != uuid.UUID('00000000-0000-0000-0000-000000000000'):
        show = get_object_or_404(Show, uuid = show_uuid)
    else:
        show = None

    # Render sales tab content
    return render_sales(request, boxoffice, sale, accordion='payw', show_payw = show)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_payw_add(request, sale_uuid, show_uuid):

    # Get sale, box office and performance
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    boxoffice = sale.boxoffice
    assert boxoffice
    show = get_object_or_404(Show, uuid = show_uuid)

    # Process form
    form = sale_payw_form(sale, show, request.POST)
    if form.is_valid():

        # Add PAYW
        amount = form.cleaned_data['amount']
        payw = PayAsYouWill(
            sale = sale,
            show = show,
            amount = amount,
        )
        payw.save()
        logger.info(f"£{amount} PAYW donation for {show.name} added to sale {sale.id}")

        # Prepare for adding more  PAYW donations
        form = None
        show = None

    # Render sales tab content
    return  render_sales(request, boxoffice, sale = sale, accordion='payw', show_payw = show, payw_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_payw_remove(request, sale_uuid, payw_uuid):

    # Get sale, boxoffice and PAYW
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    boxoffice = sale.boxoffice
    assert boxoffice
    payw = get_object_or_404(PayAsYouWill, uuid = payw_uuid)

    # Remove PAYW
    logger.info(f"£{payw.amount} PAYW donation for {payw.show.name} removed from sale {sale.id}")
    payw.delete()

    # Update sales tab content
    return render_sales(request, sale.boxoffice, sale, accordion='payw')

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_extras_update(request, sale_uuid):

    # Get sale and box office
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = sale_extras_form(sale, request.POST)
    if form.is_valid():

        # Update buttons
        buttons = form.cleaned_data['buttons']
        if sale.buttons != buttons:
            sale.buttons = buttons
            sale.save()
            logger.info(f"Buttons updated to {buttons} for {sale.id}")

        # Update paper fringers
        fringers = form.cleaned_data['fringers']
        if sale.fringers != fringers:
            while (sale.fringers.count() or 0) > fringers:
                fringer = sale.fringers.first()
                logger.info(f"Fringer {fringer.id} removed from {sale.id}")
                fringer.delete()
            while (sale.fringers.count() or 0) < fringers:
                fringer = Fringer(
                    type = request.festival.paper_fringer_type,
                    sale = sale,
                )
                fringer.save()
                logger.info(f"Fringer {fringer.id} added to {sale.id}")

        # Update donation
        donation = form.cleaned_data['donation']
        if sale.donation != donation:
            sale.donation = donation
            sale.save()
            logger.info(f"Donation updated to £{donation} for {sale.id}")

        # Destroy sale form
        form = None

    # Render sales tab content
    return  render_sales(request, boxoffice, sale = sale, accordion='extras', extras_form = form)

@transaction.atomic
def sale_payment(request, sale_uuid, payment_type):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress and sale.total_cost > 0
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Update sale
        sale.customer = form.cleaned_data['email']
        sale.notes = form.cleaned_data['notes']
        sale.amount = sale.total_cost
        sale.transaction_type = payment_type
        sale.transaction_fee = 0
        sale.save()
        logger.info(f"Payment type {payment_type} selected for for sale {sale.id}")

        # Clear form
        form = None

    # Update sales tab
    return render_sales(request, boxoffice, sale, sale_form=form)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_payment_cash(request, sale_uuid):

    # Select cash payment
    return sale_payment(request, sale_uuid, Sale.TRANSACTION_TYPE_CASH)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def sale_payment_card(request, sale_uuid):

    # Select card payment
    return sale_payment(request, sale_uuid, Sale.TRANSACTION_TYPE_SQUAREUP)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_payment_cancel(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_payment_pending
    boxoffice = sale.boxoffice
    assert boxoffice

    # Cancel payment
    sale.amount = 0
    sale.transaction_type = None
    sale.transaction_fee = 0
    sale.save()
    logger.info(f"Sale {sale.id} payment cancelled")

    # Update sales tab
    return render_sales(request, boxoffice, sale)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_complete_cash(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_payment_pending and sale.is_cash
    boxoffice = sale.boxoffice
    assert boxoffice

    # Complete sale
    sale.completed = timezone.now()
    sale.save()
    logger.info(f"Sale {sale.id} completed")
    messages.success(request, 'Sale completed')

    # Send a receipt (if we have an e-mail address)
    if sale.customer:
        send_email_receipt(sale, sale.customer)

    # Update sales tab
    return render_sales(request, boxoffice, None)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_complete_zero(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress and sale.total_cost == 0 and not sale.is_empty
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Complete sale
        sale.customer = form.cleaned_data['email']
        sale.notes = form.cleaned_data['notes']
        sale.completed = timezone.now()
        sale.save()
        logger.info(f"Sale {sale.id} completed")
        messages.success(request, 'Sale completed')

        # Clear form
        form = None

    # Update sales tab
    return render_sales(request, boxoffice, sale, sale_form=form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_cancel(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_in_progress
    boxoffice = sale.boxoffice
    assert boxoffice

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
    return render_sales(request, boxoffice, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_select(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_complete
    boxoffice = sale.boxoffice
    assert boxoffice

    # Update sales tab
    return render_sales(request, boxoffice, sale)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_update(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_complete
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = sale_update_form(sale, request.POST)
    if form.is_valid():

        # Update sale
        sale.customer = form.cleaned_data['email']
        sale.notes = form.cleaned_data['notes']
        sale.save()
        logger.info(f'Sale {sale.id} updated')
        messages.success(request, 'Sale updated')

        # If e-mail address was changed send a new receipt
        if 'email' in form.changed_data:
            send_email_receipt(sale, sale.customer)

        # Clear form
        form = None

    # Update sales tab
    return render_sales(request, boxoffice, sale, sale_form=form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_close(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_complete
    boxoffice = sale.boxoffice
    assert boxoffice

    # Update sales tab
    return render_sales(request, boxoffice, None)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def sale_email(request, sale_uuid):

    # Get sale and boxoffice
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    assert sale.is_complete
    boxoffice = sale.boxoffice
    assert boxoffice

    # Process form
    form = sale_email_form(sale, request.POST)
    if form.is_valid():

        # Send e-mail receipt
        send_email_receipt(sale, form.cleaned_data['email'])
        return HttpResponse('<div id=sale-email-status" class="alert alert-success">e-mail sent.</div>')

    # Form has errors
    return HttpResponse('<div id=sale-email-status" class="alert alert-danger">Invalid e-mail address.</div>')

# Refunds
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_start(request, boxoffice_uuid):
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    refund = None
    form = refund_start_form(request.POST)
    if form.is_valid():

        # Create new refund
        customer = form.cleaned_data['customer']
        reason = form.cleaned_data['reason']
        refund = Refund(
            festival = boxoffice.festival,
            boxoffice = boxoffice,
            user = request.user,
            customer = customer,
            reason = reason
        )
        refund.save()
        form = None
        logger.info(f"Refund {refund.id} ({refund.customer}) started at {boxoffice.name}")

    # Render refunds tab content
    return render_refunds(request, boxoffice, refund, start_form = form)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def refund_show_select(request, refund_uuid):

    # Get refund, box office and show
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    boxoffice = refund.boxoffice
    assert boxoffice
    show_uuid = request.GET['ShowUUID']
    if show_uuid:
        show = get_object_or_404(Show, uuid = show_uuid)
    else:
        show = None

    # Render refunds tab content
    return render_refunds(request, boxoffice, refund, show = show)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def refund_performance_select(request, refund_uuid, show_uuid):

    # Get refund, box office, show and performance
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    boxoffice = refund.boxoffice
    assert boxoffice
    show = get_object_or_404(Show, uuid = show_uuid)
    performance_uuid = request.GET['PerformanceUUID']
    if performance_uuid:
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
        assert(show == performance.show)
    else:
        performance = None

    # Render refunds tab content
    return render_refunds(request, boxoffice, refund, show = show, performance = performance)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_add_ticket(request, refund_uuid, ticket_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    assert ticket.refund == None
    performance = ticket.performance
    logger.info(f"{ticket.description} ticket {ticket.id} for {performance.show.name} on {performance.date} at {performance.time} added to refund {refund.id}")
    ticket.refund = refund
    ticket.save()
    if refund.completed:
        logger.warning(f"Completed refund {refund.id} updated")
    return render_refunds(request, refund.boxoffice, refund, show = ticket.performance.show, performance = ticket.performance)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_remove_ticket(request, refund_uuid, ticket_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)
    assert ticket.refund == refund
    performance = ticket.performance
    logger.info(f"{ticket.description} ticket {ticket.id} for {performance.show.name} on {performance.date} at {performance.time} removed from refund {refund.id}")
    ticket.refund = None
    ticket.save()
    if refund.completed:
        logger.warning(f"Completed refund {refund.id} updated")
    return render_refunds(request, refund.boxoffice, refund, show = performance.show, performance = performance)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_complete(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    if refund.completed:
        logger.error(f"Attempt to complete refund {refund.id} which is already completed")
    else:
        refund.amount = refund.total_cost
        refund.completed = timezone.now()
        refund.save()
        logger.info(f"Refund {refund.id} completed")
    return render_refunds(request, refund.boxoffice, refund)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_cancel(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    boxoffice = refund.boxoffice
    if refund.completed:
        logger.error(f"Attempt to cancel refund {refund.id} which is already completed")
    else:
        logger.info(f"Refund {refund.id} cancelled")
        refund.delete()
        refund = None
    return render_refunds(request, boxoffice, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_close(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    return render_refunds(request, refund.boxoffice, None)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def refund_select(request, refund_uuid):
    refund = get_object_or_404(Refund, uuid = refund_uuid)
    return render_refunds(request, refund.boxoffice, refund)

# Checkpoints
@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
@transaction.atomic
def checkpoint_add(request, boxoffice_uuid):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Create form and validate
    form = checkpoint_form(boxoffice, None, request.POST)
    if form.is_valid():

        # Add checkpoint
        checkpoint = Checkpoint(
            user = request.user,
            boxoffice = boxoffice,
            cash = form.cleaned_data['cash'],
            buttons = form.cleaned_data['buttons'],
            fringers = form.cleaned_data['fringers'],
            notes = form.cleaned_data['notes'],
        )
        checkpoint.save()
        logger.info(f"Boxoffice {boxoffice.name} checkpoint {checkpoint.id} added")
        messages.success(request, 'Checkpoint added')

        # If this is the first checkpoint for the day re-render the whole page to allow entry of sales
        if get_checkpoints(boxoffice, timezone.now().date()).count() == 1:
            return HttpResponseClientRedirect(reverse('boxoffice:main', args = [boxoffice.uuid]))
        return render_checkpoint(request, boxoffice, None)

    # Render errors
    return render_checkpoint(request, boxoffice, checkpoint, checkpoint_form=form)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def checkpoint_select(request, checkpoint_uuid):

    # Get checkpoint and box office
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    boxoffice = checkpoint.boxoffice
    assert boxoffice

    # Render selected checkpoint
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
    form = checkpoint_form(boxoffice, checkpoint, request.POST)
    if form.is_valid():

        # Update checkpoint and clear
        checkpoint.notes = form.cleaned_data['notes']
        checkpoint.save()
        logger.info(f"Boxoffice {boxoffice.name} checkpoint {checkpoint.id} updated")

        # Render checkpoint list
        return render_checkpoint(request, boxoffice, None)

    # Render form errors
    return render_checkpoint(request, boxoffice, checkpoint, checkpoint_form=form)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def checkpoint_cancel(request, checkpoint_uuid):

    # Get checkpoint and box office
    checkpoint = get_object_or_404(Checkpoint, uuid = checkpoint_uuid)
    boxoffice = checkpoint.boxoffice
    assert boxoffice

    # Render checkpoint list
    return render_checkpoint(request, boxoffice, None)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def users_search(request, boxoffice_uuid):

    # Get box office
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)

    # Get form and check for errors
    email = None
    user = None
    form = user_search_form(None, request.POST)
    if form.is_valid():

        # Get e-mail address and lookup registered user (if any)
        email = form.cleaned_data['email']
        user = User.objects.get(festival=request.festival, email=email)

    # Render user tab content
    return render_users(request, boxoffice, form, email, user, None)

@require_POST
@login_required
@user_passes_test(lambda u: u.is_boxoffice or u.is_admin)
def users_badges_issued(request, boxoffice_uuid, user_uuid):

    # Get box office and user
    boxoffice = get_object_or_404(BoxOffice, uuid = boxoffice_uuid)
    user = get_object_or_404(User, uuid = user_uuid)

    # Get form and check for errors
    form = user_badges_form(user, request.POST)
    if form.is_valid():

        # Get badges issued and record them
        issued = form.cleaned_data['issued']
        if issued > 0:
            badges_issued = BadgesIssued(
                user = user,
                boxoffice = boxoffice,
                badges = issued
            )
            badges_issued.save()
            logger.info(f"{issued} badges issued to {user.email} at {boxoffice.name}")

        # Reset form
        form = None

    # Render user tab content
    return render_users(request, boxoffice, None, user.email, user, form)
