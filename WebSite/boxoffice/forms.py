from django import forms
from django.core.exceptions import ValidationError

from django_select2.forms import Select2MultipleWidget

from core.models import User
from core.widgets import ModelSelect2
from program.models import Show, ShowPerformance
from tickets.models import TicketType, Sale, Checkpoint


class SaleStartForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True, widget = forms.TextInput(attrs = { 'style': 'width: 100%' }))
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'


class RefundStartForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True, widget = forms.TextInput(attrs = { 'style': 'width: 100%' }))
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'
    reason = forms.CharField(label = 'Reason', required = False, widget = forms.Textarea(attrs = { 'style': 'width: 100%; height: 200px' }))


class SaleTicketsForm(forms.Form):

    def __init__(self, ticket_types, efringers, *args, **kwargs):
        self.ticket_types = ticket_types
        self.efringers = efringers
        super().__init__(*args, **kwargs)
        for tt in self.ticket_types:
            label = 'Paper fringer (use)' if tt.name == 'Fringer' else tt.name
            self.fields[self.ticket_field_name(tt)] = forms.IntegerField(label = label, required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
        if efringers:
            for ef in self.efringers:
                self.fields[self.efringer_field_name(ef)] = forms.BooleanField(label = ef.name, required = False, initial = False)

    @classmethod
    def ticket_field_name(cls, ticket_type):
        return f'Ticket_{ticket_type.name}'

    @classmethod
    def efringer_field_name(cls, efringer):
        return f'eFringer_{efringer.name}'

    @property
    def ticket_count(self):
        return (
            sum([self.cleaned_data[self.ticket_field_name(tt)] for tt in self.ticket_types])
            +
            sum([1 for ef in self.efringers if self.cleaned_data[self.efringer_field_name(ef)]])
        )


class SaleExtrasForm(forms.Form):

    buttons = forms.IntegerField(label = 'Badges', required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    fringers = forms.IntegerField(label = 'Paper fringers (buy)', required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))


class SaleEMailForm(forms.Form):

    email = forms.EmailField(label = 'e-mail address', required = True, widget = forms.TextInput(attrs = { 'style': 'width: 100%' }))


class CheckpointForm(forms.Form):

    cash = forms.DecimalField(label = 'Cash', required = True, max_digits = 5, decimal_places = 2, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    buttons = forms.IntegerField(label = 'Badges', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    fringers = forms.IntegerField(label = 'Fringers', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    notes = forms.CharField(label = 'Notes', required = False, widget = forms.Textarea(attrs = { 'style': 'width: 100%; height: 200px' }))

    def __init__(self, checkpoint, *args, **kwargs):
        if checkpoint:
            kwargs['initial'] = {
                'cash': checkpoint.cash,
                'buttons': checkpoint.buttons,
                'fringers': checkpoint.fringers,
                'notes': checkpoint.notes,
            }
        super().__init__(*args, **kwargs)
        if checkpoint:
            self.fields['cash'].disabled = True
            self.fields['buttons'].disabled = True
            self.fields['fringers'].disabled = True
