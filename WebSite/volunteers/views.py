import os
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
from django.views.generic import ListView, CreateView, UpdateView

from dal.autocomplete import Select2QuerySetView

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab

from core.models import User

from .models import Role, Location, Shift, Volunteer
from .forms import (
    AdminRoleForm, AdminLocationForm, AdminShiftForm,
    VolunteerAddForm, VolunteerUserForm, VolunteerRolesForm, SelectShiftsForm,
)


def get_shift_list_context(volunteer):
    return {
        'my_shifts': volunteer.shifts.all(),
        'available_shifts': Shift.objects.filter(location__festival=volunteer.user.festival, volunteer__isnull=True, role__in=volunteer.roles.all())
    }

@login_required
def shift_list(request):

    # Get volunteer
    volunteer = request.user.volunteer

    # Render the page
    return render(request, 'volunteers/shifts.html', get_shift_list_context(volunteer))


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
    return render(request, 'volunteers/shifts.html', get_shift_list_context(volunteer))


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
    return render(request, 'volunteers/shifts.html', get_shift_list_context(volunteer))


@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.site.info.festival,
    }
    return render(request, 'volunteers/admin_home.html', context)


class AdminRoleList(LoginRequiredMixin, ListView):

    model = Role
    context_object_name = 'roles'
    template_name = 'volunteers/admin_role_list.html'

    def get_queryset(self):
        return Role.objects.filter(festival=self.request.festival)


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
            'information',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


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
            'information',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form
    

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
    

@login_required
def admin_location_delete(request, slug):

    # Delete location
    location = get_object_or_404(Location, uuid=slug)
    location.delete()
    messages.success(request, 'Location deleted')
    return redirect('volunteers:admin_location_list')


class AdminShiftList(LoginRequiredMixin, ListView):

    model = Shift
    context_object_name = 'shifts'
    template_name = 'volunteers/admin_shift_list.html'

    def get_queryset(self):
        queryset = Shift.objects.filter(location__festival=self.request.festival)
        if 'location_uuid' in self.request.GET:
            queryset = queryset.filter(uuid=self.request.GET['location_uuid'])
        if 'date' in self.request.GET:
            queryset = queryset.filter(UpdateView=self.request.GET['date'])
        return queryset


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

    def get_initial(self, **kwargs):
        initial = super().get_initial(**kwargs)
        if 'location_uuid' in self.request.GET:
            initial['location'] = get_object_or_404(Location, uuid=self.request.GET['location_uuid'])
        if 'date' in self.request.GET:
            initial['date'] = self.request.GET['date']
        return initial

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'role',
            'location',
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
            ),
            'volunteer',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


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
            'role',
            'location',
            Row(
                Column('date', css_class='col-sm-4'),
                Column('start_time', css_class='col-sm-4'),
                Column('end_time', css_class='col-sm-4'),
                css_class='form-row',
            ),
            'volunteer',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form
    

@login_required
def admin_shift_delete(request, slug):

    # Delete shift
    shift = get_object_or_404(Shift, uuid=slug)
    shift.delete()
    messages.success(request, 'Shift deleted')
    return redirect('volunteers:admin_shift_list')


class VolunteerAutoComplete(Select2QuerySetView):

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
        'form': form,
    }
    return render(request, 'volunteers/admin_volunteers.html', context)


@login_required
def admin_volunteer_update(request, slug):

    # Get volunteer
    volunteer = get_object_or_404(Volunteer, uuid=slug)

    # Check request type
    if request.method == 'GET':

        # Create forms
        user_form = VolunteerUserForm(instance=volunteer.user)
        roles_form = VolunteerRolesForm(instance=volunteer)

    else:

        # Create form, bind to POST data and valdate
        user_form = VolunteerUserForm(instance=volunteer.user, data=request.POST)
        roles_form = VolunteerRolesForm(instance=volunteer, data=request.POST)
        if user_form.is_valid() and roles_form.is_valid():

            # Save changes and return to form
            user_form.save()
            roles_form.save()
            messages.success(request, 'Volunteer updated')
            return redirect('volunteers:admin_volunteers')

    # Create context and render page
    context = {
        'volunteer': volunteer,
        'user_form': user_form,
        'roles_form': roles_form,
    }
    return render(request, 'volunteers/admin_volunteer_update.html', context)


@login_required
def admin_volunteer_remove(request, slug):

    # Remove user as volunteer and return to list
    volunteer = get_object_or_404(Volunteer, uuid=slug)
    volunteer.user.is_volunteer = False;
    volunteer.user.save();
    volunteer.delete()
    messages.success(request, 'Volunteer removed')
    return redirect('volunteers:admin_volunteers')
