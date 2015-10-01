from __future__ import unicode_literals
import six
from django.template import defaultfilters
from django.conf import settings
from django.utils.encoding import force_text
from .functions import mark_safe, make_jsexpr, is_jsexpr
from . import datetimeformat


filter_translators = {}


def register(filter):
    def _decorator(translator):
        assert filter not in filter_translators
        filter_translators[filter] = translator
        return translator
    return _decorator


@register(defaultfilters.default)
def translate_filter_default(value, default):
    if is_jsexpr(value):
        return make_jsexpr('%s?%s:%s', value, value, default)
    elif value:
        return value
    else:
        return default


@register(defaultfilters.default_if_none)
def translate_filter_default_if_none(value, default):
    if is_jsexpr(value):
        return make_jsexpr('%s===null?%s:%s', value, default, value)
    elif value is not None:
        return value
    else:
        return default


@register(defaultfilters.length)
def translate_filter_length(value):
    return mark_safe(make_jsexpr('%s.length', value))


@register(defaultfilters.add)
def translate_filter_add(value, arg):
    if is_jsexpr(arg):
        return make_jsexpr('%s+%s', value, arg)
    else:
        try:
            newarg = int(arg)
        except (ValueError, TypeError):
            newarg = arg
        return make_jsexpr('%s+%s', value, newarg)


def translate_filter_date_or_time(value, arg):
    if is_jsexpr(arg):
        raise NotImplementedError(
            "Cannot translate date or time filters "
            "with variable format strings to Javascript"
        )
    format_string = six.text_type(arg)
    if format_string.endswith('_FORMAT'):
        format_string = six.text_type(getattr(settings, format_string))
    format_iterator = iter(format_string)
    parts = []
    for char in format_iterator:
        if char == '\\':
            char = six.next(format_iterator)
            parts.append(char)
        else:
            output = datetimeformat.get_datetime_format_javascript_expression(char)
            if output is None:
                parts.append(char)
            else:
                js = make_jsexpr(force_text(output), x=value)
                parts.append(mark_safe(make_jsexpr('(%s)', js)))
    return parts


@register(defaultfilters.date)
def translate_filter_date(value, arg=None):
    if not arg:
        arg = settings.DATE_FORMAT
    return translate_filter_date_or_time(value, arg)


@register(defaultfilters.time)
def translate_filter_time(value, arg=None):
    if not arg:
        arg = settings.TIME_FORMAT
    return translate_filter_date_or_time(value, arg)


@register(defaultfilters.floatformat)
def translate_filter_floatformat(value, arg=None):
    if is_jsexpr(arg):
        raise NotImplementedError(
            "Cannot translate floatformat filters "
            "with variable format strings to Javascript"
        )
    if arg is None:
        arg = -1
    else:
        arg = int(arg)
    if arg == 0:
        return mark_safe(make_jsexpr('Math.round(%s)', value))
    elif arg > 0:
        # exactly that many places
        return mark_safe(make_jsexpr('parseFloat(%s).toFixed(%s)', value, arg))
    else:
        # at most this many places, if needed
        return mark_safe(make_jsexpr(
            'Math.round(%%s*1%(x)s)/1%(x)s' % dict(x='0' * (-arg)),
            value,
        ))
