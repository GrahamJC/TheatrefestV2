import os
from datetime import datetime, date, time
import re
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from django.forms import formset_factory, modelformset_factory
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from django_htmx.http import HttpResponseClientRedirect

from .models import Sale, Refund, Basket, FringerType, Fringer, TicketType, Ticket, Donation, PayAsYouWill
from .forms import BuyTicketForm, RenameFringerForm, BuyFringerForm, CheckoutButtonsForm
from program.models import Show, ShowPerformance

# Logging
import logging
logger = logging.getLogger(__name__)

# Stripe interface
import stripe
stripe.api_key = settings.STRIPE_PRIVATE_KEY


# MyAccount
def myaccount_fringer_formset(user, post_data=None):
    FringerFormSet = modelformset_factory(Fringer, form = RenameFringerForm, extra = 0)
    formset = FringerFormSet(post_data, queryset = user.fringers.exclude(sale__completed__isnull = True))
    return formset

def myaccount_buy_fringer_form(festival, user, post_data=None):
    fringer_types = FringerType.objects.filter(festival=festival, is_online=True)
    form = BuyFringerForm(user, fringer_types, post_data)
    return form

def myaccount_tickets_context(request):

    # Get online sales status
    sales_closed = request.festival.online_sales_close and (request.now.date() > request.festival.online_sales_close)
    sales_open = request.festival.online_sales_open and (request.now.date() >= request.festival.online_sales_open) and not sales_closed

    # Get tickets grouped by performance
    performances_current = []
    performances_past = []
    for ticket in request.user.tickets.filter(sale__completed__isnull = False, refund__isnull = True).order_by('performance__date', 'performance__time', 'performance__show__name').values('performance_id').distinct():

        # Get list of performances and then get toickets for each performance
        performance = ShowPerformance.objects.get(pk = ticket['performance_id'])
        tickets = request.user.tickets.filter(performance_id = ticket['performance_id'], sale__completed__isnull = False, refund__isnull = True)
        p = {
            'id': performance.id,
            'uuid': performance.uuid,
            'show': performance.show.name,
            'date' : performance.date,
            'time': performance.time,
            'tickets': [{'id': t.id, 'uuid': t.uuid, 'description': t.type.name, 'cost': t.type.price, 'fringer_name': (t.fringer.name if t.fringer else None)} for t in tickets],
        }

        # Ok to compare naive datetimes since both are local
        if datetime.combine(performance.date, performance.time) >= request.now:
            performances_current.append(p)
        else:
            performances_past.append(p)

    # Create context and return it
    return {
        'sales_closed': sales_closed,
        'sales_open': sales_open,
        'sales_open_date': request.festival.online_sales_open,
        'performances_current': performances_current,
        'performances_past': performances_past,
        'basket': request.user.basket,
    }

def myaccount_fringers_context(request, fringer_formset=None, buy_fringer_form=None):

    # Get online sales status
    sales_closed = request.festival.online_sales_close and (request.now.date() > request.festival.online_sales_close)
    sales_open = request.festival.online_sales_open and (request.now.date() >= request.festival.online_sales_open) and not sales_closed

    # Create context and return it
    return {
        'sales_closed': sales_closed,
        'sales_open': sales_open,
        'sales_open_date': request.festival.online_sales_open,
        'fringer_formset': fringer_formset or myaccount_fringer_formset(request.user),
        'buy_fringer_form': buy_fringer_form or myaccount_buy_fringer_form(request.festival, request.user),
    }

def myaccount_volunteer_context(request):

    # Volunteer tickets
    volunteer_tickets =  request.user.tickets.filter(type=request.festival.volunteer_ticket_type).order_by('performance__date', 'performance__time', 'performance__show__name')
    return {
        'volunteer_earned': request.user.volunteer.comps_earned if request.user.is_volunteer else 0,
        'volunteer_available': request.user.volunteer.comps_available if request.user.is_volunteer else 0,
        'volunteer_tickets': volunteer_tickets,
    }

