from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django import forms
from collections import OrderedDict

from bootstrap_datepicker_plus.widgets import DatePickerInput, TimePickerInput
from django_select2.forms import Select2MultipleWidget

from core.forms import MultiModelForm
from core.models import User
from core.widgets import ModelSelect2

from .models import Role, Location, Volunteer, Shift


class AdminRoleForm(forms.ModelForm):

    class Meta:
        model = Role
        fields = [
            'description',
            'comps_per_shift',
            'information',
        ]
        labels = {
            'comps_per_shift': 'Complimentary tickets per shift',
        }
        
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


class AdminShiftSearchForm(forms.Form):

    STATUS_CHOICES = [('All', 'All'), ('Accepted', 'Accepted'), ('NotAccepted', 'Not accepted')]
    status = forms.ChoiceField(choices = STATUS_CHOICES, label = 'Status', required = True)

    def __init__(self, festival, *args, **kwargs):

        # Save festival
        self.festival = festival
        super().__init__(*args, **kwargs)

        # Create fields
        shift_dates = Shift.objects.filter(location__festival = self.festival).values('date').order_by('date').distinct()
        date_choices = [('20000101', 'All dates')]
        date_choices.extend([(sd['date'].strftime('%Y%m%d'), sd['date'].strftime('%A, %d %B')) for sd in shift_dates])
        self.fields['date'] = forms.ChoiceField(choices = date_choices, required = False)
        location_choices = [('0', 'All locations')]
        location_choices.extend([(l.id, l.description) for l in Location.objects.filter(festival = festival).order_by('description')])
        self.fields['location'] = forms.ChoiceField(choices = location_choices, required = False)
        role_choices = [('0', 'All roles')]
        role_choices.extend([(r.id, r.description) for r in Role.objects.filter(festival = festival).order_by('description')])
        self.fields['role'] = forms.ChoiceField(choices = role_choices, required = False)
        volunteer_choices = [('0', 'All volunteers')]
        volunteer_choices.extend([(v.user_id, f"{ v.user.last_name }, { v.user.first_name }") for v in Volunteer.objects.filter(user__festival = festival).order_by('user__last_name', 'user__first_name')])
        self.fields['volunteer'] = forms.ChoiceField(choices = volunteer_choices, required = False)

class AdminShiftForm(forms.ModelForm):

    class Meta:
        model = Shift
        fields = [
            'location', 
            'date', 'start_time', 'end_time',
            'role',
            'needs_dbs',
            'volunteer_can_accept',
            'volunteer',
            'notes',
        ]
        labels = {
            'needs_dbs': 'Needs DBS check',
        }
        widgets = {
            'date': DatePickerInput(),
            'start_time': TimePickerInput(),
            'end_time': TimePickerInput(),
        }


    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.filter(festival=festival)
        self.fields['location'].queryset = Location.objects.filter(festival=festival)
        self.fields['volunteer'].queryset = Volunteer.objects.filter(user__festival=festival).order_by('user__last_name', 'user__first_name')

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

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'is_boxoffice', 'is_venue')
        required = ('email', 'first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        self.festival = kwargs.pop('festival')
        if self.festival == None:
            raise ValueError('festival is required')
        super().__init__(*args, **kwargs)
        for field in self.Meta.required:
            self.fields[field].required = True

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({'email': 'A user with that e-mail already exists'}))


class VolunteerRolesForm(forms.ModelForm):

    class Meta:
        model = Volunteer
        fields = [
            'is_dbs',
            'roles',
        ]
        labels = {
            'is_dbs': 'Is DBS checked',
        }
        widgets = {
            'roles': Select2MultipleWidget(attrs={'style': 'width: 100%'}),
        }


    def __init__(self, *args, **kwargs):
        self.festival = kwargs.pop('festival')
        if self.festival == None:
            raise ValueError('festival is required')
        super().__init__(*args, **kwargs)
        self.fields['roles'].queryset = Role.objects.filter(festival=self.festival)


class AdminVolunteerForm(MultiModelForm):

    form_classes = OrderedDict((
        ('user', VolunteerUserForm),
        ('volunteer', VolunteerRolesForm),
    ))
