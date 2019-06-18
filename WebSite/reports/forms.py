import datetime

from django import forms
from django.core.exceptions import ValidationError

from bootstrap_datepicker_plus import DatePickerInput

from program.models import Venue, Show, ShowPerformance
from tickets.models import BoxOffice


class SelectVenueDateForm(forms.Form):

    venue = forms.ChoiceField(choices = [], label = 'Venue')
    date = forms.ChoiceField(choices = [], label = 'Date')

    def __init__(self, festival, fields, required, *args, **kwargs):

        # Save festival
        self.festival = festival

        # Call base
        super().__init__(*args, **kwargs)

        # Venue
        if 'venue' in fields:
            is_required = 'venue' in required
            self.fields['venue'].required = is_required
            choices = [('', 'Select venue' if required else 'All venues')]
            for venue in Venue.objects.filter(festival = self.festival, is_ticketed = True).order_by('name'):
                choices.append((venue.id, venue.name))
            self.fields['venue'].choices = choices

        # Date
        if 'date' in fields:
            is_required = 'date' in required
            self.fields['date'].required = is_required
            choices = [('', 'Select date' if is_required else 'All dates')]
            for date in ShowPerformance.objects.filter(show__festival = self.festival).values('date').order_by('date').distinct():
                choices.append((f"{date['date']:%Y%m%d}", f"{date['date']:%A, %d %B}"))
            self.fields['date'].choices = choices


class SelectBoxOfficeDateForm(forms.Form):

    boxoffice = forms.ChoiceField(choices = [], label = 'Box office')
    date = forms.ChoiceField(choices = [], label = 'Date')

    def __init__(self, festival, fields, required, *args, **kwargs):

        # Save festival
        self.festival = festival

        # Call base
        super().__init__(*args, **kwargs)

        # Box office
        if 'boxoffice' in fields:
            is_required = 'boxoffice' in required
            self.fields['boxoffice'].required = is_required
            choices = [('', 'Select box office' if required else 'All box offices')]
            for boxoffice in BoxOffice.objects.filter(festival = self.festival).order_by('name'):
                choices.append((boxoffice.id, boxoffice.name))
            self.fields['boxoffice'].choices = choices

        # Date
        if 'date' in fields:
            is_required = 'date' in required
            self.fields['date'].required = is_required
            choices = [('', 'Select date' if is_required else 'All dates')]
            first_date = datetime.date(2019, 6, 1)
            last_date = datetime.date(2019, 6, 30)
            dates = [first_date + datetime.timedelta(days = x) for x in range(0, (last_date - first_date).days + 1)]            
            for x in range(0, (last_date - first_date).days + 1):
                date = first_date + datetime.timedelta(days = x)
                choices.append((f"{date:%Y%m%d}", f"{date:%A, %d %B}"))
            self.fields['date'].choices = choices


class SelectTicketedShowForm(forms.Form):

    show = forms.ChoiceField(choices = [], label = 'Show')

    def __init__(self, festival, fields, required, *args, **kwargs):

        # Save festival
        self.festival = festival

        # Call base
        super().__init__(*args, **kwargs)

        # Show
        if 'show' in fields:
            is_required = 'show' in required
            self.fields['show'].required = is_required
            choices = [('', 'Select show' if required else 'All shows')]
            for show in Show.objects.filter(festival = self.festival, venue__is_ticketed = True).order_by('name'):
                choices.append((show.id, show.name))
            self.fields['show'].choices = choices
