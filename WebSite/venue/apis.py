import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import View
from django.http import HttpResponse, JsonResponse

import arrow

from program.models import Show, ShowPerformance
from tickets.models import BoxOffice


def reports_show_options(request):

    box_office = BoxOffice.objects.get(pk = request.session.get('box_office_id', None))
    html = '<option value="0">-- Select show --</option>'
    for show in Show.objects.filter(venue__is_ticketed = True, venue__box_office = box_office):
        html += f'<option value="{show.id}">{show.name}</option>'
    return HttpResponse(html)


def reports_performance_options(request, show_id):

    show = get_object_or_404(Show, pk = show_id)
    html = '<option value="0">-- Select performance --</option>'
    for performance in show.performances.order_by('date', 'time'):
        dt = arrow.get(datetime.datetime.combine(performance.date, performance.time))
        html += f'<option value="{performance.id}">{dt:ddd, MMM D} at {dt:h:mm a} ({performance.tickets_available} tickets available)</option>'
    return HttpResponse(html)


