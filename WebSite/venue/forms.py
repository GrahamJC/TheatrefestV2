from django import forms
from django.core.exceptions import ValidationError

from tickets.models import TicketType, Checkpoint


class OpenCheckpointForm(forms.Form):

    cash = forms.DecimalField(label = 'Cash', required = True, max_digits = 5, decimal_places = 2)
    buttons = forms.IntegerField(label = 'Buttons', required = True)
    fringers = forms.IntegerField(label = 'Fringers', required = True)
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'rows': 4 }), required = False)

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


class CloseCheckpointForm(forms.Form):

    cash = forms.DecimalField(label = 'Cash', required = True, max_digits = 5, decimal_places = 2)
    buttons = forms.IntegerField(label = 'Buttons', required = True)
    fringers = forms.IntegerField(label = 'Fringers', required = True)
    audience = forms.IntegerField(label = 'Audience', required = True)
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'rows': 4 }), required = False)

    def __init__(self, checkpoint, *args, **kwargs):
        if checkpoint:
            kwargs['initial'] = {
                'cash': checkpoint.cash,
                'buttons': checkpoint.buttons,
                'fringers': checkpoint.fringers,
                'audience': checkpoint.close_performance.audience,
                'notes': checkpoint.notes,
            }
        super().__init__(*args, **kwargs)
        if checkpoint:
            self.fields['cash'].disabled = True
            self.fields['buttons'].disabled = True
            self.fields['fringers'].disabled = True


class SaleStartForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True)
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'


class SaleForm(forms.Form):

    buttons = forms.IntegerField(label = 'Buttons', required = True, initial = 0, min_value = 0)
    fringers = forms.IntegerField(label = 'Paper fringers', required = True, initial = 0, min_value = 0)
    volunteer = forms.BooleanField(label = 'Use volunteer ticket', required = False, initial = False)

    def __init__(self, ticket_types, efringers, *args, **kwargs):
        self.ticket_types = ticket_types
        self.efringers = efringers
        super().__init__(*args, **kwargs)
        for tt in self.ticket_types:
            self.fields[self.ticket_field_name(tt)] = forms.IntegerField(label = tt.name, required = True, initial = 0, min_value = 0)
        if efringers:
            for ef in self.efringers:
                self.fields[self.efringer_field_name(ef)] = forms.BooleanField(label = f"{ef.name} ({ef.available} remaining)", required = False, initial = False)
                
    @classmethod
    def ticket_field_name(cls, ticket_type):
        return f'ticket_{ticket_type.id}'

    @classmethod
    def efringer_field_name(cls, efringer):
        return f'eFringer_{efringer.id}'

    @property
    def ticket_count(self):
        return (
            sum([self.cleaned_data[self.ticket_field_name(tt)] for tt in self.ticket_types])
            +
            sum([1 for ef in self.efringers if self.cleaned_data[self.efringer_field_name(ef)]])
            +
            1 if self.cleaned_data['volunteer'] else 0
        )
