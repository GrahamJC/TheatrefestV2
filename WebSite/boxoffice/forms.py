from django import forms
from django.core.exceptions import ValidationError

from tickets.models import TicketType, Checkpoint


class CheckpointForm(forms.Form):

    cash = forms.DecimalField(label = 'Cash', required = True, max_digits = 5, decimal_places = 2)
    buttons = forms.IntegerField(label = 'Buttons', required = True)
    fringers = forms.IntegerField(label = 'Paper fringers', required = True)
    notes = forms.CharField(label = 'Notes', widget = forms.Textarea(attrs = { 'rows': 4 }), required = False)
