import os

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.views.decorators.http import require_GET, require_POST
from django.core.mail import send_mail

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from core.models import Festival, User

from tickets.models import BoxOffice, Sale, TicketType, FringerType

from .forms import PasswordResetForm, EMailForm, AdminSaleListForm, AdminFestivalForm, AdminTicketTypeForm, AdminFringerTypeForm

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


@login_required
@user_passes_test(lambda u: u.is_venue or u.is_boxoffice)
def switch(request, name=None):

    # Get requested festival and matching user in that festival
    if name:
        festival = get_object_or_404(Festival, name__iexact=name)
    else:
        festival = get_object_or_404(Festival, name__iexact=settings.DEFAULT_FESTIVAL)
    logger.info(f"Switch session to {festival.name}.")
    user = get_object_or_404(User, festival_id=festival.id, email=request.user.email)

    # Logout as current user out and login as matching user in new festival
    logout(request)
    login(request, user)

    # Save new festival in session and redirect to home page
    if festival:
        request.session['festival_id'] = festival.id
    return redirect('home')


@user_passes_test(lambda u: u.is_admin)
@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.festival,
    }
    return render(request, 'festival/admin.html', context)


class AdminFestival(LoginRequiredMixin, View):

    def _get_form(self, festival, post_data = None):
        form = AdminFestivalForm(instance=festival, data=post_data)
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
                { 'text': 'Festival' },
            ],
            'form': form,
        }
        return render(request, 'festival/admin_festival.html', context)

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
            festival.volunteer_comps = form.cleaned_data['volunteer_comps']
            festival.save()

        # Return to menu
        messages.success(request, 'Festival updated')
        return redirect('festival:admin')

class AdminTicketTypeList(LoginRequiredMixin, ListView):

    model = TicketType
    context_object_name = 'tickettypes'
    template_name = 'festival/admin_tickettype_list.html'

    def get_queryset(self):
        return TicketType.objects.filter(festival=self.request.festival).order_by('seqno')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Ticket Types' },
        ]
        return context_data

class AdminTicketTypeCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = TicketType
    form_class = AdminTicketTypeForm
    context_object_name = 'tickettype'
    template_name = 'festival/admin_tickettype.html'
    success_message = 'Ticket type added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('seqno', css_class='col-sm-2'),
                Column('name', css_class='col-sm-10'),
                css_class='form-row',
            ),
            Row(
                Column('is_online', css_class='col-sm-4'),
                Column('is_boxoffice', css_class='col-sm-4'),
                Column('is_venue', css_class='col-sm-4'),
                css_class='form-row',
            ),
            Row(
                Column('price', css_class='col-sm-6'),
                Column('payment', css_class='col-sm-6'),
                css_class='form-row',
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Ticket Types', 'url': reverse('festival:admin_tickettype_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_tickettype_list')

class AdminTicketTypeUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = TicketType
    form_class = AdminTicketTypeForm
    slug_field = 'uuid'
    context_object_name = 'tickettype'
    template_name = 'festival/admin_tickettype.html'
    success_message = 'Ticket type updated'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('seqno', css_class='col-sm-2'),
                Column('name', css_class='col-sm-10'),
                css_class='form-row',
            ),
            Row(
                Column('is_online', css_class='col-sm-4'),
                Column('is_boxoffice', css_class='col-sm-4'),
                Column('is_venue', css_class='col-sm-4'),
                css_class='form-row',
            ),
            Row(
                Column('price', css_class='col-sm-6'),
                Column('payment', css_class='col-sm-6'),
                css_class='form-row',
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Ticket Types', 'url': reverse('festival:admin_tickettype_list') },
            { 'text': 'Update' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_tickettype_list')


@login_required
def admin_tickettype_delete(request, slug):

    # Delete ticket type
    tickettype = get_object_or_404(TicketType, uuid=slug)
    tickettype.delete()
    messages.success(request, 'Ticket type deleted')
    return redirect('festival:admin_tickettype_list')

class AdminFringerTypeList(LoginRequiredMixin, ListView):

    model = FringerType
    context_object_name = 'fringertypes'
    template_name = 'festival/admin_fringertype_list.html'

    def get_queryset(self):
        return FringerType.objects.filter(festival=self.request.festival).order_by('is_online', 'name')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Fringer Types' },
        ]
        return context_data

class AdminFringerTypeCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = FringerType
    form_class = AdminFringerTypeForm
    context_object_name = 'fringertype'
    template_name = 'festival/admin_fringertype.html'
    success_message = 'Fringer type added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('is_online'),
            Row(
                Column('price', css_class='col-sm-6'),
                Column('shows', css_class='col-sm-6'),
                css_class='form-row',
            ),
            Field('ticket_type'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Fringer Types', 'url': reverse('festival:admin_fringertype_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_fringertype_list')

class AdminFringerTypeUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = FringerType
    form_class = AdminFringerTypeForm
    slug_field = 'uuid'
    context_object_name = 'fringertype'
    template_name = 'festival/admin_fringertype.html'
    success_message = 'Fringer type updated'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('is_online'),
            Row(
                Column('price', css_class='col-sm-6'),
                Column('shows', css_class='col-sm-6'),
                css_class='form-row',
            ),
            Field('ticket_type'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Fringer Types', 'url': reverse('festival:admin_fringertype_list') },
            { 'text': 'Update' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_fringertype_list')

@login_required
def admin_fringertype_delete(request, slug):

    # Delete fringer type
    fringertype = get_object_or_404(FringerType, uuid=slug)
    fringertype.delete()
    messages.success(request, 'Fringer type deleted')
    return redirect('festival:admin_fringertype_list')


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
            sales = sales.order_by('id')[:50]
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
                    'type': sale.transaction_type_description(),
                    'customer': sale.customer,
                    'is_customer_email': sale.is_customer_email,
                    'buttons': sale.button_cost,
                    'fringers': sale.fringer_cost,
                    'tickets': sale.tickets.all(),
                    'total': sale.total_cost,
                    'location': 'Boxoffice' if sale.boxoffice else f'Venue ({sale.venue.name})' if sale.venue else 'Online',
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

