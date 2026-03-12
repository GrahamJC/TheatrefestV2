# pylint: disable=missing-docstring
from datetime import datetime
from dateutil.parser import parse

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from .models import Festival

class FestivalMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Check session to see if a festival has been selected otherwise default
        # to the live festival
        festival = None
        try:
            festival_id = request.session.get('festival_id', None)
            if festival_id:
                festival = Festival.objects.get(id=festival_id)
            if not festival:
                festival = Festival.objects.filter(is_live=True).order_by('name').last()
        except Festival.DoesNotExist:
            festival = None
        if not festival:
            return redirect('/static/maintenance.html')
        request.festival = festival

        # Add curret date/time to request
        date = parse(request.session.get('date', str(timezone.now().date()))).date()
        time = parse(request.session.get('time', str(timezone.now().time()))).time()
        request.now = datetime.combine(date, time)

        # Process request
        response = self.get_response(request)

        # Return response
        return response