def myaccount_context(request, tab, fringer_formset=None, buy_fringer_form=None):

    # Create context and return it
    context = myaccount_tickets_context(request)
    context.update(myaccount_fringers_context(request, fringer_formset, buy_fringer_form))
    context.update(myaccount_volunteer_context(request))
    context['tab'] = tab
    return context

def myaccount_render_tickets(request):

    # Create context and render ticket tab content
    context = myaccount_tickets_context(request)
    context['tab_messages'] = True
    return render(request, 'tickets/_myaccount_tickets.html', context)

def myaccount_render_fringers(request, fringer_formset=None, buy_fringer_form=None):

    # Create context and render ticket tab content
    context = myaccount_fringers_context(request, fringer_formset, buy_fringer_form)
    context['tab_messages'] = True
    return render(request, 'tickets/_myaccount_fringers.html', context)

@require_GET
@login_required
def myaccount(request):

    # Render full page with Tickets tab selected
    context = myaccount_context(request, 'tickets')
    return render(request, 'tickets/myaccount.html', context)

@require_POST
@login_required
@csrf_exempt
@transaction.atomic
def myaccount_ticket_cancel(request, ticket_uuid):

    # Get ticket to be cancelled
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)

    # Create a refund and add the ticket
    refund = Refund(
        festival = request.festival,
        user = request.user,
        customer = request.user.email,
        completed = timezone.now(),
    )
    refund.save()
    ticket.refund = refund
    ticket.save()
    logger.info(f"{ticket.description} ticket for {ticket.performance.show.name} on {ticket.performance.date} at {ticket.performance.time} cancelled")
    messages.success(request, f"{ticket.description} ticket for {ticket.performance.show.name} cancelled")

    # Render updated tickets
    return myaccount_render_tickets(request)

@require_POST
@login_required
@transaction.atomic
def myaccount_fringers_rename(request):

    # Create fringers formset and check for errors
    fringer_formset = myaccount_fringer_formset(request.user, request.POST)
    if fringer_formset.is_valid():

        # Save changes
        for fringer in fringer_formset.save():
            logger.info(f"eFringer renamed to {fringer.name}")
            messages.success(request, f"eFringer renamed to {fringer.name}")

        # Clear formset
        fringer_formset = None

    else:
        messages.error(request, f"Please correct the errors shown and try again")

    # Render updated fringers
    return myaccount_render_fringers(request, fringer_formset, None)

@require_POST
@login_required
@transaction.atomic
def myaccount_fringers_buy(request):

    # Get basket
    basket = request.user.basket

    # Create form and check for errors
    buy_fringer_form = myaccount_buy_fringer_form(request.festival, request.user, request.POST)
    if buy_fringer_form.is_valid():

        # Get fringer type
        buy_type = get_object_or_404(FringerType, pk = int(buy_fringer_form.cleaned_data['type']))
        buy_name = buy_fringer_form.cleaned_data['name']
        if not buy_name:
            fringer_count = Fringer.objects.filter(user = request.user).count()
            buy_name = f"eFringer{fringer_count + 1}"

        # Create new fringer and add to basket
        fringer = Fringer(
            user = request.user,
            type = buy_type,
            name = buy_name if buy_name else buy_type.name,
            basket = basket,
        )
        fringer.save()
        logger.info(f"eFringer {fringer.name} ({buy_type.name}) added to basket")
        messages.success(request, f"Fringer {fringer.name} ({buy_type.name}) added to basket")

        # Confirm purchase
        return HttpResponseClientRedirect(reverse('tickets:myaccount_fringers_confirm'))

    else:
        messages.error(request, f"Please correct the errors shown and try again")

    # Render updated fringers
    return myaccount_render_fringers(request, None, buy_fringer_form)

@require_GET
@login_required
def myaccount_fringers_confirm(request):
    return render(request, 'tickets/myaccount_fringers_confirm.html')

# Buy tickets
def buy_ticket_formset(request, post_data=None):

    # Get ticket types
    ticket_types = TicketType.objects.filter(festival=request.festival, is_online = True)

    # Create formset and return it
    TicketFormset = formset_factory(BuyTicketForm, extra = 0)
    initial_data = [{'id': t.id, 'name': t.name, 'price': t.price, 'quantity': 0} for t in ticket_types]
    return TicketFormset(post_data, initial = initial_data)

