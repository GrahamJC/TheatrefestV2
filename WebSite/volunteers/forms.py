from django.core.exceptions import NON_FIELD_ERRORS
from django import forms

from bootstrap_datepicker_plus import DatePickerInput, TimePickerInput
from django_select2.forms import Select2MultipleWidget

from core.models import User
from core.widgets import ModelSelect2

from .models import Role, Location, Volunteer, Shift


class AdminRoleForm(forms.ModelForm):

    class Meta:
        model = Role
        fields = [
            'description',
            'information',
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
            self._update_errors(ValidationError({'description': 'A role with that description already exists'}))


class AdminLocationForm(forms.ModelForm):

    class Meta:
        model = Location
        fields = [
            'description',
            'information',
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
            self._update_errors(ValidationError({'description': 'A location with that description already exists'}))
            

class AdminShiftForm(forms.ModelForm):

    class Meta:
        model = Shift
        fields = [
            'location', 
            'date', 'start_time', 'end_time',
            'role',
            'volunteer'
        ]
        widgets = {
            'date': DatePickerInput(),
            'start_time': TimePickerInput(),
            'end_time': TimePickerInput(),
        }


    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = Location.objects.filter(festival=festival)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({NON_FIELD_ERRORS: 'A shift with the same location, start date/time and role already exists'}))


class VolunteerAddForm(forms.Form):

    def __init__(self, festival, *args, **kwargs):

        # Call base class
        super().__init__(*args, **kwargs)

        # Restrict users to current festival
        self.fields['user'] = forms.ModelChoiceField(
            queryset = User.objects.filter(festival=festival, is_volunteer=False),
            widget = ModelSelect2(
                url = 'volunteers:admin_volunteer_autocomplete',
                attrs = {
                    'data-theme': 'bootstrap4',
                }
            )
        )


class VolunteerUserForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.Meta.required:
            self.fields[field].required = True

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        required = ('email', 'first_name', 'last_name')


class VolunteerRolesForm(forms.ModelForm):

    class Meta:
        model = Volunteer
        fields = [
            'roles',
        ]
        widgets = {
            'roles': Select2MultipleWidget(attrs={'style': 'width: 100%'}),
        }


class SelectShiftsForm(forms.Form):

    location = forms.ModelChoiceField(
        queryset = Location.objects.none(),
        required = False,
    )
    date = forms.DateField(
        widget = DatePickerInput(),
        required = False,
    )

    def __init__(self, festival, *args, **kwargs):

        # Call base class
        super().__init__(*args, **kwargs)

        # Restrict locations to current festival
        self.fields['location'].queryset = Location.objects.filter(festival=festival)
