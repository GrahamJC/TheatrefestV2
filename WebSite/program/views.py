import os
import datetime

from django.db.models import Q
from django.db.models.functions import Lower
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template import engines, Template, Context
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab

from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, portrait, landscape
from reportlab.lib.units import cm
from reportlab.lib import colors

from core.models import Festival
from content.models import Image, Resource
from .models import (
    Genre,
    Venue, VenueContact, VenueSponsor,
    Company, CompanyContact,
    Show, ShowPerformance, ShowReview, ShowImage,
)
from .forms import (
   SearchForm, 
   AdminGenreForm,
   AdminVenueForm, AdminVenueContactForm, AdminVenueSponsorForm,
   AdminCompanyForm, AdminCompanyContactForm,
   AdminShowForm, AdminShowPerformanceForm, AdminShowReviewForm, AdminShowImageForm,
)

def shows(request, festival_uuid=None):

    # Get festival
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.festival

    # Create the search form
    search = SearchForm(festival=festival, data=request.GET)

    # Create context
    context = {
        'festival': festival,
        'search': search,
    }

    # If valid add search results to context
    if search.is_valid():
        shows = Show.objects.filter(festival=festival).select_related('company').prefetch_related('genres', 'performances')
        if search.cleaned_data['days']:
            shows = shows.filter(performances__date__in = search.cleaned_data['days'])
        if search.cleaned_data['venues']:
            if '0' in search.cleaned_data['venues']:
                shows = shows.filter(Q(performances__venue_id__in = search.cleaned_data['venues']) | Q(is_ticketed = False))
            else:
                shows = shows.filter(performances__venue_id__in = search.cleaned_data['venues'])
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
        media_url = getattr(settings, 'MEDIA_URL', '/media')
        image_urls = { image.name:os.path.join(media_url, image.image.url) for image in request.festival.images.all() if image.image }
        image_urls.update({ image.name:os.path.join(media_url, image.image.url) for image in show.images.all() if image.image })
        document_urls = { document.name:reverse('content:document', args=[document.uuid]) for document in request.festival.documents.all() if document.file }
        page_urls = { page.name:reverse('content:page', args=[page.uuid]) for page in request.festival.pages.all() }
        resource_urls = { resource.name:reverse('content:resource', args=[resource.uuid]) for resource in request.festival.resources.all() }
        body_context = {
            'show': show,
            'image_urls': image_urls,
            'document_urls': document_urls,
            'page_urls': page_urls,
            'resource_urls': resource_urls,
        }
        template = Template(show.detail)
        html = template.render(Context(body_context))

    # Get show template and render page
    festival_template = Resource.objects.filter(festival=request.festival, name='ShowTemplate').first()
    engine = engines['django']
    if festival_template:
        show_template = engine.from_string(festival_template.body)
    else:
        show_template = engine.get_template('program/show.html')
    sales_closed = request.festival.online_sales_close and (request.now.date() > request.festival.online_sales_close)
    sales_open = request.festival.online_sales_open and (request.now.date() >= request.festival.online_sales_open) and not sales_closed
    context ={
        'show': show,
        'html': html,
        'sales_open_date': request.festival.online_sales_open, 
        'sales_open': sales_open, 
        'sales_closed': sales_closed,
    }
    return HttpResponse(show_template.render(context, request))


