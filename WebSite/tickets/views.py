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
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from .models import Sale, Refund, Basket, FringerType, Fringer, TicketType, Ticket, Donation
from .forms import BuyTicketForm, RenameFringerForm, BuyFringerForm
from program.models import Show, ShowPerformance

# Logging
import logging
logger = logging.getLogger(__name__)

# Stripe interface
import stripe
stripe.api_key = settings.STRIPE_PRIVATE_KEY


class MyAccountView(LoginRequiredMixin, View):

    def _get_performances(self, user):
        current = []
        past = []
        for ticket in user.tickets.filter(basket = None, refund = None).order_by('performance__date', 'performance__time', 'performance__show__name').values('performance_id').distinct():
            performance = ShowPerformance.objects.get(pk = ticket['performance_id'])
            tickets = user.tickets.filter(performance_id = ticket['performance_id'], sale__completed__isnull = False, refund__isnull = True)
            p = {
                'id': performance.id,
                'uuid': performance.uuid,
                'show': performance.show.name,
                'date' : performance.date,
                'time': performance.time,
                'tickets': [{'id': t.id, 'uuid': t.uuid, 'description': t.description, 'cost': t.cost, 'fringer_name': (t.fringer.name if t.fringer else None)} for t in tickets],
            }
            if datetime.combine(performance.date, performance.time) >= datetime.now():
                current.append(p)
            else:
                past.append(p)
        return (current, past)

    def _create_fringer_formset(self, user, post_data=None):
        FringerFormSet = modelformset_factory(Fringer, form = RenameFringerForm, extra = 0)
        formset = FringerFormSet(post_data, queryset = user.fringers.exclude(sale__completed__isnull = True))
        return formset

    def _create_buy_fringer_form(self, fringer_types, user, post_data=None):
        form = BuyFringerForm(user, fringer_types, post_data)
        return form

    def get(self, request):

        # Get tickets grouped by performance
        performances_current, performances_past = self._get_performances(request.user)

        # Create fringer formset
        formset = self._create_fringer_formset(request.user)

        # Get fringer types and create buy form
        fringer_types = FringerType.objects.filter(festival=request.festival, is_online=True)
        buy_form = self._create_buy_fringer_form(fringer_types, request.user)

        # Display tickets and fringers
        context = {
            'sales_open': request.user.is_superuser or (date.today() >= date(2018, 6, 1)),
            'tab': 'tickets',
            'performances_current': performances_current,
            'performances_past': performances_past,
            'basket': request.user.basket,
            'formset': formset,
            'buy_form': buy_form,
        }
        return render(request, 'tickets/myaccount.html', context)

    @transaction.atomic
    def post(self, request):

        # Get the action and basket
        action = request.POST.get("action")
        basket = request.user.basket
        fringer_types = FringerType.objects.filter(festival=request.festival, is_online=True)
        formset = None
        buy_form = None

        # Check for rename
        if action == "RenameFringers":

            # Create fringer formset
            formset = self._create_fringer_formset(request.user, request.POST)

            # Check for errors
            if formset.is_valid():

                # Save changes
                for fringer in formset.save():
                    logger.info("eFringer renamed to %s", fringer.name)
                    messages.success(request, f"eFringer renamed to {fringer.name}")

                # Reset formset
                formset = None

        # Check for buying
        elif action == "AddFringers":

            # Get fringer types and create form
            buy_form = self._create_buy_fringer_form(fringer_types, request.user, request.POST)

            # Check for errors
            if buy_form.is_valid():

                # Get fringer type
                buy_type = get_object_or_404(FringerType, pk = int(buy_form.cleaned_data['type']))
                buy_name = buy_form.cleaned_data['name']
                if not buy_name:
                    fringer_count = Fringer.objects.filter(user = request.user).count()
                    buy_name = f"eFringer{fringer_count + 1}"

                # Create new fringer and add to basket
                fringer = Fringer(
                    user = request.user,
                    name = buy_name if buy_name else buy_type.name,
                    description = buy_type.description,
                    shows = buy_type.shows,
                    cost = buy_type.price,
                    payment = buy_type.payment,
                    basket = basket,
                )
                fringer.save()
                logger.info("eFringer %s (%s) added to basket", fringer.name, fringer.description)
                messages.success(request, f"Fringer {fringer.name} ({fringer.description}) added to basket")

                # Confirm purchase
                return redirect(reverse('tickets:myaccount_confirm_fringers'))

        # Get tickets grouped by performance
        performances_current, performances_past = self._get_performances(request.user)

        # Create formset and buy form if not already done
        if not formset:
            formset = self._create_fringer_formset(request.user)
        if not buy_form:
            buy_form = self._create_buy_fringer_form(fringer_types, request.user)

        # Redisplay with confirmation
        context = {
            'sales_open': request.user.is_admin or (request.festival.online_slaes_open and (date.today() >= request.festival.online_slaes_open)),
            'tab': 'fringers',
            'performances_current': performances_current,
            'performances_past': performances_past,
            'basket': basket,
            'formset': formset,
            'buy_form': buy_form,
        }
        return render(request, 'tickets/myaccount.html', context)


