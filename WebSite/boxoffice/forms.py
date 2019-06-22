from django import forms
from django.core.exceptions import ValidationError

from program.models import Show, ShowPerformance
from tickets.models import TicketType, Sale, Checkpoint


class SaleStartForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True)
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'


class SaleTicketsForm(forms.Form):

    def __init__(self, ticket_types, efringers, *args, **kwargs):
        self.ticket_types = ticket_types
        self.efringers = efringers
        super().__init__(*args, **kwargs)
        for tt in self.ticket_types:
            self.fields[self.ticket_field_name(tt)] = forms.IntegerField(label = tt.name, required = True, initial = 0, min_value = 0)
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

    buttons = forms.IntegerField(label = 'Buttons', required = True, initial = 0, min_value = 0)
    fringers = forms.IntegerField(label = 'Fringers', required = True, initial = 0, min_value = 0)


class RefundStartForm(forms.Form):

    customer = forms.CharField(label = 'Customer', required = True)
    customer.widget.attrs['placeholder'] = '-- Enter customer name or e-mail --'


class RefundTicketForm(forms.Form):

    ticket_no = forms.IntegerField(label = 'Number')


class RefundForm(forms.Form):

    amount = forms.DecimalField(label = 'Refund', required = True, min_value = 0, max_digits = 5, decimal_places = 2)
    reason = forms.CharField(label = 'Reason', required = True, widget = forms.Textarea())


class CheckpointForm(forms.Form):

    cash = forms.DecimalField(label = 'Cash', required = True, max_digits = 5, decimal_places = 2)
    buttons = forms.IntegerField(label = 'Buttons', required = True)
    fringers = forms.IntegerField(label = 'Fringers', required = True)
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'rows': 4 }), required = False)
