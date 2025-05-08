from django import forms
from django.core.exceptions import ValidationError

from .models import Page, PageImage, Navigator, Image, Document, Resource


class AdminPageForm(forms.ModelForm):

    class Meta:
        model = Page
        fields = [
            'name',
            'title', 'body', 'body_test',
        ]
        labels = {
            'body': '',
            'body_test': '',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A page with that name already exists'}))


class AdminPageImageForm(forms.ModelForm):

    class Meta:
        model = PageImage
        fields = [
            'name',
            'image',
        ]

    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except ValidationError:
            self._update_errors(ValidationError({'name': 'An image with that name already exists for this page'}))


class AdminNavigatorForm(forms.ModelForm):

    class Meta:
        model = Navigator
        fields = [
            'seqno', 'label',
            'type', 'url', 'page',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['page'].queryset = Page.objects.filter(festival=self.instance.festival)

    # Same check - different error message (to avoid mention of festival)
    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except Exception as e: #ValidationError:
            if self.instance.parent:
               self._update_errors(ValidationError({'label': 'An item with that label already exists in this navigator'}))
            else:
                self._update_errors(ValidationError({'label': 'An navigator with that label already exists'}))

class AdminImageForm(forms.ModelForm):

    class Meta:
        model = Image
        fields = [
            'name',
            'image',
            'map',
        ]

    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except ValidationError:
            self._update_errors(ValidationError({'name': 'An image with that name already exists'}))


class AdminDocumentForm(forms.ModelForm):

    class Meta:
        model = Document
        fields = [
            'name',
            'file', 'filename',
        ]

    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A document with that name already exists'}))


class AdminResourceForm(forms.ModelForm):

    class Meta:
        model = Resource
        fields = [
            'name',
            'type',
            'body', 'body_test',
        ]

    def validate_unique(self):
        super().validate_unique()
        try:
            self.instance.validate_constraints()
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A resource with that name already exists'}))