class MyAccountConfirmFringersView(View):

    def get(self, request):

        # Render confirmation
        return render(request, 'tickets/myaccount_confirm_fringers.html')


class BuyView(LoginRequiredMixin, View):

    def get_ticket_formset(self, ticket_types, post_data=None):
        TicketFormset = formset_factory(BuyTicketForm, extra = 0)
        initial_data = [{'id': t.id, 'name': t.name, 'price': t.price, 'quantity': 0} for t in ticket_types]
        return TicketFormset(post_data, initial = initial_data)

    def _create_buy_fringer_form(self, fringer_types, user, post_data=None):
        form = BuyFringerForm(user, fringer_types, post_data)
        return form

    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
        ticket_types = TicketType.objects.filter(festival=request.festival, is_online = True)
        fringer_types = FringerType.objects.filter(festival=request.festival, is_online=True)

        # Check if online ticket sales are still open
        delta = datetime.combine(performance.date, performance.time) - datetime.now()
        if delta.total_seconds() <= (30 * 60):
            return redirect(reverse('tickets:buy_closed', args = [performance.uuid]))

        # Create buy ticket formset
        ticket_formset = self.get_ticket_formset(ticket_types)

        # Get fringers available for this perfromance
        fringers = Fringer.get_available(request.user, performance)

        # Create buy fringer form
        buy_fringer_form = self._create_buy_fringer_form(fringer_types, request.user)

        # Display buy page
        context = {
            'tab': 'tickets',
            'sales_open': request.user.is_admin or (request.festival.online_sales_open and (date.today() >= request.festival.online_sales_open)),
            'basket': basket,
            'performance': performance,
            'ticket_formset': ticket_formset,
            'fringers': fringers,
            'buy_fringer_form': buy_fringer_form,
        }
        return render(request, "tickets/buy.html", context)

    @transaction.atomic
    def post(self, request, performance_uuid):

        # Get basket, performance and ticket/fringer types
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)
        ticket_types = TicketType.objects.filter(festival=request.festival, is_online = True)
        fringer_types = FringerType.objects.filter(festival=request.festival, is_online=True)

        # Get the requested action
        action = request.POST.get("action")
        tab = None

        # Add tickets to basket
        if action == "AddTickets":

            # Create ticket type formset
            ticket_formset = self.get_ticket_formset(ticket_types, request.POST)

            # Check for errors
            if ticket_formset.is_valid():

                # Get total number of tickets being purchased
                tickets_requested = sum([f.cleaned_data['quantity'] for f in ticket_formset])
                if (tickets_requested > 0) and (tickets_requested <= performance.tickets_available):

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
                                    description = ticket_type.name,
                                    cost = ticket_type.price,
                                    user = request.user,
                                    basket = basket,
                                    payment = ticket_type.payment,
                                )
                                ticket.save()

                            # Confirm purchase
                            logger.info("%d x %s tickets added to basket: %s", quantity, ticket_type, performance)
                            messages.success(request, f"{quantity} x {ticket_type} tickets added to basket.")

                    # Confirm purchase
                    return redirect(reverse('tickets:buy_confirm_tickets', args = [performance.uuid]))

                # Insufficient tickets available
                else:
                    logger.info("Tickets not available (%d requested, %d available): %s", tickets_requested, performance.tickets_available, performance)
                    messages.error(request, f"There are only {performance.tickets_available} tickets available for this perfromance.")

            # Reset buy fringer form
            buy_fringer_form = self._create_buy_fringer_form(fringer_types, request.user)
            tab = 'tickets',

        # Use fringer credits
        elif action == "UseFringers":

            # Check if there are still enough tickets available
            tickets_requested = len(request.POST.getlist('fringer_id'))
            if (tickets_requested > 0) and (tickets_requested <= performance.tickets_available):

                # Create a sale
                sale = Sale(
                    festival = request.festival,
                    user = request.user,
                    customer = request.user.email,
                    completed = datetime.now(),
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
                            description = 'eFringer',
                            cost = 0,
                            fringer = fringer,
                            sale = sale,
                            payment = fringer.payment,
                        )
                        ticket.save()

                        # Confirm purchase
                        logger.info("Ticket purchased with eFringer (%s): %s", fringer.name, performance)
                        messages.success(request, f"Ticket purchased with eFringer {fringer.name}")

                    else:
                        # Fringer already used for this performance
                        logger.warn("eFringer (%s) already used: %s", fringer.name, performance)

                # Confirm purchase
                return redirect(reverse('tickets:buy_confirm_fringer_tickets', args = [performance.uuid]))

            # Insufficient tickets available
            else:
                logger.info("Tickets not available (%d requested, %d available): %s", tickets_requested, performance.tickets_available, performance)
                messages.error(request, f"There are only {performance.tickets_available} tickets available for this perfromance.")

            # Reset ticket formset and buy fringer form
            ticket_formset = self.get_ticket_formset(ticket_types)
            buy_fringer_form = self._create_buy_fringer_form(fringer_types, request.user)
            tab = 'fringers',

        # Add fringer vouchers to basket
        elif action == "AddFringers":

            # Create buy fringer form
            buy_fringer_form = self._create_buy_fringer_form(fringer_types, request.user, request.POST)

            # Check for errors
            if buy_fringer_form.is_valid():

                # Get fringer type and name
                fringer_type = get_object_or_404(FringerType, pk = int(buy_fringer_form.cleaned_data['type']))
                fringer_name = buy_fringer_form.cleaned_data['name']
                if not fringer_name:
                    fringer_count = Fringer.objects.filter(user = request.user).count()
                    fringer_name = f"eFringer{fringer_count + 1}"

                # Create new fringer and add to basket
                fringer = Fringer(
                    user = request.user,
                    name = fringer_name,
                    description = fringer_type.description,
                    shows = fringer_type.shows,
                    cost = fringer_type.price,
                    basket = basket,
                )
                fringer.save()
                logger.info("eFringer %s (%s) added to basket", fringer.name, fringer.description)
                messages.success(request, f"Fringer {fringer.name} ({fringer.description}) added to basket")

                # Confirm purchase
                return redirect(reverse('tickets:buy_confirm_fringers', args = [performance.uuid]))

            # Reset ticket formset
            ticket_formset = self.get_ticket_formset(ticket_types, None)
            tab = 'fringers',

        # Get fringers available for this performance
        fringers = Fringer.get_available(request.user, performance)

        # Display buy page
        context = {
            'tab': 'fringers',
            'sales_open': request.user.is_superuser or (date.today() >= date(2018, 6, 1)),
            'basket': basket,
            'performance': performance,
            'ticket_formset': ticket_formset,
            'fringers': fringers,
            'buy_fringer_form': buy_fringer_form,
        }
        return render(request, "tickets/buy.html", context)


