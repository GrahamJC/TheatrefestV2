from django import forms
from django import template

register = template.Library()

@register.filter
def lookup(dict, key):
    return dict.get(key, '')
