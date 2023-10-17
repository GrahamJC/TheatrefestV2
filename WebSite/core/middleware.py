# pylint: disable=missing-docstring
from datetime import datetime
from dateutil.parser import parse

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Festival

class FestivalMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Add festival to request
        festival_id = request.session.get('festival_id', None)
        if festival_id:
            request.festival = get_object_or_404(Festival, pk=festival_id)
        else:
            request.festival = get_object_or_404(Festival, name=settings.DEFAULT_FESTIVAL)
        
        # Add curret date/time to request
        date = parse(request.session.get('date', str(timezone.now().date()))).date()
        time = parse(request.session.get('time', str(timezone.now().time()))).time()
        request.now = datetime.combine(date, time)

        # Process request
        response = self.get_response(request)

        # Return response
        return response
