from __future__ import unicode_literals
import six
from django.utils.dates import (
    MONTHS, MONTHS_3, MONTHS_ALT, MONTHS_AP, WEEKDAYS, WEEKDAYS_ABBR,
)
from django.utils.functional import lazy
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _, ugettext

try:
    from django.utils.text import format_lazy
    def concat(*args):
        return format_lazy('{}' * len(args), *args)
except ImportError:
    # django < 1.11
    from django.utils.translation import string_concat as concat

# For reference:
# https://github.com/django/django/blob/master/django/utils/dateformat.py
# https://github.com/django/django/blob/master/django/utils/dates.py


def zero_padded(x, digits):
    return '"%(z)s".substr((%(x)s).toString().length)+%(x)s' % dict(
        z='0' * digits,
        x=x,
    )


def zero_padded_two_digit(x):
    return '%s<10?"0"+(%s):(%s)' % (x, x, x)


def array_index(array, index, cycle=False, capitalize=False):
    if isinstance(array, dict):
        array = [i[1] for i in sorted(array.items(), key=lambda x: x[0])]
    if cycle:
        last = array.pop()
        array.insert(0, last)
    if capitalize:
        array = [i.title() for i in array]
    return '[%s][%s]' % (','.join('"%s"' % i for i in array), index)
array_index = lazy(array_index, six.text_type)


datetime_format_javascript_expressions = dict(
    a=concat('%(x)s.getHours()<12?"', _('a.m.'), '":"', _('p.m.'), '"'),
    A=concat('%(x)s.getHours()<12?"', _('AM'), '":"', _('PM'), '"'),
    b=array_index(MONTHS_3, '%(x)s.getMonth()'),
    c=NotImplemented,  # TODO iso
    d=zero_padded_two_digit('%(x)s.getDate()'),
    D=array_index(WEEKDAYS_ABBR, '%(x)s.getDay()', cycle=True),
    e=NotImplemented,  # TODO timezone name
    E=array_index(MONTHS_ALT, '%(x)s.getMonth()'),
    f=(  # noqa
        '(%(x)s.getHours()%%12)'
        '+'
        '('
                '%(x)s.getMinutes()==0'
            '?'
                '""'
            ':'
                '('
                        '%(x)s.getMinutes()<10'
                    '?'
                        '":0"+%(x)s.getMinutes()'
                    ':'
                        '":"+%(x)s.getMinutes()'
                ')'
        ')'
    ),
    F=array_index(MONTHS, '%(x)s.getMonth()'),
    g='%(x)s.getHours()%%12',
    G='%(x)s.getHours()',
    h=zero_padded_two_digit('%(x)s.getHours()%%12'),
    H=zero_padded_two_digit('%(x)s.getHours()'),
    i=zero_padded_two_digit('%(x)s.getMinutes()'),
    I=NotImplemented,  # TODO daylight saving
    j='%(x)s.getDate()',
    l=array_index(WEEKDAYS, '%(x)s.getDay()', cycle=True),
    L=NotImplemented,  # TODO leepyear boolean
    m=zero_padded_two_digit('%(x)s.getMonth()+1'),
    M=array_index(MONTHS_3, '%(x)s.getMonth()', capitalize=True),
    n='%(x)s.getMonth()+1',
    N=array_index(MONTHS_AP.values(), '%(x)s.getMonth()'),
    o=NotImplemented,  # TODO year matching iso week number
    O=NotImplemented,  # TODO difference to GMT in hours
    # P = this expression is built below in build_formatchar_P()
    r=NotImplemented,  # TODO iso
    s=zero_padded_two_digit('%(x)s.getSeconds()'),
    S='(11<=%(x)s.getDate()&&%(x)s.getDate()<=13?"th":%(x)s.getDate()%%10==1?"st":(%(x)s.getDate()%%10==2?"nd":(%(x)s.getDate()%%10==3?"rd":"th")))',
    t=NotImplemented,  # TODO number of days in month
    T=NotImplemented,  # TODO timezone of this machine
    u=zero_padded('%(x)s.getMilliseconds()*1000', 6),
    U='Math.floor(%(x)s.getTime()/1000)',
    w='%(x)s.getDay()',
    W=NotImplemented,  # TODO iso week of year
    y=zero_padded_two_digit('%(x)s.getFullYear()%%100'),
    Y='%(x)s.getFullYear()',
    z=NotImplemented,  # TODO day of year
    Z=NotImplemented,  # TODO timezone offset in seconds
)


def build_formatchar_P():
    return ''.join(map(force_text, [  # noqa
        '(',
                '(%(x)s.getMinutes()==0&&%(x)s.getHours()==0)',
            '?',
                '"',
                ugettext('midnight'),
                '"',
            ':',
                '(',
                    '(%(x)s.getMinutes()==0&&%(x)s.getHours()==12)',
                '?',
                    '"',
                    ugettext('noon'),
                    '"',
                ':',
                    '(',
                    datetime_format_javascript_expressions['f'],
                    ')+" "+(',
                    datetime_format_javascript_expressions['a'],
                    ')',
                ')',
        ')',
    ]))
build_formatchar_P = lazy(build_formatchar_P, six.text_type)
datetime_format_javascript_expressions['P'] = build_formatchar_P()


def get_datetime_format_javascript_expression(char):
    try:
        expr = datetime_format_javascript_expressions[char]
    except KeyError:
        return None
    if expr is NotImplemented:
        raise NotImplementedError(
            "Datetime format character '%s' is not implemented yet" % char
        )
    else:
        return expr
