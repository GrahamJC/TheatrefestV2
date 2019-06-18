import os
import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.views import View
from django.views.decorators.http import require_http_methods, require_GET
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse

import arrow

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import cm
from reportlab.lib import colors

from volunteers.models import Volunteer, Shift

@require_GET
@login_required
@user_passes_test(lambda u: u.is_volunteer) 
def shifts_pdf(request, volunteer_uuid = None):

    # Get volunteer
    if volunteer_uuid:
        volunteer = get_object_or_404(Volunteer, uuid = volunteer_uuid)
    else:
        volunteer = request.user.volunteer
    assert volunteer

    # Fetch data
    shifts = Shift.objects.filter(volunteer = volunteer).order_by('date', 'start_time')

    # Render PDF
    response = HttpResponse(content_type = 'application/pdf')
    doc = SimpleDocTemplate(
        response,
        pagesize = portrait(A4),
        leftMargin = 1.5*cm,
        rightMargin = 1.5*cm,
        topMargin = 1.5*cm,
        bottomMargin = 1.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Festival banner
    if request.festival.banner:
        banner = Image(request.festival.banner.get_absolute_path(), width = 18*cm, height = 4*cm)
        banner.hAlign = 'CENTER'
        story.append(banner)
        story.append(Spacer(1, 1*cm))

    # Header
    table_data = []
    table_styles = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]
    table_data.append((
        'Date',
        'Location',
        'Start',
        'End',
        'Role',
    ))
    table_styles.append(('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey))
    table_styles.append(('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkgrey))
    for shift in shifts:
        table_data.append((
            f"{shift.date:%a, %b %d}",
            shift.location.description,
            f"{shift.start_time:%I:%M%p}",
            f"{shift.end_time:%I:%M%p}",
            shift.role.description,
        ))

    # Add to story
    table = Table(
        table_data,
        colWidths = (3*cm, 4*cm, 3*cm, 3*cm, 5*cm),
        style = table_styles,
    )
    story.append(table)
    story.append(Spacer(1, 0.5*cm))

    # Render PDF document and return it
    doc.build(story)
    return response
