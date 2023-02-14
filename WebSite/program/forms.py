from django import forms
from django.core.exceptions import ValidationError

from bootstrap_datepicker_plus.widgets import DatePickerInput, TimePickerInput
from django_select2.forms import Select2MultipleWidget

from .models import Venue, VenueContact, VenueSponsor, Company, CompanyContact, Genre, Show, ShowPerformance, ShowImage, ShowReview


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


class AdminGenreForm(forms.ModelForm):

    class Meta:
        model = Genre
        fields = [
            'name',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A genre with that name already exists'}))


class AdminVenueForm(forms.ModelForm):

    class Meta:
        model = Venue
        fields = [
            'name', 'image',
            'listing', 'listing_short', 'detail',
            'address1', 'address2', 'city', 'post_code',
            'telno', 'email',
            'website', 'twitter', 'facebook', 'instagram',
            'is_ticketed', 'is_scheduled', 'is_searchable',
            'capacity', 'map_index', 'color',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A venue with that name already exists'}))


class AdminVenueContactForm(forms.ModelForm):

    class Meta:
        model = VenueContact
        fields = [
            'name', 'role',
            'address1', 'address2', 'city', 'post_code',
            'telno', 'mobile', 'email',
        ]

    def __init__(self, venue, *args, **kwargs):
        self.venue = venue
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('venue')
        self.instance.venue = self.venue
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A contact with that name already exists'}))


class AdminVenueSponsorForm(forms.ModelForm):

    class Meta:
        model = VenueSponsor
        fields = [
            'name', 'image', 'color', 'background',
            'contact', 'telno', 'email',
            'message',
            'website', 'twitter', 'facebook', 'instagram',
        ]

    def __init__(self, venue, *args, **kwargs):
        self.venue = venue
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('venue')
        self.instance.venue = self.venue
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A sponsor with that name already exists'}))


class AdminCompanyForm(forms.ModelForm):

    class Meta:
        model = Company
        fields = [
            'name', 'image',
            'listing', 'listing_short', 'detail',
            'address1', 'address2', 'city', 'post_code',
            'telno', 'email',
            'website', 'twitter', 'facebook', 'instagram',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of festival)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A company with that name already exists'}))


class AdminCompanyContactForm(forms.ModelForm):

    class Meta:
        model = CompanyContact
        fields = [
            'name', 'role',
            'address1', 'address2', 'city', 'post_code',
            'telno', 'mobile', 'email',
        ]

    def __init__(self, company, *args, **kwargs):
        self.company = company
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of company)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('company')
        self.instance.company = self.company
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A contact with that name already exists'}))
            

class AdminShowForm(forms.ModelForm):

    class Meta:
        model = Show
        fields = [
            'name', 'company', 'venue',
            'image', 'listing', 'listing_short', 'detail',
            'website', 'twitter', 'facebook', 'instagram',
            'genres', 'genre_text', 'has_warnings', 'warnings',
            'age_range', 'duration',
            'is_suspended', 'is_cancelled', 'replaced_by',
        ]
        widgets = {
            'genres': Select2MultipleWidget(attrs={'style': 'width: 100%'}),
        }

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(festival=self.festival)
        self.fields['venue'].queryset = Venue.objects.filter(festival=self.festival)
        self.fields['genres'].queryset = Genre.objects.filter(festival=self.festival)
        self.fields['replaced_by'].queryset = Show.objects.filter(festival=self.festival)
        
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A show with that name already exists'}))


class AdminShowPerformanceForm(forms.ModelForm):

    class Meta:
        model = ShowPerformance
        fields = [
            'date', 'time', 'notes',
        ]
        widgets = {
            'date': DatePickerInput(),
            'time': TimePickerInput(),
        }

    def __init__(self, show, *args, **kwargs):
        self.show = show
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of company)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('show')
        self.instance.show = self.show
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A performance at that date/time already exists'}))


class AdminShowReviewForm(forms.ModelForm):

    class Meta:
        model = ShowReview
        fields = [
            'source', 'rating', 'body', 'url',
        ]

    def __init__(self, show, *args, **kwargs):
        self.show = show
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of company)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('show')
        self.instance.show = self.show
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A review from that source already exists'}))


class AdminShowImageForm(forms.ModelForm):

    class Meta:
        model = ShowImage
        fields = [
            'name', 'image',
        ]

    def __init__(self, show, *args, **kwargs):
        self.show = show
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of company)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('show')
        self.instance.show = self.show
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'An image with that name already exists'}))

