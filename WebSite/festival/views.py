import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST

from core.models import Festival, User

from .forms import PasswordResetForm

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
    return redirect('https://archive.theatrefest.co.uk/archive/index.htm')


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
        'breadcrumbs': [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Users' },
        ],
        'user_list': User.objects.filter(festival = request.festival).order_by('email')
    }
    return render(request, 'festival/admin_user_list.html', context)
