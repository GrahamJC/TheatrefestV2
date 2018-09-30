from django import forms

from .models import Venue, Genre, Show, ShowPerformance

class SearchForm(forms.Form):


    def __init__(self, *args, **kwargs):

        # Save festival
        self.festival = kwargs.pop('festival', None)

        # Call base class
        super().__init__(*args, **kwargs)

        # Search by day
        self.fields['days'] = forms.MultipleChoiceField(choices = ShowPerformance.objects.filter(show__festival=self.festival).order_by('date').values_list('date', 'date').distinct(), required = False, widget = forms.CheckboxSelectMultiple)

        # Search by ticketed venue with option to include non-ticketed
        venue_list = [(v.id, v.name) for v in Venue.objects.filter(festival=self.festival, is_searchable = True)]
        venue_list.append((0, 'Alt Spaces'))
        self.fields['venues'] = forms.MultipleChoiceField(choices = venue_list, required = False, widget = forms.CheckboxSelectMultiple)

        # Search by genre
        self.fields['genres'] = forms.ModelMultipleChoiceField(Genre.objects.filter(festival=self.festival), to_field_name = "id", required = False, widget = forms.CheckboxSelectMultiple())

