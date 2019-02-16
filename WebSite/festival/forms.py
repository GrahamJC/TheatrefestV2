from django import forms
from django.core.exceptions import ValidationError

from core.models import User
from content.models import Page, PageImage, Navigator

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
