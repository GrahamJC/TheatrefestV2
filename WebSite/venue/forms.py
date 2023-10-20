from django import forms
from django.core.exceptions import ValidationError

from tickets.models import TicketType, Checkpoint


class OpenCheckpointForm(forms.Form):

    buttons = forms.IntegerField(label = 'Badges', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    fringers = forms.IntegerField(label = 'Fringers', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'style': 'width:100%; height: 200px' }), required = False)

    def __init__(self, checkpoint, *args, **kwargs):
        if checkpoint:
            kwargs['initial'] = {
                'buttons': checkpoint.buttons,
                'fringers': checkpoint.fringers,
                'notes': checkpoint.notes,
            }
        super().__init__(*args, **kwargs)
        if checkpoint:
            self.fields['buttons'].disabled = True
            self.fields['fringers'].disabled = True


class SaleItemsForm(forms.Form):

    buttons = forms.IntegerField(label = 'Badges', required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    fringers = forms.IntegerField(label = 'Paper fringers (buy)', required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    volunteer = forms.BooleanField(label = 'Use volunteer ticket', required = False, initial = False)

    def __init__(self, ticket_types, *args, **kwargs):
        self.ticket_types = ticket_types
        super().__init__(*args, **kwargs)
        for tt in self.ticket_types:
            label = 'Paper fringer (use)' if tt.name == 'Fringer' else tt.name
            self.fields[self.ticket_field_name(tt)] = forms.IntegerField(label = label, required = True, initial = 0, min_value = 0, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
                
    @classmethod
    def ticket_field_name(cls, ticket_type):
        return f'ticket_{ticket_type.id}'

    @property
    def ticket_count(self):
        return (
            sum([self.cleaned_data[self.ticket_field_name(tt)] for tt in self.ticket_types])
        )


class SaleForm(forms.Form):

    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'style': 'width: 100%; height: 100px' }), required = False)

    def __init__(self, sale, *args, **kwargs):
        if sale:
            kwargs['initial'] = {
                'notes': sale.notes,
            }
        super().__init__(*args, **kwargs)

class CloseCheckpointForm(forms.Form):

    buttons = forms.IntegerField(label = 'Badges', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    fringers = forms.IntegerField(label = 'Fringers', required = True, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    audience = forms.IntegerField(label = 'Audience', required = False, widget = forms.NumberInput(attrs = { 'style': 'width: 75px' }))
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'style': 'width: 100%; height: 200px' }), required = False)

    def __init__(self, checkpoint, *args, **kwargs):
        if checkpoint:
            kwargs['initial'] = {
                'buttons': checkpoint.buttons,
                'fringers': checkpoint.fringers,
                'audience': checkpoint.close_performance.audience,
                'notes': checkpoint.notes,
            }
        super().__init__(*args, **kwargs)
        if checkpoint:
            self.fields['buttons'].disabled = True
            self.fields['fringers'].disabled = True