class BuyClosedView(LoginRequiredMixin, View):

    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

        # Display closed page
        context = {
            'basket': basket,
            'performance': performance,
            'last_30mins': (datetime.combine(performance.date, performance.time) - datetime.now()).total_seconds() > 0,
        }
        return render(request, "tickets/buy_closed.html", context)


class BuyConfirmTicketsView(LoginRequiredMixin, View):

    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

        # Display confirmation
        context = {
            'basket': basket,
            'performance': performance,
        }
        return render(request, "tickets/buy_confirm_tickets.html", context)


class BuyConfirmFringerTicketsView(LoginRequiredMixin, View):

    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

        # Display confirmation
        context = {
            'basket': basket,
            'performance': performance,
        }
        return render(request, "tickets/buy_confirm_fringer_tickets.html", context)


class BuyConfirmFringersView(LoginRequiredMixin, View):

    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

        # Display confirmation
        context = {
            'basket': basket,
            'performance': performance,
        }
        return render(request, "tickets/buy_confirm_fringers.html", context)


class CheckoutView(LoginRequiredMixin, View):

    def get(self, request):

        # Get basket
        basket = request.user.basket

        # Display basket
        context = {
            'basket': basket,
            'stripe_key': settings.STRIPE_PUBLIC_KEY,
        }
        return render(request, "tickets/checkout.html", context)

