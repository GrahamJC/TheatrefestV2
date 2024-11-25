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

from bootstrap_datepicker_plus.widgets import DatePickerInput, TimePickerInput

from core.models import Festival, User


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


class MultiForm():

    form_classes = {}

    def __init__(self, data=None, files=None, *args, **kwargs):

        # Some things expect these to exist
        self.data = {} if data is None else data
        self.files = {} if files is None else files

        # Get initial values dictionary and initialize other stuff
        self.initial = kwargs.pop('initial', None) or {}
        self.forms = OrderedDict()
        self._errors = None

        # Create forms
        for form_name, form_class in self.form_classes.items():
            form_args, form_kwargs = self.get_form_args_kwargs(form_name, args, kwargs)
            self.forms[form_name] = form_class(data=data, files=files, *form_args, **form_kwargs)

    def get_form_args_kwargs(self, form_name, args, kwargs):

        # Copy keyword arguments and add/update prefix and initial values
        form_kwargs = kwargs.copy()
        form_kwargs.update(
            initial = self.initial.get(form_name),
            prefix = form_name
        )
        return args, form_kwargs

    def __str__(self):
        return self.as_table()

    @cached_property
    def fields(self):
        fields = OrderedDict()
        for form_name, form in self.forms.items():
            for field_name, field in form.fields.items():
                fields[form.add_prefix(field_name)] = field
        return fields

    def __getitem__(self, name):

        # Get prefix
        form_name, field_name = name.split('-', 1)
        try:
            form = self.forms[form_name]
            return form[field_name]
        except KeyError:
            raise KeyError(f"Form '{form_name}' not found in '{self.__class__.__name__}'. Choices are: {', '.join(sorted(f for f in self.forms))}.")

    def __iter__(self):
        for name in self.fields:
            yield self[name]

    @cached_property
    def errors(self):
        errors = ErrorDict()
        for form_name, form in self.forms.items():
            for field_name, error in form.errors.items():
                errors[form.add_prefix(field_name)] = error
        return errors

    @cached_property
    def non_field_errors(self):
        errors = ErrorList()
        for form in self.forms.values():
            for error in form.non_field_errors():
                errors.append(error)
        return errors

    @property
    def is_bound(self):
        return any(form.is_bound for form in self.forms.values())

    def clean(self):
        return self.cleaned_data

    @cached_property
    def cleaned_data(self):
        cleaned_data = {}
        for form_name, form in self.forms.items():
            for field_name, data in form.cleaned_data.items():
                cleaned_data[form.add_prefix(field_name)] = data
        return cleaned_data

    def full_clean(self):
        for form in self.forms.values():
            form.full_clean()

    def is_valid(self):
        return all(form.is_valid() for form in self.forms.values())

    def as_table(self):
        return mark_safe(''.join(form.as_table() for form in self.forms.values()))

    def as_ul(self):
        return mark_safe(''.join(form.as_ul() for form in self.forms.values()))

    def as_p(self):
        return mark_safe(''.join(form.as_p() for form in self.forms.values()))

    def is_multipart(self):
        return any(form.is_multipart() for form in self.forms.values())

    @property
    def media(self):
        return reduce(add, (form.media for form in self.forms.values()))

    def hidden_fields(self):
        return [field for field in self if field.is_hidden]

    def visible_fields(self):
        return [field for field in self if not field.is_hidden]


class MultiModelForm(MultiForm):

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        if self.instance is None:
            self.instance = {}
        super().__init__(*args, **kwargs)


    def get_form_args_kwargs(self, form_name, args, kwargs):
        fargs, fkwargs = super().get_form_args_kwargs(form_name, args, kwargs)
        try:
            # If we only pass instance when there was one specified, we make it
            # possible to use non-ModelForms together with ModelForms.
            fkwargs['instance'] = self.instance[form_name]
        except KeyError:
            pass
        return fargs, fkwargs

    def save(self, commit=True):
        objects = OrderedDict( (key, form.save(commit)) for key, form in self.forms.items())

        if any(hasattr(form, 'save_m2m') for form in self.forms.values()):
            def save_m2m():
                for form in self.forms.values():
                    if hasattr(form, 'save_m2m'):
                        form.save_m2m()
            self.save_m2m = save_m2m

        return objects


class DebugForm(forms.Form):

    festival = forms.ModelChoiceField(required=False, queryset=Festival.objects.all())
    date = forms.DateField(required=False, widget=DatePickerInput)
    time = forms.TimeField(required=False, widget=TimePickerInput)

