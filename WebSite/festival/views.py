import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Festival


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

    # Redirect to home page
    return redirect('home')


@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.site.info.festival,
    }
    return render(request, 'festival/admin.html', context)