class CheckoutRemoveFringerView(LoginRequiredMixin, View):

    @transaction.atomic
    def get(self, request, fringer_uuid):

        # Get basket and fringer to be removed
        basket = request.user.basket
        fringer = get_object_or_404(Fringer, uuid = fringer_uuid)

        # Delete fringer
        logger.info("eFringer %s (%s) removed from basket", fringer.name, fringer.description)
        messages.success(request, f"Fringer {fringer.name} ({fringer.description}) removed from basket")
        fringer.delete()

        # Redisplay checkout
        return redirect(reverse("tickets:checkout"))


class CheckoutRemovePerformanceView(LoginRequiredMixin, View):

    @transaction.atomic
    def get(self, request, performance_uuid):

        # Get basket and performance
        basket = request.user.basket
        performance = get_object_or_404(ShowPerformance, uuid = performance_uuid)

        # Delete all tickets for the performance
        for ticket in basket.tickets.filter(performance = performance):
            logger.info("%s ticket for %s removed from basket", ticket.description, ticket.performance)
            ticket.delete()
        messages.success(request, f"{performance} removed from basket")

        # Redisplay checkout
        return redirect(reverse("tickets:checkout"))


class CheckoutRemoveTicketView(LoginRequiredMixin, View):

    @transaction.atomic
    def get(self, request, ticket_uuid):

        # Get basket and ticket to be removed
        basket = request.user.basket
        ticket = get_object_or_404(Ticket, uuid = ticket_uuid)

        # Delete ticket
        logger.info("%s ticket for %s removed from basket", ticket.description, ticket.performance)
        messages.success(request, f"{ticket.description} ticket for {ticket.performance} removed from basket")
        ticket.delete()

        # Redisplay checkout
        return redirect(reverse("tickets:checkout"))


class CheckoutConfirmView(View):

    def get(self, request, sale_uuid):

        # Get sale
        sale = get_object_or_404(Sale, uuid = sale_uuid)

        # Render confirmation
        context = {
            'sale': sale,
        }
        return render(request, 'tickets/checkout_confirm.html', context)


@login_required
@require_POST
def checkout_stripe(request):

    # Get basket
    basket = request.user.basket

    # Check that tickets are still available
    tickets_available = True
    for p in basket.tickets.values('performance').annotate(count = Count('performance')):
        performance = ShowPerformance.objects.get(pk = p["performance"])
        if p["count"] > performance.tickets_available:
            messages.error(request, f"Your basket contains {p['count']} tickets for {performance} but there are only {performance.tickets_available} tickets available.")
            logger.warn("Basket contains %d tickets but only %d available: %s", p["count"], performance.tickets_available, performance)
            tickets_available = False

    # If tickets no longer available redisplay checkout with notifications
    if not tickets_available:
        messages.error(request, f"Your card has not been charged.")
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
            stripe_fee = basket.stripe_fee,
        )
        sale.save()
        for ticket in basket.tickets.all():
            ticket.basket = None
            ticket.sale = sale
            ticket.save()
            logger.info("Purchase complete: %s ticket for %s", ticket.description, ticket.performance)
        for fringer in basket.fringers.all():
            fringer.basket = None
            fringer.sale = sale
            fringer.save()
            logger.info("Purchase complete: eFringer (%s)", fringer.name)

        # Create Stripe session
        stripe.api_key = settings.STRIPE_PRIVATE_KEY
        session = stripe.checkout.Session.create(
            client_reference_id = str(sale.id),
            customer_email = basket.user.email,
            payment_method_types = ['card'],
            mode = 'payment',
            line_items = [
                {
                    'name': 'Theatrefest',
                    'description': 'Tickets and eFringers',
                    'amount': int(sale.stripe_charge * 100),
                    'currency': 'GBP',
                    'quantity': 1,
                },
            ],
            success_url = request.build_absolute_uri(reverse('tickets:checkout_success', args=[sale.uuid])),
            cancel_url = request.build_absolute_uri(reverse('tickets:checkout_cancel', args=[sale.uuid])),
        )

    return redirect(session.url, code=303)


