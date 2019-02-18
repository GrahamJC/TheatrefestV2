from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms

from django_registration.forms import RegistrationForm as BaseRegistrationForm

from core.models import User


class UserCreationForm(forms.ModelForm):

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


class UserChangeForm(forms.ModelForm):

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
        super().__init__(*args, **kwargs)
        self.fields['festival'].widget = forms.HiddenInput()

    class Meta(BaseRegistrationForm.Meta):
        model = User
        fields = [
            'festival',
            User.get_email_field_name(),
            'password1',
            'password2'
        ]
