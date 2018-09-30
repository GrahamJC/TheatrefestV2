import os

from django.db.models.functions import Lower
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse
from django.views import View

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors

from core.models import Festival
from .models import Show, ShowPerformance, Venue
from .forms import SearchForm

def shows(request, festival_uuid=None):

    # Get festival
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.site.info.festival

    # Create the search form
    search = SearchForm(festival=festival, data=request.GET)

    # Create context
    context = {
        'festival': festival,
        'search': search,
    }

    # If valid add search results to context
    if search.is_valid():
        shows = Show.objects.filter(festival=festival).select_related('company', 'venue').prefetch_related('genres', 'performances')
        if search.cleaned_data['days']:
            shows = shows.filter(performances__date__in = search.cleaned_data['days'])
        if search.cleaned_data['venues']:
            if '0' in search.cleaned_data['venues']:
                shows = shows.filter(Q(venue_id__in = search.cleaned_data['venues']) | Q(venue__is_ticketed = False))
            else:
                shows = shows.filter(venue_id__in = search.cleaned_data['venues'])
        if search.cleaned_data['genres']:
            shows = shows.filter(genres__id__in = search.cleaned_data['genres'] )
        shows = shows.order_by(Lower('name'))
        results = []
        for show in shows.distinct():
            results.append(show)
        context['results'] = results

    # Render search results
    return render(request, 'program/shows.html', context)


def show(request, show_uuid):

    # Get show
    show = get_object_or_404(Show, uuid=show_uuid)

    # Check for HTML description
    html = None
    if show.detail:
        context = { 'show': show }
        media_url = getattr(settings, 'MEDIA_URL', '/')
        for image in show.images.all():
            context[f"image_{image.name}_url"] = os.path.join(media_url, image.image.url)
        template = Template(show.detail)
        html = template.render(Context(context))

    # Render show details
    context ={
        'show': show,
        'html': html,
    }
    return render(request, 'program/show.html', context)


def _add_non_scheduled_performances(festival, day):
    performances = []
    for performance in ShowPerformance.objects.filter(show__festival=festival, show__venue__is_scheduled=False, date = day['date']).order_by('time').values('time', 'show__uuid', 'show__name', 'show__is_cancelled'):
        performances.append(
            {
                'show_uuid': performance['show__uuid'],
                'show_name': performance['show__name'],
                'time': performance['time'],
                'is_cancelled': performance['show__is_cancelled'],
            }
        )
    day['venues'].append(
        {
            'name': 'Other (alt spaces)',
            'color': '',
            'performances': performances,
        }
    )

def schedule(request, festival_uuid=None):

    # Get festival
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.site.info.festival

    # Build the schedule
    days = []
    day = None
    for performance in ShowPerformance.objects.filter(show__festival=festival, show__venue__is_scheduled=True) \
                                              .order_by('date', 'show__venue__map_index', 'show__venue__name', 'time') \
                                              .values('date', 'show__venue__name', 'show__venue__color', 'time', 'show__uuid', 'show__name', 'show__is_cancelled'):
            
        # If the date has changed start a new day
        if day and performance['date'] != day['date']:
            if venue:
                day['venues'].append(venue)
                venue = None
            _add_non_scheduled_performances(festival, day)
            days.append(day)
            day = None
        if not day:
            day = {
                'date': performance['date'],
                'venues': [],
            }
            venue = None

        # If the venue has changed add it to the page and start a new one
        if venue and performance['show__venue__name'] != venue['name']:
            day['venues'].append(venue)
            venue = None
        if not venue:
            venue = {
                'name': performance['show__venue__name'],
                'color': performance['show__venue__color'],
                'performances': [],
            }

        # Add performance to venue
        venue['performances'].append(
            {
                'show_uuid': performance['show__uuid'],
                'show_name': performance['show__name'],
                'time': performance['time'],
                'is_cancelled': performance['show__is_cancelled'],
            }
        )

    # Add final day and venue
    if day:
        if venue:
            day['venues'].append(venue)
        _add_non_scheduled_performances(festival, day)
        days.append(day)

    # Render schedule
    context = {
        'days': days,
    }
    return render(request, 'program/schedule.html', context)