@login_required
@require_GET
def checkout_success(request, sale_uuid):

    # Get sale and mark as complete
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    sale.completed = datetime.now()
    sale.save()
    logger.info("Credit card charged GBP%.2f", sale.stripe_charge)
    logger.info("Sale %s completed", sale.id)

    # Send e-mail to confirm tickets
    if sale.tickets:
        context = {
            'festival': request.festival,
            'tickets': sale.tickets.order_by('performance__date', 'performance__time', 'performance__show__name')
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

    # Move sale items back into basket and delete sale
    for ticket in sale.tickets.all():
        ticket.basket = basket
        ticket.sale = None
        ticket.save()
        logger.info("Purchase cancelled: %s ticket for %s", ticket.description, ticket.performance)
    for fringer in sale.fringers.all():
        fringer.basket = basket
        fringer.sale = None
        fringer.save()
        logger.info("Purchase cancelled: eFringer (%s)", fringer.name)
    sale.delete()

    # Display checkout with notification
    messages.error(request, f"Payment cancelled. Your card has not been charged.")
    context = {
        'basket': basket
    }
    return render(request, "tickets/checkout.html", context)

@transaction.atomic
@login_required
def ticket_cancel(request, ticket_uuid):

    # Get ticket to be cancelled
    ticket = get_object_or_404(Ticket, uuid = ticket_uuid)

    # Create a refund and add the ticket
    refund = Refund(
        festival = request.festival,
        user = request.user,
        customer = request.user.email,
        completed = datetime.now(),
    )
    refund.save()
    ticket.refund = refund
    ticket.save()
    logger.info("%s ticket for %s cancelled", ticket.description, ticket.performance)
    messages.success(request, f"{ticket.description} ticket for {ticket.performance} cancelled")

    # Redisplay tickets
    return redirect(reverse("tickets:myaccount"))

@require_GET
def donations(request):

    context = {
        'stripe_key': settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, 'tickets/donations.html', context)

@require_POST
@csrf_exempt
def donation_stripe(request):

    amount = int(request.POST['donationAmount'])
    email = request.POST['donationEmail']

    try:
        session = stripe.checkout.Session.create(
            customer_email = email,
            payment_method_types = ['card'],
            line_items = [
                {
                    'name': 'Theatrefest',
                    'description': 'Donation',
                    'amount': amount * 100,
                    'currency': 'GBP',
                    'quantity': 1,
                },
            ],
            mode = 'payment',
            success_url = request.build_absolute_uri(reverse('tickets:donation_success') + f"?amount={amount}&email={email}"),
            cancel_url = request.build_absolute_uri(reverse('tickets:donation_cancel')),
        )

        return redirect(session.url, code=303)

    except Exception as e:
        return HttpResponse('Error')

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


class PrintSaleView(LoginRequiredMixin, View):

    def get(self, request, sale_uuid):

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
                tableData.append(("eFringer", fringer.name, fringer.description, f"£{fringer.cost}"))
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
            for performance in sale.performances:
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

        # Stripe fee
        table = Table(
            (
                ("", Paragraph("<para><b>Card fee:</b></para>", styles['Normal']), f"£{sale.stripe_fee}"),
            ),
            colWidths = (8*cm, 4*cm, 4*cm),
            hAlign = 'LEFT',
            style = (
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
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


class PrintPerformanceView(LoginRequiredMixin, View):

    def get(self, request, performance_uuid):

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
            tableData.append((f"{ticket.id}", "", ticket.description, f"£{ticket.cost}"))
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