def buy_fringer_form(request, post_data=None):

    # Get fringer types
    fringer_types = FringerType.objects.filter(festival=request.festival, is_online=True)

    # Create form and return it
    form = BuyFringerForm(request.user, fringer_types, post_data)
    return form

def buy_tickets_context(request, performance, ticket_formset=None):

    # Create context and return it
    return {
        'performance': performance,
        'ticket_formset': ticket_formset or buy_ticket_formset(request),
    }

def buy_fringers_context(request, performance, fringer_form=None):

    # Get fringers available for this perfromance
    fringers = Fringer.get_available(request.user, performance)

    # Create context and return it
    return {
        'performance': performance,
        'fringers': fringers,
        'buy_fringer_form': fringer_form or buy_fringer_form(request),
    }

def buy_volunteer_context(request, performance):

    # Get volunteer ticket info
    volunteer_available = request.user.volunteer.comps_available
    volunteer_used = request.user.tickets.filter(performance=performance, type=request.festival.volunteer_ticket_type)

    # Create context and return it
    return {
        'performance': performance,
        'volunteer_available': volunteer_available,
        'volunteer_used': volunteer_used,
    }

def buy_render_tickets(request, performance, ticket_formset=None):

    # Create context and render tickets tab
    context = buy_tickets_context(request, performance, ticket_formset)
    context['tab_messages'] = True
    return render(request, "tickets/_buy_tickets.html", context)

def buy_render_fringers(request, performance, fringer_form=None):

    # Create context and render fringers tab
    context = buy_fringers_context(request, performance, fringer_form)
    context['tab_messages'] = True
    return render(request, "tickets/_buy_fringers.html", context)

def buy_render_volunteer(request, performance):

    # Create context and render volunteer tab
    context = buy_volunteer_context(request, performance)
    context['tab_messages'] = True
    return render(request, "tickets/_buy_fringers.html", context)

@require_GET
@login_required
def buy(request, performance_uuid):

    # Get performance
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Check if ticket sales are still open
    if performance.has_close_checkpoint:
        return redirect(reverse('tickets:buy_closed', args = [performance.uuid]))

    # Create context and display page with tickets tab active
    context = buy_tickets_context(request, performance)
    context.update(buy_fringers_context(request, performance))
    if request.user.is_volunteer:
        context.update(buy_volunteer_context(request, performance))
    context['tab'] = 'tickets'
    return render(request, "tickets/buy.html", context)

