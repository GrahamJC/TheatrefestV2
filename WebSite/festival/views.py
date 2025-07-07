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

from program.models import Company, Show, ShowPerformance
from tickets.models import BoxOffice, Sale, TicketType, Ticket, FringerType, Fringer, PayAsYouWill, Bucket

from .forms import PasswordResetForm, EMailForm, AdminSaleListForm, AdminFestivalForm, AdminTicketTypeForm, AdminFringerTypeForm, AdminSaleForm, AdminSaleFringerForm, AdminSaleTicketForm, AdminSalePayAsYouWillForm, AdminBucketForm

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


@login_required
@require_POST
def admin_tickettype_copy(request):

    # Get ticket type to be copied
    copy_id = int(request.POST['copy_id'])
    if copy_id == 0:
        messages.warning(request, 'No type selected')
        return redirect('festival:admin_tickettype_list')
    type_to_copy = get_object_or_404(TicketType, id=copy_id)

    # If type name already exists in this festival add a numeric suffix
    copy_name = type_to_copy.name
    index = 0
    while TicketType.objects.filter(festival=request.festival, name=copy_name).exists():
        index += 1
        copy_name = f"{type_to_copy.name}_{index}"

    # Copy the type
    copy_type = TicketType(festival=request.festival, name=copy_name)
    copy_type.seqno = type_to_copy.seqno
    copy_type.price = type_to_copy.price
    copy_type.is_online = type_to_copy.is_online
    copy_type.is_boxoffice = type_to_copy.is_boxoffice
    copy_type.is_venue = type_to_copy.is_venue
    copy_type.rules = type_to_copy.rules
    copy_type.payment = type_to_copy.payment
    copy_type.save()
    messages.success(request, 'Type copied')
    return redirect('festival:admin_tickettype_update', slug=copy_type.uuid)


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


@login_required
@require_POST
def admin_fringertype_copy(request):

    # Get type to be copied
    copy_id = int(request.POST['copy_id'])
    if copy_id == 0:
        messages.warning(request, 'No type selected')
        return redirect('festival:admin_fringertype_list')
    type_to_copy = get_object_or_404(FringerType, id=copy_id)

    # If type name already exists in this festival add a numeric suffix
    copy_name = type_to_copy.name
    index = 0
    while FringerType.objects.filter(festival=request.festival, name=copy_name).exists():
        index += 1
        copy_name = f"{type_to_copy.name}_{index}"

    # Copy the type
    copy_type = FringerType(festival=request.festival, name=copy_name)
    copy_type.shows = type_to_copy.shows
    copy_type.price = type_to_copy.price
    copy_type.is_online = type_to_copy.is_online
    copy_type.rules = type_to_copy.rules
    copy_type.ticket_type = TicketType.objects.filter(festival=copy_type.festival, name=type_to_copy.ticket_type.name).first()
    copy_type.save()
    messages.success(request, 'Type copied')
    return redirect('festival:admin_fringertype_update', slug=copy_type.uuid)

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
                Button('add', 'Add Sale')
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
                sales = sales.filter(boxoffice__isnull=True, venue__isnull=True)
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

class AdminSaleCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Sale
    form_class = AdminSaleForm
    context_object_name = 'sale'
    template_name = 'festival/admin_sale.html'
    success_message = 'Sale added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Sale(festival=self.request.festival)
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('boxoffice', css_class='form-group col-md-6 mb-0'),
                Column('venue', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('user'),
            Field('customer'),
            Row(
                Column('amount', css_class='form-group col-md-6 mb-0'),
                Column('buttons', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('transaction_type', css_class='form-group col-md-4 mb-0'),
                Column('transaction_ID', css_class='form-group col-md-8 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('completed', css_class='form-group col-md-6 mb-0'),
                Column('cancelled', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('notes'),
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
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': 'Add' }
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update', args=[self.object.uuid])

class AdminSaleUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Sale
    form_class = AdminSaleForm
    slug_field = 'uuid'
    context_object_name = 'sale'
    template_name = 'festival/admin_sale.html'
    success_message = 'Sale updated'

    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)
    
    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            TabHolder(
                Tab ('Sale',
                    Row(
                        Column('boxoffice', css_class='form-group col-md-6 mb-0'),
                        Column('venue', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Field('user'),
                    Field('customer'),
                    Row(
                        Column('amount', css_class='form-group col-md-6 mb-0'),
                        Column('buttons', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('transaction_type', css_class='form-group col-md-4 mb-0'),
                        Column('transaction_ID', css_class='form-group col-md-8 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('completed', css_class='form-group col-md-6 mb-0'),
                        Column('cancelled', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Field('notes'),
                    FormActions(
                        Submit('save', 'Save'),
                        Button('delete', 'Delete'),
                        Button('cancel', 'Cancel'),
                    ),
                ),
                Tab('Fringers',
                    HTML('{% include \'festival/_admin_sale_fringers.html\' %}'),
                ),
                Tab('Tickets',
                    HTML('{% include \'festival/_admin_sale_tickets.html\' %}'),
                ),
                Tab('PAYW',
                    HTML('{% include \'festival/_admin_sale_payw.html\' %}'),
                ),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': 'Update' }
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update', args=[self.object.uuid])

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_sale_delete(request, slug):

    # Delete sale
    sale = get_object_or_404(Sale, uuid=slug)
    sale.delete()
    messages.success(request, 'Sale deleted')
    return redirect('festival:admin_sale_list')

class AdminSaleFringerCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Fringer
    form_class = AdminSaleFringerForm
    context_object_name = 'fringer'
    template_name = 'festival/admin_sale_fringer.html'
    success_message = 'Fringer added'

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, uuid=kwargs['sale_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Fringer(sale=self.sale)
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('type'),
            Field('user'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['sale'] = self.sale
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': f'Sale {self.sale.id}', 'url': reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'fringers']) },
            { 'text': 'Add Fringer' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'fringers'])

class AdminSaleFringerUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Fringer
    form_class = AdminSaleFringerForm
    slug_field = 'uuid'
    context_object_name = 'fringer'
    template_name = 'festival/admin_sale_fringer.html'
    success_message = 'Fringer updated'

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, uuid=kwargs['sale_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('type'),
            Field('user'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['sale'] = self.sale
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': f'Sale {self.sale.id}', 'url': reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'fringers']) },
            { 'text': 'Update Fringer' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'fringers'])

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_sale_fringer_delete(request, sale_uuid, slug):

    # Delete fringer from sale
    fringer = get_object_or_404(Fringer, uuid=slug)
    fringer.delete()
    messages.success(request, 'Fringer deleted')
    return redirect('festival:admin_sale_update_tab', sale_uuid, 'fringers')


class AdminSaleTicketCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Ticket
    form_class = AdminSaleTicketForm
    context_object_name = 'ticket'
    template_name = 'festival/admin_sale_ticket.html'
    success_message = 'Ticket added'

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, uuid=kwargs['sale_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Fringer(sale=self.sale)
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('performance'),
            Field('type'),
            Field('user'),
            Field('fringer'),
            Field('token_issued'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['sale'] = self.sale
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': f'Sale {self.sale.id}', 'url': reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'tickets']) },
            { 'text': 'Add Ticket' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'tickets'])


class AdminSaleTicketUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Ticket
    form_class = AdminSaleTicketForm
    slug_field = 'uuid'
    context_object_name = 'ticket'
    template_name = 'festival/admin_sale_ticket.html'
    success_message = 'Ticket updated'

    def dispatch(self, request, *args, **kwargs):
        self.sale = get_object_or_404(Sale, uuid=kwargs['sale_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('performance'),
            Field('type'),
            Field('user'),
            Field('fringer'),
            Field('token_issued'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['sale'] = self.sale
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Sales', 'url': reverse('festival:admin_sale_list') },
            { 'text': f'Sale {self.sale.id}', 'url': reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'tickets']) },
            { 'text': 'Update Ticket' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_sale_update_tab', args=[self.sale.uuid, 'tickets'])

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_sale_ticket_delete(request, sale_uuid, slug):

    # Delete ticket from sale
    ticket = get_object_or_404(Ticket, uuid=slug)
    ticket.delete()
    messages.success(request, 'Ticket deleted')
    return redirect('festival:admin_sale_update_tab', sale_uuid, 'tickets')


class AdminSalePAYWCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    pass

class AdminSalePAYWUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    pass

@require_GET
@login_required
@user_passes_test(lambda u: u.is_admin)
def admin_sale_payw_delete(request, sale_uuid, slug):
    pass


# Buckets
class AdminBucketList(LoginRequiredMixin, ListView):

    model = Bucket
    context_object_name = 'buckets'
    template_name = 'festival/admin_bucket_list.html'

    def get_queryset(self):
        return Bucket.objects.filter(company__festival=self.request.festival).order_by('company__name', 'show__name', 'performance__date', 'performance__time')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Buckets' },
        ]
        return context_data


class AdminBucketCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Bucket
    form_class = AdminBucketForm
    context_object_name = 'bucket'
    template_name = 'festival/admin_bucket.html'
    success_message = 'Bucket added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['company'].widget.attrs = { 'hx-get': reverse('festival:ajax_get_shows'), 'hx-target': '#id_show' }
        form.fields['show'].widget.attrs = { 'hx-get': reverse('festival:ajax_get_performances'), 'hx-target': '#id_performance' }
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('date'),
            Field('company'),
            Field('show'),
            Field('performance'),
            Row(
                Column('cash', css_class='col-sm-4'),
                Column('fringers', css_class='col-sm-4'),
                Column('cards', css_class='col-sm-4'),
                css_class='form-row'
            ),
            Field('audience'),
            Field('description'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_initial(self):
        return { 'date': datetime.now().date }
    
    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Buckets', 'url': reverse('festival:admin_bucket_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_bucket_list')

class AdminBucketUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Bucket
    form_class = AdminBucketForm
    slug_field = 'uuid'
    context_object_name = 'bucket'
    template_name = 'festival/admin_bucket.html'
    success_message = 'Bucket updated'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['company'].widget.attrs = { 'hx-get': reverse('festival:ajax_get_shows'), 'hx-target': '#id_show' }
        form.fields['show'].widget.attrs = { 'hx-get': reverse('festival:ajax_get_performances'), 'hx-target': '#id_performance' }
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('date'),
            Field('company'),
            Field('show'),
            Field('performance'),
            Row(
                Column('cash', css_class='col-sm-4'),
                Column('fringers', css_class='col-sm-4'),
                Column('cards', css_class='col-sm-4'),
                css_class='form-row'
            ),
            Field('audience'),
            Field('description'),
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
            { 'text': 'Buckets', 'url': reverse('festival:admin_bucket_list') },
            { 'text': 'Update' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('festival:admin_bucket_list')


@login_required
def admin_bucket_delete(request, slug):

    # Delete bucket
    bucket = get_object_or_404(Bucket, uuid=slug)
    bucket.delete()
    messages.success(request, 'Bucket deleted')
    return redirect('festival:admin_bucket_list')


# AJAX support
def ajax_get_shows(request):

    # Get company
    id = request.GET.get('company')
    company = get_object_or_404(Company, pk=id) if id else None

    # Return list of shows
    html = '<option value selected>---------</option>'
    if company:
        for show in company.shows.order_by('name'):
            html += f'<option value={show.id}>{show.name}</option>'
    return HttpResponse(html)

def ajax_get_performances(request):

    # Get show
    id = request.GET.get('show')
    show = get_object_or_404(Show, pk=id) if id  else None

    # Return list of shows
    html = '<option value selected>---------</option>'
    if show:
        for performance in show.performances.order_by('date', 'time'):
            html += f'<option value={performance.id}>{performance.date} at {performance.time}</option>'
    return HttpResponse(html)
