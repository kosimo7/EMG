from django import template
from django.template.defaultfilters import register
register = template.Library()

# Cusom Filter returning dict value from given key for use within django templates
@register.filter(name='dict_key')
def dict_key(d, k):
    '''Returns the given key from a dictionary.'''
    return d.get(k)

@register.simple_tag()
def multiply(a, b, *args, **kwargs):
    # simple tag to multiply variables within templates
    return a * b

@register.simple_tag()
def divide(a, b, *args, **kwargs):
    # simple tag to divide variables within templates
    return a / b

@register.simple_tag()
def subtract(a, b, *args, **kwargs):
    # simple tag to subtract variables within templates
    return a - b