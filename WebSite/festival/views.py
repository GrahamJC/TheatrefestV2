import os

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.core.mail import send_mail

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from core.models import Festival, User

from tickets.models import BoxOffice, Sale

from .forms import PasswordResetForm, EMailForm, AdminSaleListForm, AdminSetupForm

# Logging
import logging
logger = logging.getLogger(__name__)


def archive_index(request):

    # Clear festival from session
    try:
        del request.session['festival_id']
    except KeyError:
        pass

    # Redirect to archive
    #return redirect('https://archive.theatrefest.co.uk/archive/index.htm')
    return redirect('/static/ionos/archive/index.htm')


def archive_home(request):

    # Clear festival from session
    try:
        del request.session['festival_id']
    except KeyError:
        pass

    # Redirect to home page
    return redirect('home')


def archive_festival(request, festival_name):

    # Get festival and save it in the session
    festival = get_object_or_404(Festival, name=festival_name)
    request.session['festival_id'] = festival.id

    # Redirect to show listing
    return redirect('program:shows')


@user_passes_test(lambda u: u.is_admin)
@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.festival,
    }
    return render(request, 'festival/admin.html', context)


class AdminSetupView(LoginRequiredMixin, View):

    def _get_form(self, festival, post_data = None):
        form = AdminSetupForm(instance=festival, data=post_data)
        helper = FormHelper()
        helper.form_method = 'POST'
        helper.layout = Layout(
            Row(
                Column('online_sales_open', css_class='col-6'),
                Column('online_sales_close', css_class='col-6'),
                css_class='form-row',
            ),
            Row(
                Column('boxoffice_open', css_class='col-6'),
                Column('boxoffice_close', css_class='col-6'),
                css_class='form-row',
            ),
            Row(
                Column('button_price'),
                css_class='form-row',
            ),
            Row(
                Column('fringer_price', css_class='col-6'),
                Column('fringer_shows', css_class='col-6'),
                css_class='form-row',
            ),
            Row(
                Column('volunteer_comps'),
                css_class='form-row',
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            )
        )
        form.helper = helper
        return form

    def get(self, request):

        # Render setup form
        form = self._get_form(request.festival)
        context = {
            'festival': request.festival,
            'breadcrumbs': [
                { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
                { 'text': 'Setup' },
            ],
            'form': form,
        }
        return render(request, 'festival/admin_setup.html', context)

    def post(self, request):

        # Get setup form and update festival
        form = self._get_form(request.festival, request.POST)
        if form.is_valid():
            festival = request.festival
            festival.online_sales_open = form.cleaned_data['online_sales_open']
            festival.online_sales_close = form.cleaned_data['online_sales_close']
            festival.boxoffice_open = form.cleaned_data['boxoffice_open']
            festival.boxoffice_close = form.cleaned_data['boxoffice_close']
            festival.button_price = form.cleaned_data['button_price']
            festival.fringer_price = form.cleaned_data['fringer_price']
            festival.fringer_shows = form.cleaned_data['fringer_shows']
            festival.volunteer_comps = form.cleaned_data['volunteer_comps']
            festival.save()

        # Render page
        context = {
            'festival': request.festival,
            'breadcrumbs': [
                { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
                { 'text': 'Sales' },
            ],
            'form': form,
        }
        return render(request, 'festival/admin_setup.html', context)


@user_passes_test(lambda u: u.is_admin)
@login_required
def reports_venue(request):

    # Render the page
    context = {
        'festival': request.festival,
    }
    return render(request, 'festival/reports_venue.html', context)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_user_list(request):

    # Render page
    context = {
        'festival': request.festival,
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Users' },
        ],
        'user_list': User.objects.filter(festival = request.festival).order_by('email')
    }
    return render(request, 'festival/admin_user_list.html', context)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_user_activate(request, user_uuid):

    # Get user and activate
    user = get_object_or_404(User, uuid = user_uuid)
    user.is_active = True
    user.save()
    logger.info(f"User {user.email} activated.")
    messages.success(request, "User activated")

    # Render page
    context = {
        'festival': request.festival,
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Users' },
        ],
        'user_list': User.objects.filter(festival = request.festival).order_by('email')
    }
    return render(request, 'festival/admin_user_list.html', context)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_user_password(request, user_uuid):

    # Get user
    user = get_object_or_404(User, uuid = user_uuid)
    user.is_active = True
    user.save()

    # Process form
    form = PasswordResetForm(data = request.POST)
    if form.is_valid():
        user.set_password(form.cleaned_data['password'])
        user.save()
        logger.info(f"User {user.email} password reset.")
        messages.success(request, "Password reset")
    else:
        logger.info(f"User {user.email} password reset failed.")
        messages.error(request, mark_safe('<br>'.join(form.errors['password'])))

    # Render page
    context = {
        'festival': request.festival,
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Users' },
        ],
        'user_list': User.objects.filter(festival = request.festival).order_by('email')
    }
    return render(request, 'festival/admin_user_list.html', context)


