from django import template

register = template.Library()

@register.filter(name='replace')
def replace_filter(value, arg):
    """
    Replaces all occurrences of the first part of arg with the second part of arg in the given string.
    Argument 'arg' should be a string in the format "old,new".
    Example: {{ some_string|replace:"_, " }}
    """
    if not isinstance(value, str):
        value = str(value) # Ensure value is a string
        
    if isinstance(arg, str) and ',' in arg:
        old_char, new_char = arg.split(',', 1)
        return value.replace(old_char, new_char)
    return value

@register.filter(name='getattr')
def getattr_filter(obj, attr_name):
    """
    Gets an attribute from an object. Returns None if attribute doesn't exist.
    Usage: {{ my_object|getattr:"attribute_name" }}
    """
    return getattr(obj, attr_name, None)