def _add_non_scheduled_performances(festival, day):
    performances = []
    for performance in ShowPerformance.objects.filter(show__festival=festival, venue__is_scheduled=False, date = day['date']).order_by('time').values('time', 'show__uuid', 'show__name', 'show__is_cancelled'):
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
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.festival

    # Build the schedule
    days = []
    day = None
    for performance in ShowPerformance.objects.filter(show__festival=festival, venue__is_scheduled=True) \
                                              .order_by('date', 'venue__map_index', 'venue__name', 'time') \
                                              .values('date', 'venue__name', 'venue__color', 'time', 'show__uuid', 'show__name', 'show__is_cancelled'):
            
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
        if venue and performance['venue__name'] != venue['name']:
            day['venues'].append(venue)
            venue = None
        if not venue:
            venue = {
                'name': performance['venue__name'],
                'color': performance['venue__color'],
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
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.festival

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
    venues = Venue.objects.filter(festival=festival, is_ticketed=True).order_by('map_index')
    venues_data = []
    for v in venues:
        venues_data.append(Paragraph(f'<para align="center"><b>{v.name}</b></para>', venue_style))
        venues_data.append('')
    table_data.append(venues_data)
    for i, v in enumerate(venues):
        table_styles.append(('SPAN', (2*i, 0), (2*i + 1, 0)))
        table_styles.append(('BACKGROUND', (2*i, 0), (2*i + 1, 0), v.color ))

    # Days
    days = ShowPerformance.objects.filter(show__festival=festival, show__is_cancelled=False, show__is_ticketed=True).order_by('date').values('date').distinct()
    day_color = ('#fbe4d5', '#fff2cc', '#e2efd9', '#deeaf6')
    for index, day in enumerate(days):

        # Add a row for the day
        first_row = len(table_data)
        table_data.append([Paragraph(f"{day['date']:%A %d}", day_style)] + ['' for i in range(2*len(venues) - 1)])
        table_styles.append(('SPAN', (0, first_row), (-1, first_row)))

        # Get performances for each venue
        venue_performances = [ ShowPerformance.objects.filter(venue=v, show__is_cancelled=False, date = day['date']).order_by('time') for v in venues]
        slots = max([len(vp) for vp in venue_performances])
        for i in range(slots):
            slot_data = []
            for v in range(len(venues)):
                if (i < len(venue_performances[v])):
                    performance = venue_performances[v][i]
                    slot_data.append(Paragraph(f'{performance.time:%H:%M}', time_style))
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
    festival = get_object_or_404(Festival, uuid=festival_uuid) if festival_uuid else request.festival

    # List ticketd and non-ticketd vebues separately
    context = {
        'ticketed_venues': Venue.objects.filter(festival=festival, is_ticketed=True).order_by('map_index', 'name'),
        'nonticketed_venues': Venue.objects.filter(festival=festival, is_ticketed=False).order_by('map_index', 'name'),
    }

    # Get venue map
    venue_map = Image.objects.filter(festival=request.festival, name='VenueMap').first()
    if venue_map:
        context['venue_map'] = venue_map.get_absolute_url()

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


class AdminGenreList(LoginRequiredMixin, ListView):

    model = Genre
    context_object_name = 'genres'
    template_name = 'program/admin_genre_list.html'

    def get_queryset(self):
        return Genre.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Genres' },
        ]
        return context_data


class AdminGenreCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Genre
    form_class = AdminGenreForm
    context_object_name = 'genre'
    template_name = 'program/admin_genre.html'
    success_message = 'Genre added'
    success_url = reverse_lazy('program:admin_genre_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Navigators', 'url': reverse('program:admin_genre_list') },
            { 'text': 'Add' },
        ]
        return context_data


@login_required
@require_POST
def admin_genre_copy(request):

    # Get genre to be copied
    copy_id = int(request.POST['copy_id'])
    if copy_id == 0:
        messages.warning(request, 'No genre selected')
        return redirect('program:admin_genre_list')
    genre_to_copy = get_object_or_404(Genre, id=copy_id)

    # If genre name already exists in this festival add a numeric suffix
    copy_name = genre_to_copy.name
    index = 0
    while Genre.objects.filter(festival=request.festival, name=copy_name).exists():
        index += 1
        copy_name = f"{genre_to_copy.name}_{index}"

    # Copy the genre
    copy_genre = Genre(festival=request.festival, name=copy_name)
    copy_genre.save()
    messages.success(request, 'Genre copied')
    return redirect('program:admin_genre_update', slug=copy_genre.uuid)


class AdminGenreUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Genre
    form_class = AdminGenreForm
    slug_field = 'uuid'
    context_object_name = 'genre'
    template_name = 'program/admin_genre.html'
    success_message = 'Genre updated'
    success_url = reverse_lazy('program:admin_genre_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Navigators', 'url': reverse('program:admin_genre_list') },
            { 'text': 'Update' },
        ]
        return context_data
    

