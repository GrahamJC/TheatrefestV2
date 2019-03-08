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
            self._update_errors(ValidationError({'name': 'A page with that name already exists'}))


class AdminPageImageForm(forms.ModelForm):

    class Meta:
        model = PageImage
        fields = [
            'name',
            'image',
        ]

    def __init__(self, page, *args, **kwargs):
        self.page = page
        super().__init__(*args, **kwargs)

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('page')
        self.instance.page = self.page
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'An image with that name already exists'}))


class AdminNavigatorForm(forms.ModelForm):

    class Meta:
        model = Navigator
        fields = [
            'seqno', 'label',
            'type', 'url', 'page',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)
        self.fields['page'].queryset = Page.objects.filter(festival=festival)

    # Same check - different error message (to avoid mention of festival)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A navigator with that name already exists'}))


class AdminImageForm(forms.ModelForm):

    class Meta:
        model = Image
        fields = [
            'name',
            'image',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of festival)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            self._update_errors(ValidationError({'name': 'A image with that name already exists'}))


class AdminDocumentForm(forms.ModelForm):

    class Meta:
        model = Document
        fields = [
            'name',
            'file', 'filename',
        ]

    def __init__(self, festival, *args, **kwargs):
        self.festival = festival
        super().__init__(*args, **kwargs)

    # Same check - different error message (to avoid mention of festival)
    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        exclude.remove('festival')
        self.instance.festival = self.festival
        try:
            self.instance.validate_unique(exclude=exclude)
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
            self._update_errors(ValidationError({'name': 'A resource with that name already exists'}))
