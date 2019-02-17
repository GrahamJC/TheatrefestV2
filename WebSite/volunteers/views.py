import os
import arrow

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse_lazy

from dal.autocomplete import Select2QuerySetView

from core.models import User

from .models import Role, Location, Volunteer, Shift
from .forms import RoleForm, LocationForm, VolunteerAddForm, VolunteerUserForm, VolunteerRolesForm, SelectShiftsForm, ShiftForm


@login_required
def shifts(request):

    # Render the page
    context = {
        'my_shifts': request.user.volunteer.shifts.all(),
        'available_shifts': Shift.objects.filter(location__festival=request.festival)
    }
    return render(request, 'volunteers/shifts.html', context)


@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.site.info.festival,
    }
    return render(request, 'volunteers/admin_home.html', context)


@login_required
def admin_roles(request):

    # Render the page
    return render(request, 'volunteers/admin_roles.html')


@login_required
def admin_role_create(request):

    # Check request type
    if request.method == 'GET':

        # Create form
        form = RoleForm(initial={'festival': request.festival})

    else:

        # Create form, bind it to POST data and valdate
        role = None
        form = RoleForm(data=request.POST)
        if form.is_valid():

            # Save and return to list
            role = form.save()
            messages.success(request, 'Role added')
            return redirect('volunteers:admin_roles')

    # Create context and render page
    context = {
        'form': form,
    }
    return render(request, 'volunteers/admin_role_create.html', context)


@login_required
def admin_role_update(request, role_uuid):

    # Get role
    role = get_object_or_404(Role, uuid=role_uuid)

    # Check request type
    if request.method == 'GET':

        # Create form
        form = RoleForm(instance=role)

    else:

        # Create form, bind it to POST data and valdate
        form = RoleForm(instance=role, data=request.POST)
        if form.is_valid():

            # Save changes and return to list
            form.save()
            messages.success(request, 'Role updated')
            return redirect('volunteers:admin_roles')

    # Create context and render page
    context = {
        'role': role,
        'form': form,
    }
    return render(request, 'volunteers/admin_role_update.html', context)


@login_required
def admin_role_delete(request, role_uuid):

    # Delete role and return to list
    role = get_object_or_404(Role, uuid=role_uuid)
    role.delete()
    messages.success(request, 'Role deleted')
    return redirect('volunteers:admin_roles')


@login_required
def admin_locations(request):

    # Render the page
    return render(request, 'volunteers/admin_locations.html')


@login_required
def admin_location_create(request):

    # Check request type
    if request.method == 'GET':

        # Create form
        form = LocationForm(initial={'festival': request.festival})

    else:

        # Create form, bind it to POST data and valdate
        location = None
        form = LocationForm(data=request.POST)
        if form.is_valid():

            # Save and return to list
            location = form.save()
            messages.success(request, 'Location added')
            return redirect('volunteers:admin_locations')

    # Create context and render page
    context = {
        'form': form,
    }
    return render(request, 'volunteers/admin_location_create.html', context)


@login_required
def admin_location_update(request, location_uuid):

    # Get location
    location = get_object_or_404(Location, uuid=location_uuid)

    # Check request type
    if request.method == 'GET':

        # Create form
        form = LocationForm(instance=location)

    else:

        # Create form, bind it to POST data and valdate
        form = LocationForm(instance=location, data=request.POST)
        if form.is_valid():

            # Save changes and return to list
            form.save()
            messages.success(request, 'Location updated')
            return redirect('volunteers:admin_locations')

    # Create context and render page
    context = {
        'location': location,
        'form': form,
    }
    return render(request, 'volunteers/admin_location_update.html', context)


@login_required
def admin_location_delete(request, location_uuid):

    # Delete location and return to list
    location = get_object_or_404(Location, uuid=location_uuid)
    location.delete()
    messages.success(request, 'Location deleted')
    return redirect('volunteers:admin_locations')


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
            return redirect('volunteers:admin_volunteer_update', user_uuid=user.uuid)

    # Create context and render page
    context = {
        'form': form,
    }
    return render(request, 'volunteers/admin_volunteers.html', context)


