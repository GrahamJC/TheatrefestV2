import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def admin(request):

    # Render the page
    context = {
        'festival': request.site.info.festival,
    }
    return render(request, 'festival/admin.html', context)
