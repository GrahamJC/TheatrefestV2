import datetime

from django import forms
from django.core.exceptions import ValidationError

from bootstrap_datepicker_plus import DatePickerInput

from program.models import Venue, ShowPerformance
from tickets.models import BoxOffice

class SelectForm(forms.Form):

    def create_field(self, name, required):

        # Box office
        if name == 'boxoffice':
            boxoffices = BoxOffice.objects.filter(festival = self.festival).order_by('name')
            choices = [(b.id, b.name) for b in boxoffices]
            choices.insert(0, ('', '' if required else 'All box offices'))
            return forms.ChoiceField(choices = choices, required = required, label = 'Box office')

        # Ticketed venue
        elif name == 'ticketed_venue':
            venues = Venue.objects.filter(festival = self.festival, is_ticketed = True).order_by('name')
            choices = [(v.id, v.name) for v in venues]
            choices.insert(0, ('', '' if required else 'All venues'))
            return forms.ChoiceField(choices = choices, required = required, label = 'Venue')

        # Performance date
        elif name == 'performance_date':
            dates = ShowPerformance.objects.filter(show__festival = self.festival).values('date').order_by('date').distinct()            
            choices = [(f"{d['date']:%Y%m%d}", f"{d['date']:%A, %d %B}") for d in dates]
            choices.insert(0, ('', '' if required else 'All dates'))
            return forms.ChoiceField(choices = choices, required = required, label = 'Date')

        # Box office date
        elif name == 'boxoffice_date':
            first_date = datetime.date(2019, 6, 1)
            last_date = datetime.date(2019, 6, 30)
            dates = [first_date + datetime.timedelta(days = x) for x in range(0, (last_date - first_date).days + 1)]            
            choices = [(f"{d:%Y%m%d}", f"{d:%A, %d %B}") for d in dates]
            choices.insert(0, ('', '' if required else 'All dates'))
            return forms.ChoiceField(choices = choices, required = required, label = 'Date')

        # Field not recognized (shouldn't happen)
        assert False
        return None


    def __init__(self, festival, fields, required, *args, **kwargs):

        # Save festival
        self.festival = festival

        # Call base
        super().__init__(*args, **kwargs)

        # Create fields
        for field in fields:
            self.fields[field] = self.create_field(field, field in required)