@login_required
def admin_volunteer_update(request, user_uuid):

    # Get user
    user = get_object_or_404(User, uuid=user_uuid)

    # Check request type
    if request.method == 'GET':

        # Create forms
        user_form = VolunteerUserForm(instance=user)
        roles_form = VolunteerRolesForm(instance=user.volunteer)

    else:

        # Create form, bind to POST data and valdate
        user_form = VolunteerUserForm(instance=user, data=request.POST)
        roles_form = VolunteerRolesForm(instance=user.volunteer, data=request.POST)
        if user_form.is_valid() and roles_form.is_valid():

            # Save changes and return to form
            user_form.save()
            roles_form.save()
            messages.success(request, 'Volunteer updated')
            return redirect('volunteers:admin_volunteers')

    # Create context and render page
    context = {
        'volunteer': user.volunteer,
        'user_form': user_form,
        'roles_form': roles_form,
    }
    return render(request, 'volunteers/admin_volunteer_update.html', context)


@login_required
def admin_volunteer_remove(request, user_uuid):

    # Remove user as volunteer and return to list
    user = get_object_or_404(User, uuid=user_uuid)
    user.volunteer.delete()
    user.is_volunteer = False;
    user.save();
    messages.success(request, 'Volunteer removed')
    return redirect('volunteers:admin_volunteers')


@login_required
def admin_shifts(request, location_uuid=None, date=None):

    # Check request type
    if request.method == 'GET':

        # Create form to select location and date
        location = get_object_or_404(Location, uuid=location_uuid) if location_uuid else None
        date = arrow.get(date).date() if date else arrow.now().date()
        form = SelectShiftsForm(request.festival, initial={'location': location, 'date': date})

    else:

        # Create form, bind POST data and valdate
        form = SelectShiftsForm(request.festival, data=request.POST)
        if form.is_valid():

            # Get selected shifts
            location = form.cleaned_data['location']
            date = form.cleaned_data['date']

    # Get selected shifts
    shifts = []
    if request.POST or location or date:
        shifts = Shift.objects.all()
        if location:
            shifts = shifts.filter(location=location)
        if date:
            shifts = shifts.filter(date=date)
        shifts = shifts.order_by('location__description', 'start_time', 'role__description')
        if shifts.count() == 0:
            messages.info(request, 'No shifts found for the selected location and date.')

    # Render the page
    context = {
        'location': location,
        'date': date,
        'shifts': shifts,
        'form': form,
    }
    return render(request, 'volunteers/admin_shifts.html', context)


@login_required
def admin_shift_create(request, location_uuid=None, date=None):

    # Get parameters
    location = get_object_or_404(Location, uuid=location_uuid) if location_uuid else None
    date = arrow.get(date).date() if date else None

    # Check request type
    if request.method == 'GET':

        # Create form
        form = ShiftForm(request.festival, initial={'location': location, 'date': date})

    else:

        # Create form, bind it to POST data and valdate
        form = ShiftForm(request.festival, data=request.POST)
        if form.is_valid():

            # Save and return to list
            shift = form.save()
            messages.success(request, 'Shift added')
            return redirect('volunteers:admin_shifts', location_uuid=shift.location.uuid, date=shift.date)

    # Create context and render page
    context = {
        'location': location,
        'date': date,
        'form': form,
    }
    return render(request, 'volunteers/admin_shift_create.html', context)


@login_required
def admin_shift_update(request, shift_uuid):

    # Get shift
    shift = get_object_or_404(Shift, uuid=shift_uuid)

    # Check request type
    if request.method == 'GET':

        # Create form
        form = ShiftForm(request.festival, instance=shift)

    else:

        # Create form, bind it to POST data and valdate
        form = ShiftForm(request.festival, instance=shift, data=request.POST)
        if form.is_valid():

            # Save and return to list
            form.save()
            messages.success(request, 'Shift updated')
            return redirect('volunteers:admin_shifts', location_uuid=shift.location.uuid, date=shift.date)

    # Create context and render page
    context = {
        'shift': shift,
        'form': form,
    }
    return render(request, 'volunteers/admin_shift_update.html', context)


@login_required
def admin_shift_delete(request, shift_uuid):

    # Delete shift and return to list
    shift = get_object_or_404(Shift, uuid=shift_uuid)
    location = shift.location
    date = shift.date
    shift.delete()
    messages.success(request, 'Shift deleted')
    return redirect('volunteers:admin_shifts', location_uuid=location.uuid, date=date)
