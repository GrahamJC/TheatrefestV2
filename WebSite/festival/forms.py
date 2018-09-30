from django import forms
from django.core.exceptions import ValidationError

from .models import ContentPage, ContentPageImage


class ContentPageForm(forms.ModelForm):

    class Meta:
        model = ContentPage
        fields = ('festival', 'name', 'title', 'body')
        widgets = {
            'festival': forms.HiddenInput(),
        }

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(ValidationError({'name': 'A page with that name already exists'}))


class ContentPageImageForm(forms.ModelForm):

    class Meta:
        model = ContentPageImage
        fields = ('page', 'name', 'image')

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self._update_errors(ValidationError({'name': 'An image with that name already exists'}))