@require_GET
@login_required
def buy_closed(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Display closed page
    context = {
        'basket': basket,
        'performance': performance,
    }
    return render(request, "tickets/buy_closed.html", context)

@require_POST
@login_required
@transaction.atomic
def buy_tickets_add(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Create ticket formset and check for errors
    ticket_formset = buy_ticket_formset(request, request.POST)

    # Check for errors
    if ticket_formset.is_valid():

        # Get total number of tickets being purchased
        tickets_requested = sum([f.cleaned_data['quantity'] for f in ticket_formset])
        if (tickets_requested > 0) and (tickets_requested <= performance.tickets_available()):

            # Process ticket types
            for form in ticket_formset:

                # Get ticket type and quantity                
                ticket_type = get_object_or_404(TicketType, pk =  form.cleaned_data['id'])
                quantity = form.cleaned_data['quantity']

                # Create tickets and add to basket
                if quantity > 0:
                    for i in range(0, quantity):
                        ticket = Ticket(
                            performance = performance,
                            type = ticket_type,
                            user = request.user,
                            basket = basket,
                        )
                        ticket.save()

                    # Confirm purchase
                    logger.info(f"{quantity} x {ticket_type.name} tickets for {performance.show.name} on {performance.date} at {performance.time} added to basket")
                    messages.success(request, f"{quantity} x {ticket_type.name} tickets added to basket.")

            # Confirm purchase
            return HttpResponseClientRedirect(reverse('tickets:buy_tickets_confirm', args = [performance.uuid]))

        # Insufficient tickets available
        else:
            available = performance.tickets_available()
            logger.info(f"Insufficient tickets ({tickets_requested} requested, {available} available) for {performance.show.name} on {performance.date} at {performance.time}")
            messages.error(request, f"There are only {available} tickets available for this perfromance.")

    else:
        messages.error(request, f"Please correct the errors below and try again.")

    # Render updated tickets tab
    return buy_render_tickets(request, performance, ticket_formset)

@require_GET
@login_required
def buy_tickets_add_confirm(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Display confirmation
    context = {
        'basket': basket,
        'performance': performance,
    }
    return render(request, "tickets/buy_tickets_add_confirm.html", context)

@require_POST
@login_required
@transaction.atomic
def buy_fringers_use(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Check if there are still enough tickets available
    tickets_requested = len(request.POST.getlist('fringer_id'))
    if (tickets_requested > 0) and (tickets_requested <= performance.tickets_available()):

        # Create a sale
        sale = Sale(
            festival = request.festival,
            user = request.user,
            customer = request.user.email,
            completed = timezone.now(),
        )
        sale.save()

        # Process each checked fringer
        for fringer_id in request.POST.getlist('fringer_id'):

            # Get fringer and double check that it has not been used for this performance
            fringer = Fringer.objects.get(pk = int(fringer_id))
            if fringer.is_available(performance):

                # Create ticket and add to sale
                ticket = Ticket(
                    user = request.user,
                    performance = performance,
                    type = fringer.type.ticket_type,
                    fringer = fringer,
                    sale = sale,
                )
                ticket.save()

                # Confirm purchase
                logger.info(f"Ticket for {performance.show.name} on {performance.date} at {performance.time} purchased with eFringer {fringer.name}")
                messages.success(request, f"Ticket purchased with eFringer {fringer.name}")

            else:
                # Fringer already used for this performance
                logger.warn(f"eFringer {fringer.name} already used for this perfromance")

        # Confirm purchase
        return HttpResponseClientRedirect(reverse('tickets:buy_fringers_use_confirm', args = [performance.uuid]))

    # Insufficient tickets available
    else:
        available = performance.tickets_available()
        logger.info(f"Insufficient tickets ({tickets_requested} requested, {available} available) for {performance.show.name} on {performance.date} at {performance.time}")
        messages.error(request, f"There are only {available} tickets available for this perfromance.")

    # Render updated fringers tab content
    return buy_render_fringers(request, performance)

@require_GET
@login_required
def buy_fringers_use_confirm(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Display confirmation
    context = {
        'basket': basket,
        'performance': performance,
    }
    return render(request, "tickets/buy_fringers_use_confirm.html", context)

@require_POST
@login_required
@transaction.atomic
def buy_fringers_add(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Create buy fringer form
    fringer_form = buy_fringer_form(request, request.POST)

    # Check for errors
    if fringer_form.is_valid():

        # Get fringer type and name
        fringer_type = get_object_or_404(FringerType, pk = int(fringer_form.cleaned_data['type']))
        fringer_name = fringer_form.cleaned_data['name']
        if not fringer_name:
            fringer_count = Fringer.objects.filter(user = request.user).count()
            fringer_name = f"eFringer{fringer_count + 1}"

        # Create new fringer and add to basket
        fringer = Fringer(
            user = request.user,
            type = fringer_type,
            name = fringer_name,
            basket = basket,
        )
        fringer.save()
        logger.info(f"eFringer {fringer.name} ({fringer.description}) added to basket")
        messages.success(request, f"eFringer {fringer.name} ({fringer.description}) added to basket")

        # Confirm purchase
        return HttpResponseClientRedirect(reverse('tickets:buy_fringers_add_confirm', args = [performance.uuid]))

    # Render updated fringers tab content
    return buy_render_fringers(request, performance, fringer_form)

@require_GET
@login_required
def buy_fringers_add_confirm(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Display confirmation
    context = {
        'basket': basket,
        'performance': performance,
    }
    return render(request, "tickets/buy_fringers_add_confirm.html", context)

@require_POST
@login_required
@transaction.atomic
def buy_volunteer_use(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Check if there are still enough tickets available
    if (performance.tickets_available() > 0):

        # Create a sale
        sale = Sale(
            festival = request.festival,
            user = request.user,
            customer = request.user.email,
            completed = timezone.now(),
        )
        sale.save()

        # Add volunteer ticket to sale
        ticket = Ticket(
            user = request.user,
            performance = performance,
            type = request.festival.volunteer_ticket_type,
            sale = sale,
        )
        ticket.save()

        # Confirm purchase
        logger.info(f"Ticket for {performance.show.name} on {performance.date} at {performance.time} purchased using volunteer credit.")
        messages.success(request, f"Volunteer ticket used")

        # Confirm purchase
        return HttpResponseClientRedirect(reverse('tickets:buy_volunteer_use_confirm', args = [performance.uuid]))

    # Insufficient tickets available
    else:
        logger.info(f"Insufficient tickets (1 requested, {performance.tickets_available()} available) for {performance.show.name} on {performance.date} at {performance.time}")
        messages.error(request, f"There are no tickets available for this perfromance.")

    # Render updated volunteer tab content
    return buy_render_volunteer(request, performance)

@require_GET
@login_required
def buy_volunteer_use_confirm(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Display confirmation
    context = {
        'basket': basket,
        'performance': performance,
    }
    return render(request, "tickets/buy_volunteer_use_confirm.html", context)

# PAYW
@require_GET
@login_required
def payw(request, show_uuid):

    # Get show details
    show = get_object_or_404(Show, uuid = show_uuid)

    # Get fringers available
    fringers = Fringer.get_available(request.user)

    # Display PAYW page
    context = {
        'show': show,
        'fringers': fringers,
    }
    return render(request, "tickets/payw.html", context)

@require_POST
@login_required
@transaction.atomic
def payw_donate(request, show_uuid):

    # Get show details
    show = get_object_or_404(Show, uuid = show_uuid)

    # Check if any fringers are selected
    fringer_ids = request.POST.getlist('fringer_id')
    if fringer_ids:

        # Create a sale
        sale = Sale(
            festival = request.festival,
            user = request.user,
            customer = request.user.email,
            completed = timezone.now(),
        )
        sale.save()
        logger.info(f"Sale { sale.id } crfeated for eFringer PAYW donation to { show.name }")

        # Create donations for each fringer seleted
        for fringer_id in fringer_ids:

            # Get fringer and donate to this show
            fringer = Fringer.objects.get(pk = int(fringer_id))
            payw = PayAsYouWill(
                sale = sale,
                show = show,
                fringer = fringer,
                amount = fringer.ticket_type.payment,
            )
            payw.save()

            # Confirm donation
            logger.info(f"eFringer {fringer.name} PAYW donation added to sale { sale.id }")
            messages.success(request, f"eFringer {fringer.name} credit donated to { show.name }")

        # Return to show page
        return redirect(reverse("program:show", args=[show.uuid]))
        
    # No fringers selected so redisplay
    messages.warning(request, f"No fringers selected for donation")
    fringers = Fringer.get_available(request.user)
    context = {
        'show': show,
        'fringers': fringers,
    }
    return render(request, "tickets/payw.html", context)

# Checkout
def checkout_buttons_form(basket, post_data=None):

    # Create form
    initial_data = { 'buttons': basket.buttons }
    form = CheckoutButtonsForm(initial=initial_data, data=post_data)

    # Add crispy form helper
    form.helper = FormHelper()
    form.helper.form_id = 'buttons-form'
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-6'
    form.helper.field_class = 'col-6'

    # Return form
    return form

def render_checkout_buttons(request, form=None):
    context = {
        'buttons_form': form,
    }
    return render(request, "tickets/_checkout_buttons.html", context)

def render_checkout_pay(request, basket, form=None):
    if not form:
        form = checkout_buttons_form(basket)
    context = {
        'basket': basket,
        'buttons_form': form,
    }
    return render(request, "tickets/_checkout_pay.html", context)

@login_required
@require_GET
def checkout(request):

    # Get basket
    basket = request.user.basket

    # Create buttons form
    form = checkout_buttons_form(basket)

    # Render checkout page
    context = {
        'buttons_form': form,
    }
    return render(request, "tickets/checkout.html", context)

@login_required
@require_POST
@transaction.atomic
def checkout_buttons_add(request):

    # Get basket
    basket = request.user.basket

    # Create buttons form
    form = checkout_buttons_form(basket, request.POST)

    # Check for errors
    if form.is_valid():

        # Add buttons to basket and proceed to payment
        basket.buttons = form.cleaned_data['buttons']
        basket.save()
        return render_checkout_pay(request, basket)

    # Re-display buttons form with errors
    return render_checkout_buttons(request, form)

@login_required
@require_POST
@transaction.atomic
def checkout_buttons_none(request):

    # Get basket
    basket = request.user.basket

    # Clear buttons and proceed to payment
    basket.buttons = 0
    basket.save()
    return render_checkout_pay(request, basket)

@login_required
@require_POST
@transaction.atomic
def checkout_buttons_update(request):

    # Get basket
    basket = request.user.basket

    # Create buttons form
    form = checkout_buttons_form(basket, request.POST)

    # Check for errors
    if form.is_valid():

        # Update buttons 
        basket.buttons = form.cleaned_data['buttons']
        basket.save()
        form = None

    # Re-display buttons form with errors
    return render_checkout_pay(request, basket, form)

@login_required
@require_POST
@csrf_exempt
@transaction.atomic
def checkout_performance_remove(request, performance_uuid):

    # Get basket and performance
    basket = request.user.basket
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Delete all tickets for the performance
    for ticket in basket.tickets.filter(performance = performance):
        logger.info(f"{ticket.description} ticket for {performance.show.name} on {performance.date} at {performance.time} removed from basket {basket.user.id}")
        ticket.delete()
    messages.success(request, f"{performance.show.name} removed from basket {basket.user.id}")

    # Redisplay payment details
    return render_checkout_pay(request, basket)

@login_required
@require_POST
@csrf_exempt
@transaction.atomic
def checkout_ticket_remove(request, ticket_uuid):

    # Get basket and ticket to be removed
    basket = request.user.basket
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)

    # Delete ticket
    logger.info(f"{ticket.description} ticket for {ticket.performance.show.name} on {ticket.performance.date} at {ticket.performance.time} removed from basket {basket.user.id}")
    messages.success(request, f"{ticket.description} ticket for {ticket.performance.show.name} removed from basket")
    ticket.delete()

    # Redisplay payment details
    return render_checkout_pay(request, basket)

@login_required
@require_POST
@csrf_exempt
@transaction.atomic
def checkout_fringer_remove(request, fringer_uuid):

    # Get basket and fringer to be removed
    basket = request.user.basket
    fringer = get_object_or_404(Fringer, uuid = fringer_uuid)

    # Delete fringer
    logger.info(f"eFringer {fringer.name} removed from basket {basket.user.id}")
    messages.success(request, f"Fringer {fringer.name} removed from basket")
    fringer.delete()

    # Redisplay payment details
    return render_checkout_pay(request, basket)

@login_required
@require_POST
def checkout_stripe(request):

    # Get basket
    basket = request.user.basket

    # Check that tickets are still available
    tickets_available = True
    for p in basket.tickets.values('performance').annotate(count = Count('performance')):
        performance = ShowPerformance.objects.get(pk = p["performance"])
        available = performance.tickets_available()
        if p["count"] > available:
            messages.error(request, f"Your basket contains {p['count']} tickets for {performance.show.name} but there are only {available} tickets available.")
            logger.info(f"Basket contains {p['count']} tickets for {performance.show.name} but there are only {available} available")
            tickets_available = False

    # If tickets no longer available redisplay checkout with notifications
    if not tickets_available:
        messages.error(request, "Your card has not been charged.")
        context = {
            'basket': basket
        }
        return render(request, "tickets/checkout.html", context)

    # Use a transaction to protect the conversion of basket to sale and creation of Stripe session
    with transaction.atomic():

        # Move tickets and fringers from basket to sale
        sale = Sale(
            festival = request.festival,
            user = request.user,
            customer = request.user.email,
            amount = basket.total_cost,
            transaction_type = Sale.TRANSACTION_TYPE_STRIPE,
            transaction_fee = 0,
        )
        sale.save()
        logger.info(f"Sale {sale.id} created")
        for ticket in basket.tickets.all():
            ticket.basket = None
            ticket.sale = sale
            ticket.save()
            logger.info(f"{ticket.description} ticket for {ticket.performance.show.name} on {ticket.performance.date} at {ticket.performance.time} added to sale {sale.id}")
        for fringer in basket.fringers.all():
            fringer.basket = None
            fringer.sale = sale
            fringer.save()
            logger.info(f"eFringer {fringer.name} added to sale {sale.id}")
        sale.button = basket.buttons
        sale.save()
        basket.buttons = 0
        basket.save()

        # Create Stripe session
        stripe.api_key = settings.STRIPE_PRIVATE_KEY
        session = stripe.checkout.Session.create(
            client_reference_id = str(sale.id),
            customer_email = basket.user.email,
            payment_method_types = ['card'],
            mode = 'payment',
            line_items = [{
                'price_data': {
                    'currency': 'GBP',
                    'unit_amount': int(sale.total_cost * 100),
                    'product_data': {
                        'name': 'Theatrefest',
                        'description': 'Tickets and eFringers',
                    },
                },
                'quantity': 1,
            }],
            success_url = request.build_absolute_uri(reverse('tickets:checkout_success', args=[sale.uuid])),
            cancel_url = request.build_absolute_uri(reverse('tickets:checkout_cancel', args=[sale.uuid])),
        )
        logger.info(f"Stripe PI {session.id} created for sale {sale.id}")
        sale.transaction_ID = session.id
        sale.save()

    return redirect(session.url, code=303)

@login_required
@require_GET
def checkout_success(request, sale_uuid):

    # Get sale and mark as complete
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    sale.completed = timezone.now()
    sale.save()
    logger.info(f"Stripe payment for sale {sale.id} succeeded")
    logger.info(f"Credit card charged £{sale.total_cost:2f}")
    logger.info(f"Sale {sale.id} completed")

    # Send e-mail to confirm tickets
    if sale.tickets:
        context = {
            'festival': request.festival,
            'tickets': sale.tickets.order_by('performance__date', 'performance__time', 'performance__show__name'),
        }
        body = render_to_string('tickets/sale_email.txt', context)
        send_mail('Tickets for ' + request.festival.title, body, settings.DEFAULT_FROM_EMAIL, [request.user.email])

    # Display confirmation
    context = {
        'sale': sale,
    }
    return render(request, 'tickets/checkout_confirm.html', context)


@login_required
@require_GET
def checkout_cancel(request, sale_uuid):

    # Get basket and sale
    basket = request.user.basket
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    logger.info(f"Stripe payment for sale {sale.id} cancelled")

    # Move sale items back into basket and delete sale
    for ticket in sale.tickets.all():
        ticket.basket = basket
        ticket.sale = None
        ticket.save()
        logger.info(f"{ticket.description} ticket for {ticket.performance.show.name} on {ticket.performance.date} at {ticket.performance.time} returned to basket {basket.user.id}")
    for fringer in sale.fringers.all():
        fringer.basket = basket
        fringer.sale = None
        fringer.save()
        logger.info(f"eFringer {fringer.name} returned to basket {basket.user.id}")
    basket.buttons = sale.buttons
    basket.save()
    sale.buttons = 0
    sale.amount = 0
    sale.transaction_type = None
    sale.transaction_fee = 0
    sale.cancelled = timezone.now()
    sale.save()
    logger.info(f"Sale {sale.id} cancelled")

    # Display checkout with notification
    messages.error(request, f"Payment cancelled. Your card has not been charged.")
    context = {
        'basket': basket
    }
    return render(request, "tickets/checkout.html", context)

@require_GET
def donations(request):

    return render(request, 'tickets/donations.html')

@require_POST
@csrf_exempt
def donation_stripe(request):

    amount = int(request.POST['donationAmount'])
    email = request.POST['donationEmail']

    try:
        # Create Stripe session
        stripe.api_key = settings.STRIPE_PRIVATE_KEY
        session = stripe.checkout.Session.create(
            customer_email = email,
            payment_method_types = ['card'],
            mode = 'payment',
            line_items = [{
                'price_data': {
                    'currency': 'GBP',
                    'unit_amount': int(amount * 100),
                    'product_data': {
                        'name': 'Theatrefest',
                        'description': 'Donation',
                    },
                },
                'quantity': 1,
            }],
            success_url = request.build_absolute_uri(reverse('tickets:donation_success') + f"?amount={amount}&email={email}"),
            cancel_url = request.build_absolute_uri(reverse('tickets:donation_cancel')),
        )

        return redirect(session.url, code=303)

    except Exception as e:
        return HttpResponse(f'Error: {e.message}')


@require_GET
def donation_success(request):

    # Save donation details
    donation = Donation(
        festival = request.festival,
        amount = request.GET["amount"],
        email = request.GET['email'],
    )
    donation.save()
    logger.info("Donation of £%s received from %s", donation.amount, donation.email)

    # Confirm donation received
    messages.success(request, "Donaction completed")
    return render(request, 'tickets/donation_success.html')

@require_GET
def donation_cancel(request):

    messages.info(request, "Donaction cancelled")
    return redirect(reverse("tickets:donations"))

# PDF generation
import os
from django.conf import settings
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

@require_GET
@login_required
def print_sale(request, sale_uuid):

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
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
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
    story.append(Spacer(1, 0.5*cm))

    # Fringers
    if sale.fringers.count():
        tableData = []
        for fringer in sale.fringers.all():
            tableData.append(("eFringer", fringer.name, fringer.description, f"£{fringer.price}"))
            table = Table(
                tableData,
                colWidths = (4*cm, 4*cm, 4*cm, 4*cm),
                hAlign = 'LEFT',
                style = (
                    ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                )
            )
        story.append(table)
        story.append(Spacer(1, 0.5*cm))

    # Tickets
    if sale.tickets:
        is_first = True
        for performance in sale.ticket_performances:
            if not is_first:
                story.append(Spacer(1, 0.3*cm))
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
        story.append(Spacer(1, 0.5*cm))

    # Total
    table = Table(
        (
            ("", Paragraph("<para><b>Total:</b></para>", styles['Normal']), f"£{sale.amount}"),
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

@require_GET
@login_required
def print_performance(request, performance_uuid):

    # Get performance to be printed
    performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

    # Create a Platypus story
    response = HttpResponse(content_type = "application/pdf")
    response["Content-Disposition"] = f"filename=performance{performance.id}.pdf"
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
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Tickets
    tableData = []
    tableData.append((Paragraph(f"<para><b>{performance.show.name}</b></para>", styles['Normal']), "", "", ""))
    tableData.append((f"{performance.date:%a, %e %b} at {performance.time:%I:%M %p}", "", "", ""))
    for ticket in request.user.tickets.filter(performance_id = performance.id):
        tableData.append((f"{ticket.id}", "", ticket.description, f"£{ticket.price}"))
    table = Table(
        tableData,
        colWidths = (4*cm, 4*cm, 4*cm, 4*cm),
        hAlign = 'LEFT',
        style = (
            ('SPAN', (0, 0), (3, 0)),
            ('SPAN', (0, 1), (3, 1)),
            ('ALIGN', (0, 2), (0, -1), 'RIGHT'),
            ('ALIGN', (3, 2), (3, -1), 'RIGHT'),
        )
    )
    story.append(table)

    # Create PDF document and return it
    doc.build(story)
    return response
