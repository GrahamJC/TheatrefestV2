from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django import forms
from collections import OrderedDict

from bootstrap_datepicker_plus.widgets import DatePickerInput, TimePickerInput
from django_select2.forms import Select2MultipleWidget

from core.forms import MultiModelForm
from core.models import User
from core.widgets import ModelSelect2

from .models import Role, Location, Volunteer, Commitment, Shift

# Logging
import logging
logger = logging.getLogger(__name__)

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
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': 'A role with that description already exists',
            }
        }
        
    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival


class AdminLocationForm(forms.ModelForm):

    class Meta:
        model = Location
        fields = [
            'description',
            'information',
        ]
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': 'A location with that description already exists',
            }
        }

    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival


class AdminCommitmentForm(forms.ModelForm):

    class Meta:
        model = Commitment
        fields = [
            'description', 
            'role',
            'needs_dbs',
            'volunteer_can_accept',
            'volunteer',
            'notes',
        ]
        labels = {
            'needs_dbs': 'Needs DBS check',
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': 'A commitment with that description already exists',
            }
        }

    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival
        self.fields['role'].queryset = Role.objects.filter(festival=festival)
        self.fields['volunteer'].queryset = Volunteer.objects.filter(user__festival=festival).order_by('user__last_name', 'user__first_name')


class AdminShiftSearchForm(forms.Form):

    STATUS_CHOICES = [('All', 'All'), ('Accepted', 'Accepted'), ('NotAccepted', 'Not accepted')]

    date = forms.ChoiceField(required=False)
    location = forms.ChoiceField(required=False)
    role = forms.ChoiceField(required=False)
    volunteer = forms.ChoiceField(required=False)
    status = forms.ChoiceField(choices = STATUS_CHOICES, label = 'Status', required = True)
    include_commitments = forms.BooleanField(label='Include commitment shifts', required=False)

    def __init__(self, festival, *args, **kwargs):

        # Save festival
        self.festival = festival
        super().__init__(*args, **kwargs)

        # Set field choices
        shift_dates = Shift.objects.filter(location__festival = self.festival).values('date').order_by('date').distinct()
        self.fields['date'].choices = [('20000101', 'All dates')] + [(sd['date'].strftime('%Y%m%d'), sd['date'].strftime('%A, %d %B')) for sd in shift_dates]
        self.fields['location'].choices = [('0', 'All locations')] + [(l.id, l.description) for l in Location.objects.filter(festival = festival).order_by('description')]
        self.fields['role'].choices = [('0', 'All roles')] + [(r.id, r.description) for r in Role.objects.filter(festival = festival).order_by('description')]
        self.fields['volunteer'].choices = [('0', 'All volunteers')] + [(v.user_id, f"{ v.user.last_name }, { v.user.first_name }") for v in Volunteer.objects.filter(user__festival = festival).order_by('user__last_name', 'user__first_name')]


class AdminShiftForm(forms.ModelForm):

    class Meta:
        model = Shift
        fields = [
            'location', 
            'date', 'start_time', 'end_time',
            'commitment',
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
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': 'A shift with the same location, start date/time and role already exists',
            }
        }

    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival
        if self.instance.commitment or self.initial.get('commitment'):
            self.fields['commitment'].disabled = True
            self.fields['role'].disabled = True
            self.fields['needs_dbs'].disabled = True
            self.fields['volunteer_can_accept'].disabled = True
            self.fields['volunteer'].disabled = True
        else:
            self.fields['commitment'].queryset = Commitment.objects.filter(festival=festival)
            self.fields['role'].queryset = Role.objects.filter(festival=festival)
            self.fields['volunteer'].queryset = Volunteer.objects.filter(user__festival=festival).order_by('user__last_name', 'user__first_name')
        self.fields['location'].queryset = Location.objects.filter(festival=festival)
    

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

    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival
        for field in self.Meta.required:
            self.fields[field].required = True


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


    def __init__(self, festival, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.festival = festival
        self.fields['roles'].queryset = Role.objects.filter(festival=self.festival)


class AdminVolunteerForm(MultiModelForm):

    form_classes = OrderedDict((
        ('user', VolunteerUserForm),
        ('volunteer', VolunteerRolesForm),
    ))
