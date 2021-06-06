from django.core.exceptions import ValidationError
from django import forms

from program.models import Show, ShowPerformance
from .models import Fringer


class BuyTicketForm(forms.Form):
    
    id = forms.IntegerField(widget = forms.HiddenInput())
    name = forms.CharField(widget = forms.HiddenInput(), required = False)
    price = forms.DecimalField(widget = forms.HiddenInput(), required = False)
    quantity = forms.IntegerField()


class RenameFringerForm(forms.ModelForm):

    class Meta:
        model = Fringer
        fields = ('name',)

    def validate_unique(self):
        # Because 'user' is not included in the form it is normally excluded from
        # validation checks but we need to add it back for the uniqueness check
        exclude = self._get_validation_exclusions()
        exclude.remove('user')
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            self.add_error('name', 'Name already used')


class BuyFringerForm(forms.Form):

    def __init__(self, user, fringer_types, *args, **kwargs):

        #Call base constructor
        super(BuyFringerForm, self).__init__(*args, **kwargs)

        # Save user
        self.user = user

        # Create fringer type choices
        fringer_choices = [(t.id, "{0} shows for £{1:0.2}".format(t.shows, t.price)) for t in fringer_types]

        # Add fields
        self.fields['type'] = forms.ChoiceField(label = "Type", choices = fringer_choices, initial = [fringer_choices[0][0]])
        self.fields['name'] = forms.CharField(label = "Name", max_length = 32, required = False, help_text = "Keep track of your eFringer Vouchers by giving each a name.")

    def clean_name(self):
        name = self.cleaned_data['name']
        if Fringer.objects.filter(user = self.user, name = name).exists():
            raise forms.ValidationError("Name has already been used")
        return name

class DonationsForm(forms.Form):

    amount = forms.TypedChoiceField(
        label = 'Amount',
        choices = (
            (1, '£1'),
            (2, '£2'),
            (5, '£5'),
            (10, '£10'),
            (20, '£25'),
        ),
        coerce = lambda x: int(x),
        widget = forms.RadioSelect,
        initial = '1',
        required = True,
    )
    email = forms.CharField(
        label = 'e-mail',
        required = True,
    )
