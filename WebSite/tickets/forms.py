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


class CustomerForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True, max_length = 64)
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'


class SaleTicketsForm(forms.Form):

    show = forms.ModelChoiceField(Show.objects.none(), to_field_name = 'uuid', label = "Show", empty_label = '-- Select show --')
    performance = forms.ModelChoiceField(ShowPerformance.objects.none(), to_field_name = 'uuid', label = "Performance", empty_label = '-- Select performance --')

    def __init__(self, shows, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['show'].queryset = shows
        self.fields['performance'].queryset = ShowPerformance.objects.none()
        if 'show' in self.data:
            try:
                show_uuid = self.data.get('show')
                self.fields['performance'].queryset = ShowPerformance.objects.filter(show__uuid = show_uuid)
            except:
                pass


class SaleTicketSubForm(forms.Form):

    type_id = forms.IntegerField(widget = forms.HiddenInput())
    name = forms.CharField(widget = forms.HiddenInput())
    price = forms.DecimalField(widget = forms.HiddenInput())
    quantity = forms.IntegerField(required = False, min_value = 0)

    def clean_quantity(self):
        value = self.cleaned_data['quantity']
        return value or 0


class SaleFringerSubForm(forms.Form):

    performance = None
    fringer_id = forms.IntegerField(widget = forms.HiddenInput())
    name = forms.CharField(widget = forms.HiddenInput())
    buy = forms.BooleanField(required = False)

    def clean_buy(self):
        buy = self.cleaned_data['buy']
        if buy:
            try:
                fringer = Fringer.objects.get(pk = self.cleaned_data['fringer_id'])
                if not fringer.is_available(self.performance):
                    raise forms.ValidationError('Already used for this performance')
            except Fringer.DoesNotExist:
                raise forms.ValidationError('Not found')
        return buy


class SaleExtrasForm(forms.Form):

    buttons = forms.IntegerField(label = 'Buttons', required = False, min_value = 0)
    fringers = forms.IntegerField(label = 'Frequent fringers', required = False, min_value = 0)

    def clean_buttons(self):
        value = self.cleaned_data['buttons']
        return value or 0

    def clean_fringers(self):
        value = self.cleaned_data['fringers']
        return value or 0


class RefundTicketForm(forms.Form):

    ticket_no = forms.IntegerField(label = 'Number')


class RefundForm(forms.Form):

    amount = forms.DecimalField(label = 'Refund', min_value = 0, max_digits = 5, decimal_places = 2)
    reason = forms.CharField(label = 'Reason', widget = forms.Textarea())
