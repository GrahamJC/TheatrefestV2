from django.contrib.auth.forms import ReadOnlyPasswordHashField, PasswordResetForm as BasePasswordResetForm
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django import forms
from django.forms.utils import ErrorList, ErrorDict
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from six.moves import reduce
from collections import OrderedDict
from itertools import chain
from operator import add

from django_registration.forms import RegistrationForm as BaseRegistrationForm

from django_select2.forms import Select2MultipleWidget

from bootstrap_datepicker_plus.widgets import DatePickerInput, TimePickerInput

from core.models import Festival, User
from core.widgets import ModelSelect2


class AdminUserCreationForm(forms.ModelForm):

    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('festival', 'email', 'first_name', 'last_name')

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class AdminUserChangeForm(forms.ModelForm):

    password = ReadOnlyPasswordHashField(help_text='<a href="../password/">change password</a>')

    class Meta:
        model = User
        fields = (
            'email', 'password',
            'first_name', 'last_name',
            'is_active',
            'is_admin', 'is_boxoffice', 'is_venue', 'is_volunteer',
        )

    def clean_password(self):
        return self.initial['password']
        

class RegistrationForm(BaseRegistrationForm):

    def __init__(self, *args, **kwargs):
        self.festival = kwargs.pop('festival')
        super().__init__(*args, **kwargs)

    class Meta(BaseRegistrationForm.Meta):
        model = User
        fields = [
            User.get_email_field_name(),
            'password1',
            'password2'
        ]

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude)
        except ValidationError:
            self._update_errors(ValidationError({User.get_email_field_name(): 'A user with that e-mail already exists.'}))


class PasswordResetForm(BasePasswordResetForm):

    def __init__(self, *args, **kwargs):
        self.festival = kwargs.pop('festival')
        super().__init__(*args, **kwargs)

    def get_users(self, email):
        user = User.objects.get_by_natural_key(self.festival, email)
        return (user,)


class AdminFestivalForm(forms.ModelForm):

    class Meta:
        model = Festival
        fields = [
            'name',
            'title',
            'previous',
            'is_archived'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['previous'].queryset = Festival.objects.order_by('name')


class AdminUserAddForm(forms.Form):

    def __init__(self, festival, *args, **kwargs):

        # Call base class
        super().__init__(*args, **kwargs)

        # Restrict to current festival and non-admin users
        self.fields['user'] = forms.ModelChoiceField(
            queryset = User.objects.filter(festival=festival, is_admin=False),
            widget = ModelSelect2(
                url = 'core:admin_user_autocomplete',
                attrs = {
                    'data-theme': 'bootstrap4',
                }
            )
        )


class DebugForm(forms.Form):

    date = forms.DateField(required=False, widget=DatePickerInput)
    time = forms.TimeField(required=False, widget=TimePickerInput)