@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_user_email(request):

    # Create form
    form = EMailForm()

    # Render page
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = reverse('festival:admin_user_email_send')
    helper.add_input(Submit('submit', 'Send'))
    form.helper = helper
    context = {
        'festival': request.festival,
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'e-mail' },
        ],
        'form': form
    }
    return render(request, 'festival/admin_user_email.html', context)


@require_POST
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_user_email_send(request):

    # Process form
    form = EMailForm(request.POST)
    if form.is_valid():

        # Send e-mail
        count = 0
        for user in User.objects.filter(festival = request.festival).order_by('email'):
            send_mail(form.cleaned_data['subject'], form.cleaned_data['body'], settings.DEFAULT_FROM_EMAIL, [user.email])
            count = count + 1
        messages.success(request, f"{count} e-mails sent")
        form = EMailForm()

    else:
        messages.error(request, f"e-mail failed")

    # Render page
    helper = FormHelper()
    helper.form_method = 'POST'
    helper.form_action = reverse('festival:admin_user_email_send')
    helper.add_input(Submit('submit', 'Send'))
    form.helper = helper
    context = {
        'festival': request.festival,
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'e-mail' },
        ],
        'form': form
    }
    return render(request, 'festival/admin_user_email.html', context)


class AdminSaleListView(LoginRequiredMixin, View):

    def _get_form(self, festival, post_data = None):
        form = AdminSaleListForm(festival, data = post_data)
        helper = FormHelper()
        helper.form_method = 'POST'
        helper.layout = Layout(
            Row(
                Column('date', css_class='col-4'),
                Column('customer', css_class='col-8'),
                css_class='form-row',
            ),
            Row(
                Column('sale_type', css_class='col-4'),
                Column(Div('boxoffice', 'venue', css_class='col-8')),
                css_class='form-row',
            ),
            FormActions(
                Submit('search', 'Search'),
            )
        )
        form.helper = helper
        return form

    def get(self, request):

        # Render search form
        form = self._get_form(request.festival)
        context = {
            'festival': request.festival,
            'breadcrumbs': [
                { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
                { 'text': 'Sales' },
            ],
            'form': form,
            'sales': None,
        }
        return render(request, 'festival/admin_sale_list.html', context)

    def post(self, request):

        # Get search criteria
        form = self._get_form(request.festival, request.POST)

        # Get results
        sales = None
        if form.is_valid():
            sales = Sale.objects.filter(festival = request.festival, completed__isnull = False)
            date = form.cleaned_data['date']
            if date:
                sales = sales.filter(completed__date = date)
            customer = form.cleaned_data['customer']
            if customer:
                sales = sales.filter(customer__icontains = customer)
            sale_type = form.cleaned_data['sale_type']
            if sale_type == 'Boxoffice':
                boxoffice = form.cleaned_data['boxoffice']
                if boxoffice:
                    sales = sales.filter(boxoffice = boxoffice)
                else:
                    sales = sales.filter(boxoffice__isnull = False)
            elif sale_type == 'Venue':
                venue = form.cleaned_data['venue']
                if venue:
                    sales = sales.filter(venue = venue)
                else:
                    sales = sales.filter(venue__isnull = False)
            elif sale_type == 'Online':
                sales = sales.filter(user__isnull = False)
            sales = sales.order_by('completed__date', 'customer')[:50]
            if sales.count() == 0:
                messages.warning(request, "No sales found")

        # Render search form and result list
        context = {
            'festival': request.festival,
            'breadcrumbs': [
                { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
                { 'text': 'Sales' },
            ],
            'form': form,
            'sales': [
                {
                    'id': sale.id,
                    'uuid': sale.uuid,
                    'date': sale.completed.date,
                    'customer': sale.customer,
                    'is_customer_email': sale.is_customer_email,
                    'buttons': sale.button_cost,
                    'fringers': sale.fringer_cost,
                    'tickets': sale.tickets.all(),
                    'total': sale.total_cost,
                    'type': 'Boxoffice' if sale.boxoffice else f'Venue ({sale.venue.name})' if sale.venue else 'Online',
                }
                for sale in sales
            ],
        }
        return render(request, 'festival/admin_sale_list.html', context)

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_sale_confirmation(request, sale_uuid):

    is_sent = False
    sale = get_object_or_404(Sale, uuid = sale_uuid)
    if sale.tickets:
        context = {
            'festival': request.festival,
            'tickets': sale.tickets.order_by('performance__date', 'performance__time', 'performance__show__name')
        }
        body = render_to_string('tickets/sale_email.txt', context)
        send_mail('Tickets for ' + request.festival.title, body, settings.DEFAULT_FROM_EMAIL, [sale.customer])
        is_sent = True

    return JsonResponse({
        'is_sent': is_sent
    })