@login_required
def admin_genre_delete(request, slug):

    # Delete genre
    genre = get_object_or_404(Genre, uuid=slug)
    genre.delete()
    messages.success(request, 'Genre deleted')
    return redirect('program:admin_genre_list')


class AdminVenueList(LoginRequiredMixin, ListView):

    model = Venue
    context_object_name = 'venues'
    template_name = 'program/admin_venue_list.html'

    def get_queryset(self):
        return Venue.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues' },
        ]
        return context_data


class AdminVenueCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Venue
    form_class = AdminVenueForm
    context_object_name = 'venue'
    template_name = 'program/admin_venue.html'
    success_message = 'Venue added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_venue_update', args=[self.object.uuid])


@login_required
@require_POST
def admin_venue_copy(request):

    # Get venue to be copied
    copy_id = int(request.POST['copy_id'])
    if copy_id == 0:
        messages.warning(request, 'No venue selected')
        return redirect('program:admin_venue_list')
    venue_to_copy = get_object_or_404(Venue, id=copy_id)

    # If venue name already exists in this festival add a numeric suffix
    copy_name = venue_to_copy.name
    index = 0
    while Venue.objects.filter(festival=request.festival, name=copy_name).exists():
        index += 1
        copy_name = f"{venue_to_copy.name}_{index}"

    # Copy the venue and contacts (but not sponsors)
    copy_venue = Venue(festival=request.festival, name=copy_name)
    copy_venue.image = venue_to_copy.image
    copy_venue.listing = venue_to_copy.listing
    copy_venue.listing_short = venue_to_copy.listing_short
    copy_venue.detail = venue_to_copy.detail
    copy_venue.address1 = venue_to_copy.address1
    copy_venue.address2 = venue_to_copy.address2
    copy_venue.city = venue_to_copy.city
    copy_venue.post_code = venue_to_copy.post_code
    copy_venue.telno = venue_to_copy.telno
    copy_venue.email = venue_to_copy.email
    copy_venue.website = venue_to_copy.website
    copy_venue.facebook = venue_to_copy.facebook
    copy_venue.twitter = venue_to_copy.twitter
    copy_venue.instagram = venue_to_copy.instagram
    copy_venue.is_ticketed = venue_to_copy.is_ticketed
    copy_venue.is_scheduled = venue_to_copy.is_scheduled
    copy_venue.is_searchable = venue_to_copy.is_searchable
    copy_venue.capacity = venue_to_copy.capacity
    copy_venue.map_index = venue_to_copy.map_index
    copy_venue.color = venue_to_copy.color
    copy_venue.save()
    for contact in venue_to_copy.contacts.all():
        copy_contact = VenueContact(venue=copy_venue, name=contact.name)
        copy_contact.role = contact.role
        copy_contact.address1 = contact.address1
        copy_contact.address2 = contact.address2
        copy_contact.city = contact.city
        copy_contact.post_code = contact.post_code
        copy_contact.telno = contact.telno
        copy_contact.mobile = contact.mobile
        copy_contact.email = contact.email
        copy_contact.save()
    messages.success(request, 'Venue copied')
    return redirect('program:admin_venue_update', slug=copy_venue.uuid)


class AdminVenueUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Venue
    form_class = AdminVenueForm
    slug_field = 'uuid'
    context_object_name = 'venue'
    template_name = 'program/admin_venue.html'
    success_message = 'Venue updated'
    success_url = reverse_lazy('program:admin_venue_list')

    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['listing'].widget.attrs['rows'] = 4
        form.fields['listing_short'].widget.attrs['rows'] = 2
        form.fields['detail'].widget.attrs['rows'] = 16
        form.fields['is_ticketed'].label = 'Ticketed'
        form.fields['is_scheduled'].label = 'Scheduled'
        form.fields['is_searchable'].label = 'Searchable'
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            TabHolder(
                Tab ('General',
                    'image',
                    'listing',
                    'listing_short',
                    Row(
                        Column('is_ticketed', css_class='form-group col-md-4 mb-0'),
                        Column('is_scheduled', css_class='form-group col-md-4 mb-0'),
                        Column('is_searchable', css_class='form-group col-md-4 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('capacity', css_class='form-group col-md-4 mb-0'),
                        Column('map_index', css_class='form-group col-md-4 mb-0'),
                        Column('color', css_class='form-group col-md-4 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Details',
                    'detail',
                ),
                Tab('Address',
                    'address1',
                    'address2',
                    Row(
                        Column('city', css_class='form-group col-md-8 mb-0'),
                        Column('post_code', css_class='form-group col-md-4 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('telno', css_class='form-group col-md-4 mb-0'),
                        Column('email', css_class='form-group col-md-8 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Social Media',
                    Row(
                        Column('website', css_class='form-group col-md-6 mb-0'),
                        Column('twitter', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('facebook', css_class='form-group col-md-6 mb-0'),
                        Column('instagram', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Contacts',
                    HTML('{% include \'program/_admin_venue_contacts.html\' %}')
                ),
                Tab('Sponsors',
                    HTML('{% include \'program/_admin_venue_sponsors.html\' %}')
                ),
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        return context_data

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': 'Update' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data
    

@login_required
def admin_venue_delete(request, slug):

    # Delete venue
    venue = get_object_or_404(Venue, uuid=slug)
    venue.delete()
    messages.success(request, 'Venue deleted')
    return redirect('program:admin_venue_list')


class AdminVenueContactCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = VenueContact
    form_class = AdminVenueContactForm
    context_object_name = 'contact'
    template_name = 'program/admin_venue_contact.html'
    success_message = 'Venue contact added'

    def dispatch(self, request, *args, **kwargs):
        self.venue = get_object_or_404(Venue, uuid=kwargs['venue_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['venue'] = self.venue
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('role'),
            Field('address1'),
            Field('address2'),
            Row(
                Column('city', css_class='form-group col-md-8 mb-0'),
                Column('post_code', css_class='form-group col-md-4 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('telno', css_class='form-group col-md-6 mb-0'),
                Column('mobile', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('email'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['venue'] = self.venue
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': self.venue.name, 'url': reverse('program:admin_venue_update', args=[self.venue.uuid]) },
            { 'text': 'Add Contact' },
        ]
        return context_data


    def get_success_url(self):
        return reverse('program:admin_venue_update_tab', args=[self.venue.uuid, 'contacts'])


class AdminVenueContactUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = VenueContact
    form_class = AdminVenueContactForm
    slug_field = 'uuid'
    context_object_name = 'contact'
    template_name = 'program/admin_venue_contact.html'
    success_message = 'Venue contact updated'

    def dispatch(self, request, *args, **kwargs):
        self.venue = get_object_or_404(Venue, uuid=kwargs['venue_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['venue'] = self.venue
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('role'),
            Field('address1'),
            Field('address2'),
            Row(
                Column('city', css_class='form-group col-md-8 mb-0'),
                Column('post_code', css_class='form-group col-md-4 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('telno', css_class='form-group col-md-6 mb-0'),
                Column('mobile', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('email'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        return context_data

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['venue'] = self.venue
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': self.venue.name, 'url': reverse('program:admin_venue_update', args=[self.venue.uuid]) },
            { 'text': 'Update Contact' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        return reverse('program:admin_venue_update_tab', args=[self.venue.uuid, 'contacts'])
    

@login_required
def admin_venue_contact_delete(request, venue_uuid, slug):

    # Delete venue contact
    contact = get_object_or_404(VenueContact, uuid=slug)
    contact.delete()
    messages.success(request, 'Venue contact deleted')
    return redirect('program:admin_venue_update_tab', venue_uuid, 'contacts')


class AdminVenueSponsorCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = VenueSponsor
    form_class = AdminVenueSponsorForm
    context_object_name = 'sponsor'
    template_name = 'program/admin_venue_sponsor.html'
    success_message = 'Venue sponsor added'

    def dispatch(self, request, *args, **kwargs):
        self.venue = get_object_or_404(Venue, uuid=kwargs['venue_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['venue'] = self.venue
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('image'),
            Field('message'),
            Row(
                Column('color', css_class='form-group col-md-6 mb-0'),
                Column('background', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('contact'),
            Row(
                Column('telno', css_class='form-group col-md-4 mb-0'),
                Column('email', css_class='form-group col-md-8 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('website', css_class='form-group col-md-6 mb-0'),
                Column('facebook', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('twitter', css_class='form-group col-md-6 mb-0'),
                Column('instagram', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['venue'] = self.venue
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': self.venue.name, 'url': reverse('program:admin_venue_update', args=[self.venue.uuid]) },
            { 'text': 'Add Sponsor' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        return reverse('program:admin_venue_update_tab', args=[self.venue.uuid, 'sponsors'])


class AdminVenueSponsorUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = VenueSponsor
    form_class = AdminVenueSponsorForm
    slug_field = 'uuid'
    context_object_name = 'sponsor'
    template_name = 'program/admin_venue_sponsor.html'
    success_message = 'Venue sponsor updated'

    def dispatch(self, request, *args, **kwargs):
        self.venue = get_object_or_404(Venue, uuid=kwargs['venue_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['venue'] = self.venue
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('image'),
            Field('message'),
            Row(
                Column('color', css_class='form-group col-md-6 mb-0'),
                Column('background', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('contact'),
            Row(
                Column('telno', css_class='form-group col-md-4 mb-0'),
                Column('email', css_class='form-group col-md-8 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('website', css_class='form-group col-md-6 mb-0'),
                Column('facebook', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('twitter', css_class='form-group col-md-6 mb-0'),
                Column('instagram', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['venue'] = self.venue
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Venues', 'url': reverse('program:admin_venue_list') },
            { 'text': self.venue.name, 'url': reverse('program:admin_venue_update', args=[self.venue.uuid]) },
            { 'text': 'Update Sponsor' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        return reverse('program:admin_venue_update_tab', args=[self.venue.uuid, 'sponsors'])
    

@login_required
def admin_venue_sponsor_delete(request, venue_uuid, slug):

    # Delete venue sponsor
    sponsor = get_object_or_404(VenueSponsor, uuid=slug)
    sponsor.delete()
    messages.success(request, 'Venue sponsor deleted')
    return redirect('program:admin_venue_update_tab', venue_uuid, 'sponsors')


class AdminCompanyList(LoginRequiredMixin, ListView):

    model = Company
    context_object_name = 'companies'
    template_name = 'program/admin_company_list.html'

    def get_queryset(self):
        return Company.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Companies' },
        ]
        return context_data


class AdminCompanyCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Company
    form_class = AdminCompanyForm
    context_object_name = 'company'
    template_name = 'program/admin_company.html'
    success_message = 'Company added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Companies', 'url': reverse('program:admin_company_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_company_update', args=[self.object.uuid])


class AdminCompanyUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Company
    form_class = AdminCompanyForm
    slug_field = 'uuid'
    context_object_name = 'company'
    template_name = 'program/admin_company.html'
    success_message = 'Company updated'
    success_url = reverse_lazy('program:admin_company_list')

    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['listing'].widget.attrs['rows'] = 4
        form.fields['listing_short'].widget.attrs['rows'] = 2
        form.fields['detail'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            TabHolder(
                Tab ('General',
                    'image',
                    'listing',
                    'listing_short',
                ),
                Tab('Details',
                    'detail',
                ),
                Tab('Address',
                    'address1',
                    'address2',
                    Row(
                        Column('city', css_class='form-group col-md-8 mb-0'),
                        Column('post_code', css_class='form-group col-md-4 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('telno', css_class='form-group col-md-4 mb-0'),
                        Column('email', css_class='form-group col-md-8 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Social Media',
                    Row(
                        Column('website', css_class='form-group col-md-6 mb-0'),
                        Column('twitter', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('facebook', css_class='form-group col-md-6 mb-0'),
                        Column('instagram', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Contacts',
                    HTML('{% include \'program/_admin_company_contacts.html\' %}')
                ),
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Companies', 'url': reverse('program:admin_company_list') },
            { 'text': 'Update' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data
    

@login_required
def admin_company_delete(request, slug):

    # Delete company
    company = get_object_or_404(Company, uuid=slug)
    company.delete()
    messages.success(request, 'Company deleted')
    return redirect('program:admin_company_list')


class AdminCompanyContactCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = CompanyContact
    form_class = AdminCompanyContactForm
    context_object_name = 'contact'
    template_name = 'program/admin_company_contact.html'
    success_message = 'Company contact added'

    def dispatch(self, request, *args, **kwargs):
        self.company = get_object_or_404(Company, uuid=kwargs['company_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.company
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('role'),
            Field('address1'),
            Field('address2'),
            Row(
                Column('city', css_class='form-group col-md-8 mb-0'),
                Column('post_code', css_class='form-group col-md-4 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('telno', css_class='form-group col-md-6 mb-0'),
                Column('mobile', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('email'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['company'] = self.company
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Companies', 'url': reverse('program:admin_company_list') },
            { 'text': self.company.name, 'url': reverse('program:admin_company_update', args=[self.company.uuid]) },
            { 'text': 'Add Contact' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_company_update_tab', args=[self.company.uuid, 'contacts'])


class AdminCompanyContactUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = CompanyContact
    form_class = AdminCompanyContactForm
    slug_field = 'uuid'
    context_object_name = 'contact'
    template_name = 'program/admin_company_contact.html'
    success_message = 'Company contact updated'

    def dispatch(self, request, *args, **kwargs):
        self.company = get_object_or_404(Company, uuid=kwargs['company_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.company
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('role'),
            Field('address1'),
            Field('address2'),
            Row(
                Column('city', css_class='form-group col-md-8 mb-0'),
                Column('post_code', css_class='form-group col-md-4 mb-0'),
                css_class = 'form-row',
            ),
            Row(
                Column('telno', css_class='form-group col-md-6 mb-0'),
                Column('mobile', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('email'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['company'] = self.company
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Companies', 'url': reverse('program:admin_company_list') },
            { 'text': self.company.name, 'url': reverse('program:admin_company_update', args=[self.company.uuid]) },
            { 'text': 'Update Contact' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_company_update_tab', args=[self.company.uuid, 'contacts'])
    

@login_required
def admin_company_contact_delete(request, company_uuid, slug):

    # Delete company contact
    contact = get_object_or_404(CompanyContact, uuid=slug)
    contact.delete()
    messages.success(request, 'Company contact deleted')
    return redirect('program:admin_company_update_tab', company_uuid, 'contacts')


class AdminShowList(LoginRequiredMixin, ListView):

    model = Show
    context_object_name = 'shows'
    template_name = 'program/admin_show_list.html'

    def get_queryset(self):
        return Show.objects.filter(festival=self.request.festival)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['festival'] = self.request.festival
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows' },
        ]
        return context_data


class AdminShowCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Show
    form_class = AdminShowForm
    context_object_name = 'show'
    template_name = 'program/admin_show.html'
    success_message = 'Show added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            Field('company'),
            Field('is_ticketed'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': 'Add' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update', args=[self.object.uuid])


class AdminShowUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Show
    form_class = AdminShowForm
    slug_field = 'uuid'
    context_object_name = 'show'
    template_name = 'program/admin_show.html'
    success_message = 'Show updated'
    success_url = reverse_lazy('program:admin_show_list')

    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['listing'].widget.attrs['rows'] = 4
        form.fields['listing_short'].widget.attrs['rows'] = 2
        form.fields['detail'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            TabHolder(
                Tab ('General',
                    Field('company'),
                    Field('is_ticketed'),
                    'image',
                    'listing',
                    'listing_short',
                ),
                Tab('Information',
                    Row(
                        Column('genres', css_class='form-group col-md-6 mb-0'),
                        Column('genre_text', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('age_range', css_class='form-group col-md-6 mb-0'),
                        Column('duration', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    'has_warnings',
                    'warnings',
                    Row(
                        Column('is_suspended', css_class='form-group col-md-2 mb-0'),
                        Column('is_cancelled', css_class='form-group col-md-2 mb-0'),
                        css_class = 'form-row',
                    ),
                    'replaced_by',
                ),
                Tab('Details',
                    'detail',
                ),
                Tab('Social Media',
                    Row(
                        Column('website', css_class='form-group col-md-6 mb-0'),
                        Column('twitter', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                    Row(
                        Column('facebook', css_class='form-group col-md-6 mb-0'),
                        Column('instagram', css_class='form-group col-md-6 mb-0'),
                        css_class = 'form-row',
                    ),
                ),
                Tab('Performances',
                    HTML('{% include \'program/_admin_show_performances.html\' %}'),
                ),
                Tab('Reviews',
                    HTML('{% include \'program/_admin_show_reviews.html\' %}'),
                ),
                Tab('Images',
                    HTML('{% include \'program/_admin_show_images.html\' %}'),
                ),
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel', css_class='btn-secondary'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': 'Update' },
        ]
        context_data['initial_tab'] = self.initial_tab
        return context_data
    

@login_required
def admin_show_delete(request, slug):

    # Delete show
    show = get_object_or_404(Show, uuid=slug)
    show.delete()
    messages.success(request, 'Show deleted')
    return redirect('program:admin_show_list')


class AdminShowPerformanceCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = ShowPerformance
    form_class = AdminShowPerformanceForm
    context_object_name = 'performance'
    template_name = 'program/admin_show_performance.html'
    success_message = 'Show performance added'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('date', css_class='form-group col-md-6 mb-0'),
                Column('time', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('venue'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Add Performance' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'performances'])


class AdminShowPerformanceUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = ShowPerformance
    form_class = AdminShowPerformanceForm
    slug_field = 'uuid'
    context_object_name = 'performance'
    template_name = 'program/admin_show_performance.html'
    success_message = 'Show performance updated'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('date', css_class='form-group col-md-6 mb-0'),
                Column('time', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            Field('venue'),
            Field('notes'),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Update Performance' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'performances'])
    

@login_required
def admin_show_performance_delete(request, show_uuid, slug):

    # Delete show performance
    performance = get_object_or_404(ShowPerformance, uuid=slug)
    performance.delete()
    messages.success(request, 'Show performance deleted')
    return redirect('program:admin_show_update_tab', show_uuid, 'performances')


class AdminShowReviewCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = ShowReview
    form_class = AdminShowReviewForm
    context_object_name = 'review'
    template_name = 'program/admin_show_review.html'
    success_message = 'Show review added'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'source',
            'rating',
            'body',
            'url',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Add Review' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'reviews'])


class AdminShowReviewUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = ShowReview
    form_class = AdminShowReviewForm
    slug_field = 'uuid'
    context_object_name = 'review'
    template_name = 'program/admin_show_review.html'
    success_message = 'Show review updated'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'source',
            'rating',
            'body',
            'url',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Update Review' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'reviews'])
    

@login_required
def admin_show_review_delete(request, show_uuid, slug):

    # Delete show review
    review = get_object_or_404(ShowReview, uuid=slug)
    review.delete()
    messages.success(request, 'Show review deleted')
    return redirect('program:admin_show_update_tab', show_uuid, 'reviews')


class AdminShowImageCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = ShowImage
    form_class = AdminShowImageForm
    context_object_name = 'image'
    template_name = 'program/admin_show_image.html'
    success_message = 'Show image added'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Add Image' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'images'])


class AdminShowImageUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = ShowImage
    form_class = AdminShowImageForm
    slug_field = 'uuid'
    context_object_name = 'image'
    template_name = 'program/admin_show_image.html'
    success_message = 'Show image updated'

    def dispatch(self, request, *args, **kwargs):
        self.show = get_object_or_404(Show, uuid=kwargs['show_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['show'] = self.show
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['show'] = self.show
        context_data['breadcrumbs'] = [
            { 'text': 'Festival Admin', 'url': reverse('festival:admin') },
            { 'text': 'Shows', 'url': reverse('program:admin_show_list') },
            { 'text': self.show.name, 'url': reverse('program:admin_show_update', args=[self.show.uuid]) },
            { 'text': 'Update Image' },
        ]
        return context_data

    def get_success_url(self):
        return reverse('program:admin_show_update_tab', args=[self.show.uuid, 'images'])
    

@login_required
def admin_show_image_delete(request, show_uuid, slug):

    # Delete show image
    image = get_object_or_404(ShowImage, uuid=slug)
    image.delete()
    messages.success(request, 'Show image deleted')
    return redirect('program:admin_show_update_tab', show_uuid, 'images')
