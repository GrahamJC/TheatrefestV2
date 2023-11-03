import os
import datetime
import arrow

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse, reverse_lazy
from django.views.generic import View, ListView, CreateView, UpdateView

from dal.autocomplete import Select2QuerySetView

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab

from core.models import User
from content.models import Document

from .models import Role, Location, Shift, Commitment, Volunteer
from .forms import (
    AdminRoleForm, AdminLocationForm, AdminShiftForm, AdminCommitmentForm,
    VolunteerAddForm, AdminVolunteerForm, VolunteerUserForm, VolunteerRolesForm,
    AdminShiftSearchForm,
)


# Logging
import logging
logger = logging.getLogger(__name__)


def render_shifts(request, volunteer):

    # Get days that have shifts defined
    shifts = Shift.objects.filter(location__festival=volunteer.user.festival, volunteer_can_accept=True, volunteer__isnull=True, role__in=volunteer.roles.all())
    if volunteer.is_dbs == False:
        shifts = shifts.filter(needs_dbs = False)
    days = []
    for day in shifts.order_by('date').values('date').distinct():
        days.append({
            'date': day['date'],
            'shifts': shifts.filter(date = day['date']).order_by('start_time')
        })
    context = {
        'my_shifts': volunteer.shifts.all(),
        'can_cancel': settings.VOLUNTEER_CANCEL_SHIFTS,
        'days': days,
    }

    # Get volunteer handbook URL
    handbook = Document.objects.filter(festival = request.festival, name='VolunteerHandbook').first()
    if handbook:
        context['handbook_url'] = handbook.get_absolute_url()

    # Render shifts
    return render(request, 'volunteers/shifts.html', context)

@login_required
def shift_list(request):

    # Get volunteer
    volunteer = request.user.volunteer

    # Render the page
    return render_shifts(request, volunteer)


@login_required
@transaction.atomic
def shift_accept(request, slug):

    # Get volunteer
    volunteer = request.user.volunteer

    # Get shift and assign to volunteer
    shift = get_object_or_404(Shift, uuid=slug)
    if not shift.volunteer:
        shift.volunteer = volunteer
        shift.save()
        messages.success(request, 'Shift accepted')
    else:
        messages.error(request, 'Shift has been accepted by another volunteer')

    # Render the page
    return render_shifts(request, volunteer)


@login_required
@transaction.atomic
def shift_cancel(request, slug):

    # Get volunteer
    volunteer = request.user.volunteer

    # Get shift and de-assign
    shift = get_object_or_404(Shift, uuid=slug)
    if shift.volunteer == volunteer:
        shift.volunteer = None
        shift.save()
        messages.success(request, 'Shift cancelled')
    else:
        messages.error(request, 'Shift is assigned to another volunteer')

    # Render the page
    return render_shifts(request, volunteer)


@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.festival,
    }
    return render(request, 'volunteers/admin_home.html', context)


class AdminRoleList(LoginRequiredMixin, ListView):

    model = Role
    context_object_name = 'roles'
    template_name = 'volunteers/admin_role_list.html'

    def get_queryset(self):
        return Role.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Roles' },
        ]
        return context_data


class AdminRoleCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Role
    form_class = AdminRoleForm
    context_object_name = 'role'
    template_name = 'volunteers/admin_role.html'
    success_message = 'Role added'
    success_url = reverse_lazy('volunteers:admin_role_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['information'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'description',
            'comps_per_shift',
            'information',
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Roles', 'url': reverse('volunteers:admin_role_list') },
            { 'text': 'Create' },
        ]
        return context_data


class AdminRoleUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Role
    form_class = AdminRoleForm
    slug_field = 'uuid'
    context_object_name = 'role'
    template_name = 'volunteers/admin_role.html'
    success_message = 'Role updated'
    success_url = reverse_lazy('volunteers:admin_role_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['information'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'description',
            'comps_per_shift',
            'information',
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Roles', 'url': reverse('volunteers:admin_role_list') },
            { 'text': 'Update' },
        ]
        return context_data
    

@login_required
def admin_role_delete(request, slug):

    # Delete role
    role = get_object_or_404(Role, uuid=slug)
    role.delete()
    messages.success(request, 'Role deleted')
    return redirect('volunteers:admin_role_list')


class AdminLocationList(LoginRequiredMixin, ListView):

    model = Location
    context_object_name = 'locations'
    template_name = 'volunteers/admin_location_list.html'

    def get_queryset(self):
        return Location.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Locations' },
        ]
        return context_data


class AdminLocationCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Location
    form_class = AdminLocationForm
    context_object_name = 'location'
    template_name = 'volunteers/admin_location.html'
    success_message = 'Location added'
    success_url = reverse_lazy('volunteers:admin_location_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['information'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'description',
            'information',
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Locations', 'url': reverse('volunteers:admin_location_list') },
            { 'text': 'Create' },
        ]
        return context_data


class AdminLocationUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Location
    form_class = AdminLocationForm
    slug_field = 'uuid'
    context_object_name = 'location'
    template_name = 'volunteers/admin_location.html'
    success_message = 'Location updated'
    success_url = reverse_lazy('volunteers:admin_location_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['information'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'description',
            'information',
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Locations', 'url': reverse('volunteers:admin_location_list') },
            { 'text': 'Update' },
        ]
        return context_data
    

@login_required
def admin_location_delete(request, slug):

    # Delete location
    location = get_object_or_404(Location, uuid=slug)
    location.delete()
    messages.success(request, 'Location deleted')
    return redirect('volunteers:admin_location_list')


class AdminCommitmentList(LoginRequiredMixin, ListView):

    model = Commitment
    context_object_name = 'commitments'
    template_name = 'volunteers/admin_commitment_list.html'

    def get_queryset(self):
        return Commitment.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Commitments', 'url': reverse('volunteers:admin_commitment_list') },
        ]
        return context_data

class AdminCommitmentCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Commitment
    form_class = AdminCommitmentForm
    context_object_name = 'commitment'
    template_name = 'volunteers/admin_commitment.html'
    success_message = 'Commitment added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('description'),
            Field('role'),
            Field('needs_dbs'),
            Field('volunteer_can_accept'),
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Commitments', 'url': reverse('volunteers:admin_commitment_list') },
            { 'text': 'Create' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('volunteers:admin_commitment_update', kwargs={'slug': self.object.uuid})


class AdminCommitmentUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Commitment
    form_class = AdminCommitmentForm
    slug_field = 'uuid'
    context_object_name = 'commitment'
    template_name = 'volunteers/admin_commitment.html'
    success_message = 'Commitment updated'

    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            TabHolder(
                Tab('General',
                    Field('description'),
                    Field('role'),
                    Field('needs_dbs'),
                    Field('volunteer_can_accept'),
                    Field('volunteer'),
                ),
                Tab('Shifts',
                    HTML('{% include \'volunteers/_admin_commitment_shifts.html\' %}')
                ),
                Tab('Notes',
                    Field('notes'),
                ),
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
        context_data['initial_tab'] = self.initial_tab
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Commitments', 'url': reverse('volunteers:admin_commitment_list') },
            { 'text': 'Update' },
        ]
        return context_data

    def form_valid(self, form):
        form.instance.update_shifts()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('volunteers:admin_commitment_update', kwargs={'slug': self.object.uuid})


@login_required
def admin_commitment_delete(request, slug):

    # Delete commitment
    group = get_object_or_404(Commitment, uuid=slug)
    group.delete()
    messages.success(request, 'Commitment deleted')
    return redirect('volunteers:admin_commitment_list')


class AdminCommitmentShiftCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Shift
    form_class = AdminShiftForm
    context_object_name = 'shift'
    template_name = 'volunteers/admin_commitment_shift.html'
    success_message = 'Commitment shift added'

    def dispatch(self, request, *args, **kwargs):
        self.commitment = get_object_or_404(Commitment, uuid=kwargs['commitment_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial['commitment'] = self.commitment
        initial['role'] = self.commitment.role
        initial['needs_dbs'] = self.commitment.needs_dbs
        initial['volunteer_can_accept'] = self.commitment.volunteer_can_accept
        initial['volunteer'] = self.commitment.volunteer
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('location'),
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
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
        context_data['commitment'] = self.commitment
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Commitments', 'url': reverse('volunteers:admin_commitment_list') },
            { 'text': 'Shifts', 'url': reverse('volunteers:admin_commitment_update_tab', kwargs={ 'slug': self.commitment.uuid, 'tab': 'shifts' }) },
            { 'text': 'Create' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('volunteers:admin_commitment_update_tab', args=[self.commitment.uuid, 'shifts'])


class AdminCommitmentShiftUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Shift
    form_class = AdminShiftForm
    slug_field = 'uuid'
    context_object_name = 'shift'
    template_name = 'volunteers/admin_commitment_shift.html'
    success_message = 'Commitment shift updated'

    def dispatch(self, request, *args, **kwargs):
        self.commitment = get_object_or_404(Commitment, uuid=kwargs['commitment_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs
        
    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('location'),
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
            ),
            Field('notes'),
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
        context_data['commitment'] = self.commitment
        context_data['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Commitments', 'url': reverse('volunteers:admin_commitment_list') },
            { 'text': 'Shifts', 'url': reverse('volunteers:admin_commitment_update_tab', kwargs={ 'slug': self.commitment.uuid, 'tab': 'shifts' }) },
            { 'text': 'Update' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('volunteers:admin_commitment_update_tab', args=[self.commitment.uuid, 'shifts'])
    

@login_required
def admin_commitment_shift_delete(request, commitment_uuid, slug):

    # Delete venue contact
    shift = get_object_or_404(Shift, uuid=slug)
    shift.delete()
    messages.success(request, 'Commitment shift deleted')
    return redirect('volunteers:admin_commitment_update_tab', commitment_uuid, 'shifts')


def create_admin_shift_search_form(festival, initial_data = None, post_data = None):

    form = AdminShiftSearchForm(festival, post_data, initial = initial_data)
    form.helper = FormHelper()
    form.helper.form_class = 'form-horizontal'
    form.helper.label_class = 'col-2'
    form.helper.field_class = 'col-10'
    form.helper.layout = Layout(
        Field('date'),
        Field('location'),
        Field('role'),
        Field('volunteer'),
        Field('status'),
        Field('include_commitments'),
        Submit('shift-search', 'Search', css_class='btn-primary'),
    )
    return form


def admin_get_shifts(festival, date_str, location_id_str, role_id_str, volunteer_id_str, status, include_commitments):

    # Get shifts meeting criteria
    shifts = Shift.objects.filter(location__festival = festival)
    date = datetime.datetime.strptime(date_str, '%Y%m%d')
    if date != datetime.datetime(2000, 1, 1):
        shifts = shifts.filter(date = date)
    location_id = int(location_id_str)
    if location_id != 0:
        shifts = shifts.filter(location_id = location_id)
    role_id = int(role_id_str)
    if role_id != 0:
        shifts = shifts.filter(role_id = role_id)
    volunteer_id = int(volunteer_id_str)
    if volunteer_id != 0:
        shifts = shifts.filter(volunteer_id = volunteer_id)
    if status == 'Accepted':
        shifts = shifts.filter(volunteer__isnull = False)
    elif status == 'NotAccepted':
        shifts = shifts.filter(volunteer__isnull = True)
    if not include_commitments:
        shifts = shifts.filter(commitment__isnull=True)
    shifts = list(shifts.order_by('date', 'start_time', 'location__description', 'role__description'))
    return shifts


class AdminShiftList(LoginRequiredMixin, View):

    template_name = 'volunteers/admin_shift_list.html'

    def get(self, request, *args, **kwargs):

        # Get search criteria from session
        #date_str = request.session.get('shift_search_date', '20000101')
        #location_id_str = request.session.get('shift_search_location_id', '0')
        #role_id_str = request.session.get('shift_search_role_id', '0')
        #volunteer_id_str = request.session.get('shift_search_volunteer_id', '0')
        #status = request.session.get('shift_search_status', 'All')
        #include_commitments = request.session.get('shift_search_include_commitments', False)

        # Create search form
        #initial_data = {
        #    'date': date_str,
        #    'location': location_id_str,
        #    'role': role_id_str,
        #    'volunteer': volunteer_id_str,
        #    'status': status,
        #    'include_commitments': include_commitments,
        #}
        #search_form = create_admin_shift_search_form(request.festival, initial_data = initial_data)
        search_form = create_admin_shift_search_form(request.festival)

        # Get shifts that meet criteria
        #shifts = admin_get_shifts(request.festival, date_str, location_id_str, role_id_str, volunteer_id_str, status, include_commitments)

        # Render page
        context = {
            'search_form': search_form,
            'shifts': None,
            'breadcrumbs': [
                { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
                { 'text': 'Shifts' },
            ]
        }
        return render(request, 'volunteers/admin_shift_list.html', context)

    def post(self, request, *args, **kwargs):

        # Handle search form
        search_form = create_admin_shift_search_form(request.festival, post_data = request.POST)
        shifts = None
        if search_form.is_valid():

            # Get shifts that meet selection criteria
            date_str = search_form.cleaned_data['date']
            location_id_str = search_form.cleaned_data['location']
            role_id_str = search_form.cleaned_data['role']
            volunteer_id_str = search_form.cleaned_data['volunteer']
            status = search_form.cleaned_data['status']
            include_commitments = search_form.cleaned_data['include_commitments']
            shifts = admin_get_shifts(request.festival, date_str, location_id_str, role_id_str, volunteer_id_str, status, include_commitments)

            # Save search criteria in session
            #request.session['shift_search_date'] = date_str
            #request.session['shift_search_location_id'] = location_id_str
            #request.session['shift_search_role_id'] = role_id_str
            #request.session['shift_search_volunteer_id'] = volunteer_id_str
            #request.session['shift_search_status'] = status
            #request.session['shift_search_include_commitments'] = include_commitments
        
        # Render page
        context = {
            'search_form': search_form,
            'shifts': shifts,
            'breadcrumbs': [
                { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
                { 'text': 'Shifts' },
            ]
        }
        return render(request, 'volunteers/admin_shift_list.html', context)


class AdminShiftCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Shift
    form_class = AdminShiftForm
    context_object_name = 'shift'
    template_name = 'volunteers/admin_shift.html'
    success_message = 'Shift added'
    success_url = reverse_lazy('volunteers:admin_shift_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('role'),
            Field('location'),
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
            ),
            Field('needs_dbs'),
            Field('volunteer_can_accept'),
            Field('volunteer'),
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Shifts', 'url': reverse('volunteers:admin_shift_list') },
            { 'text': 'Create' },
        ]
        return context_data


class AdminShiftUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Shift
    form_class = AdminShiftForm
    slug_field = 'uuid'
    context_object_name = 'shift'
    template_name = 'volunteers/admin_shift.html'
    success_message = 'Shift updated'
    success_url = reverse_lazy('volunteers:admin_shift_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('role'),
            Field('location'),
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
            ),
            Field('needs_dbs'),
            Field('volunteer_can_accept'),
            Field('volunteer'),
            Field('notes'),
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
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Shifts', 'url': reverse('volunteers:admin_shift_list') },
            { 'text': 'Update' },
        ]
        return context_data
    

@login_required
def admin_shift_delete(request, slug):

    # Delete shift
    shift = get_object_or_404(Shift, uuid=slug)
    shift.delete()
    messages.success(request, 'Shift deleted')
    return redirect('volunteers:admin_shift_list')


class AdminVolunteerAutoComplete(Select2QuerySetView):

    def get_queryset(self):
        qs = User.objects.filter(festival = self.request.festival, is_volunteer=False)
        if self.q:
            qs = qs.filter(email__istartswith = self.q)
        return qs

    def get_result_label(self, item):
        return item.email


@login_required
def admin_volunteers(request):

    # Check request type
    if request.method == 'GET':

        # Create form
        form = VolunteerAddForm(request.festival)

    else:

        # Create form, bind it to POST data and valdate
        form = VolunteerAddForm(request.festival, data=request.POST)
        if form.is_valid():

            # Add user as volunteer and edit details
            user = form.cleaned_data['user']
            user.is_volunteer = True
            user.save()
            volunteer = Volunteer(user = user)
            volunteer.save()
            messages.success(request, 'Volunteer added')
            return redirect('volunteers:admin_volunteer_update', slug=volunteer.uuid)

    # Create context and render page
    context = {
        'breadcrumbs': [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Volunteers' },
        ],
        'form': form,
    }
    return render(request, 'volunteers/admin_volunteers.html', context)


class AdminVolunteerUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Volunteer
    form_class = AdminVolunteerForm
    context_object_name = 'volunteer'
    slug_field = 'uuid'
    template_name = 'volunteers/admin_volunteer.html'
    success_message = 'Volunteer updated'
    success_url = reverse_lazy('volunteers:admin_volunteers')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'festival': self.request.festival,
            'instance': { 'user': self.object.user, 'volunteer': self.object },
        })
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'user-email',
            'user-first_name',
            'user-last_name',
            'user-is_boxoffice',
            'user-is_venue',
            'volunteer-is_dbs',
            'volunteer-roles',
            FormActions(
                Submit('save', 'Save'),
                Button('remove', 'Remove'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['festival'] = self.request.festival
        context['breadcrumbs'] = [
            { 'text': 'Volunteer Admin', 'url': reverse('volunteers:admin_home') },
            { 'text': 'Volunteers', 'url': reverse('volunteers:admin_volunteers') },
            { 'text': 'Update' },
        ]
        return context


@login_required
def admin_volunteer_remove(request, slug):

    # Remove user as volunteer and return to list
    volunteer = get_object_or_404(Volunteer, uuid=slug)
    volunteer.user.is_volunteer = False;
    volunteer.user.save();
    volunteer.delete()
    messages.success(request, 'Volunteer removed')
    return redirect('volunteers:admin_volunteers')