def schedule_pdf(request, festival_uuid=None):

    # Get festival
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.site.info.festival

    # Create a Platypus story
    response = HttpResponse(content_type = 'application/pdf')
    response["Content-Disposition"] = 'inline; filename="TheatrefestSchedule.pdf"'
    doc = SimpleDocTemplate(
        response,
        pagesize = landscape(A4),
        leftMargin = 0.5*cm,
        rightMargin = 0.5*cm,
        topMargin = 0.5*cm,
        bottomMargin = 0.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Table data and styles
    table_data = []
    table_styles = []

    # Paragraph styles
    venue_style = ParagraphStyle(
        name = 'Venue',
        align = TA_CENTER,
        fontSize = 10,
        textColor = colors.white,
    )
    day_style = ParagraphStyle(
        name = 'Day',
        fontSize = 10,
    )
    time_style = ParagraphStyle(
        name = 'Time',
        fontSize = 8,
        leading = 8,
        textColor = colors.indianred,
    )
    show_style = ParagraphStyle(
        name = 'Show',
        fontSize = 8,
        leading = 8,
        textColor = '#1a7cf3',
    )

    # Venues
    venues = Venue.objects.filter(festival=festival, is_scheduled=True).order_by('map_index')
    venues_data = []
    for v in venues:
        venues_data.append(Paragraph(f'<para align="center"><b>{v.name}</b></para>', venue_style))
        venues_data.append('')
    table_data.append(venues_data)
    for i, v in enumerate(venues):
        table_styles.append(('SPAN', (2*i, 0), (2*i + 1, 0)))
        table_styles.append(('BACKGROUND', (2*i, 0), (2*i + 1, 0), v.color ))

    # Days
    days = ShowPerformance.objects.filter(show__festival=festival, show__is_cancelled=False, show__venue__is_scheduled=True).order_by('date').values('date').distinct()
    day_color = ('#fbe4d5', '#fff2cc', '#e2efd9', '#deeaf6')
    for index, day in enumerate(days):

        # Add a row for the day
        first_row = len(table_data)
        table_data.append([Paragraph(f"{day['date']:%A %d}", day_style)] + ['' for i in range(2*len(venues) - 1)])
        table_styles.append(('SPAN', (0, first_row), (-1, first_row)))

        # Get performances for each venue
        venue_performances = [ ShowPerformance.objects.filter(show__venue=v, show__is_cancelled=False, date = day['date']).order_by('time') for v in venues]
        slots = max([len(vp) for vp in venue_performances])
        for i in range(slots):
            slot_data = []
            for v in range(len(venues)):
                if (i < len(venue_performances[v])):
                    performance = venue_performances[v][i]
                    slot_data.append(Paragraph(f'{performance.time:%I:%M}', time_style))
                    slot_url = f'http://{ request.get_host() }{ reverse("program:show", args = [performance.show.uuid]) }' 
                    slot_data.append(Paragraph(f'<a href="{ slot_url }">{ performance.show.name }</a>', show_style))
                else:
                    slot_data.append('')
                    slot_data.append('')
            table_data.append(slot_data)

        # Set background color
        table_styles.append(('BACKGROUND', (0, first_row), (-1, len(table_data)), day_color[index % len(day_color)]))
        for i in range(len(venues) - 1):
            table_styles.append(('LINEAFTER', (2*i + 1, first_row + 1), (2*i + 1, len(table_data)), 1, colors.gray))

    # Table styles
    table_styles.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
    table_styles.append(('ALIGN', (0, 0), (-1, 0), 'CENTER'))
    table_styles.append(('LEFTPADDING', (0, 0), (-1, -1), 2))
    table_styles.append(('RIGHTPADDING', (0, 0), (-1, -1), 2))
    table_styles.append(('TOPPADDING', (0, 0), (-1, -1), 1))
    table_styles.append(('BOTTOMPADDING', (0, 0), (-1, -1), 2))
    table_styles.append(('BOX', (0, 0), (-1, -1), 2, colors.gray))
    table_styles.append(('GRID', (0, 0), (-1, 0), 1, colors.gray))
    table_styles.append(('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.gray))

    slot_width_cm = 28.3 / len(venues)
    time_width_cm = 0.9
    show_width_cm = slot_width_cm - time_width_cm
    table = Table(
        table_data,
        colWidths = len(venues) * [time_width_cm*cm, show_width_cm*cm],
        hAlign = 'LEFT',
        vAlign = 'TOP',
        style = table_styles,
    )
    story.append(table)

    # Create PDF document and return it
    doc.build(story)
    return response


def venues(request, festival_uuid=None):

    # Get festival
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.site.info.festival

    # List ticketd and non-ticketd vebues separately
    context = {
        'ticketed_venues': Venue.objects.filter(festival=festival, is_ticketed=True).order_by('map_index', 'name'),
        'nonticketed_venues': Venue.objects.filter(festival=festival, is_ticketed=False).order_by('map_index', 'name'),
    }

    # Render venue list
    return render(request, 'program/venues.html', context)


def venue(request, venue_uuid):

    # Get venue
    venue = get_object_or_404(Venue, uuid = venue_uuid)

    # Render venue details
    context = {
        'venue': venue,
        'shows': venue.shows.order_by(Lower('name')),
    }
    return render(request, 'program/venue.html', context)
