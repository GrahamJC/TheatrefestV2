from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password

from bootstrap_datepicker_plus.widgets import DatePickerInput

from core.models import User, Festival
from content.models import Page, PageImage, Navigator
from program.models import Company, Venue, Show, ShowPerformance
from tickets.models import BoxOffice, TicketType, FringerType, Bucket

class PageForm(forms.ModelForm):

    class Meta:
        model = Page
        fields = ('festival', 'name', 'title', 'body')
        widgets = {
            'festival': forms.HiddenInput(),
        }

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A page with that name already exists'}))


class PageImageForm(forms.ModelForm):

    class Meta:
        model = PageImage
        fields = ('page', 'name', 'image')

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'An image with that name already exists'}))


class NavigatorForm(forms.ModelForm):

    class Meta:
        model = Navigator
        fields = ('festival', 'seqno', 'label', 'type', 'url', 'page')
        widgets = {
            'festival': forms.HiddenInput(),
        }

    def __init__(self, festival, *args, **kwargs):

        # Call base class
        super().__init__(*args, **kwargs)

        # Restrict pages to current festival
        self.fields['page'] = forms.ModelChoiceField(Page.objects.filter(festival=festival), to_field_name = "id", required = False)


    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A navigator with that name already exists'}))


class PasswordResetForm(forms.Form):

    password = forms.CharField(required = True, widget = forms.PasswordInput)

    def clean_password(self):
        data = self.cleaned_data['password']
        validate_password(data)
        return data


class EMailForm(forms.Form):

    subject = forms.CharField(required = True, max_length = 64)
    body = forms.CharField(required = True, widget = forms.Textarea)


class AdminSaleListForm(forms.Form):

    date = forms.DateField(required = False, initial = datetime.today(), widget = DatePickerInput)
    customer = forms.CharField(required = False, label = 'Customer (contains)', widget = forms.TextInput(attrs = {'size': 64}))
    sale_type = forms.ChoiceField(choices = (('All', 'All'), ('Online', 'Online'), ('Boxoffice', 'Boxoffice'), ('Venue', 'Venue')), initial = 'All', widget = forms.RadioSelect)

    def __init__(self, festival, *args, **kwargs):

        # Call base class
        super().__init__(*args, **kwargs)

        # Add venue field
        self.fields['boxoffice'] = forms.ModelChoiceField(BoxOffice.objects.filter(festival = festival), required = False)
        self.fields['venue'] = forms.ModelChoiceField(Venue.objects.filter(festival = festival, is_ticketed = True), required = False)


class AdminFestivalForm(forms.ModelForm):

    class Meta:
        model = Festival
        fields = [
            'online_sales_open',
            'online_sales_close',
            'boxoffice_open',
            'boxoffice_close',
            'button_price',
            'volunteer_comps',
        ]
        widgets = {
            'online_sales_open': DatePickerInput,
            'online_sales_close': DatePickerInput,
            'boxoffice_open': DatePickerInput,
            'boxoffice_close': DatePickerInput,
        }

class AdminTicketTypeForm(forms.ModelForm):

    class Meta:
        model = TicketType
        fields = [
            'seqno','name',
            'price', 'payment',
            'is_online', 'is_boxoffice', 'is_venue',
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
            self._update_errors(ValidationError({'name': 'A ticket type with that name already exists'}))

class AdminFringerTypeForm(forms.ModelForm):

    class Meta:
        model = FringerType
        fields = [
            'name',
            'price', 'shows',
            'is_online',
            'ticket_type',
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
            self._update_errors(ValidationError({'name': 'A fringer type with that name already exists'}))

class AdminBucketForm(forms.ModelForm):

    class Meta:
        model = Bucket
        fields = [
            'date',
            'company',
            'show',
            'performance',
            'description',
            'cash',
            'fringers',
            'cards',
            'audience'
        ]
        widgets = {
            'date': DatePickerInput,
        }

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(festival=self.festival)
        self.fields['company'].label_from_instance = self.company_label_from_instance
        if hasattr(self.instance, 'company'):
            self.fields['show'].queryset = Show.objects.filter(company=self.instance.company)
        else:
            self.fields['show'].queryset = Show.objects.filter(pk=0)
        self.fields['show'].label_from_instance = self.show_label_from_instance
        if hasattr(self.instance, 'show'):
            self.fields['performance'].queryset = ShowPerformance.objects.filter(show=self.instance.show)
        else:
            self.fields['performance'].queryset = ShowPerformance.objects.filter(pk=0)
        self.fields['performance'].label_from_instance = self.performance_label_from_instance
        self.fields['description'].label = 'Notes'

    def clean_company(self):
        # Update show queryset for selected company
        company = self.cleaned_data['company']
        if company:
            self.fields['show'].queryset = Show.objects.filter(company=company)
        return company

    def clean_show(self):
        # Update performance queryset for selected show
        show = self.cleaned_data['show']
        if show:
            self.fields['performance'].queryset = ShowPerformance.objects.filter(show=show)
        return show
    
    @staticmethod
    def company_label_from_instance(obj):
        return obj.name

    @staticmethod
    def show_label_from_instance(obj):
        return obj.name

    @staticmethod
    def performance_label_from_instance(obj):
        return f'{obj.date:%A %b %d} at {obj.time:%I:%M%p}'
    