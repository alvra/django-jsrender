from __future__ import unicode_literals
import datetime
import json
import six
from django.utils import html
from django.utils.safestring import SafeText


def as_javascript(value):
    "Translate a pure Python value to Javascript"
    return six.text_type(json.dumps(value))


def express(value):
    "Express a value (Javascript expression or other) in Javascript"
    if isinstance(value, JavascriptExpression):
        return value.expression
    elif isinstance(value, datetime.datetime):
        return 'new Date({y},{m},{d},{h},{min},{s},{milli})'.format(
            y=value.year,
            m=value.month - 1,
            d=value.day,
            h=value.hour,
            min=value.minute,
            s=value.second,
            milli=value.microsecond/1000,
        )
    else:
        return as_javascript(value)


def is_escaped(x):
    "Returns true if x was marked safe, i.e. that it doesn't need escaping"
    return isinstance(x, (SafeText, SafeJavascriptExpression))


def escape(escaper, x):
    "Takes Javascript and escapes it if needed."
    if is_escaped(x):
        return x
    elif isinstance(x, six.text_type):
        return html.conditional_escape(x)
    elif isinstance(x, JavascriptExpression):
        return mark_safe(make_jsexpr('%s(%%s)' % escaper, x))
    else:
        raise TypeError((x, type(x)))


def mark_safe(x):
    "Mark an object (Javascript expression or other) that doesn't need to be escaped"
    if is_escaped(x):
        return x
    elif isinstance(x, six.text_type):
        return SafeText(x)
    elif isinstance(x, JavascriptExpression):
        return SafeJavascriptExpression(x.expression)
    else:
        raise TypeError((x, type(x)))


def is_jsexpr(x):
    "Returns True if the argument is a Javascript expression"
    return isinstance(x, JavascriptExpression)


def make_jsexpr(template, *args, **kwargs):
    "Build a javascript expression from a template and substitutions."
    assert isinstance(template, six.text_type), "Not text %r" % text
    assert not (args and kwargs), "Both args and kwargs given %r %r" % (args, kwargs)
    cls = JavascriptExpression
    if args:
        return cls(template % tuple(express(v) for v in args))
    elif kwargs:
        return cls(template % dict((k, express(v)) for k, v in kwargs.items()))
    else:
        return cls(template)


def concatenate(escaper, parts):
    "Build a new Javascript expression by concatenating expressions and text."
    # shortcuts
    parts = list(parts)
    if len(parts) == 0:
        return ''
    elif len(parts) == 1:
        return parts[0]
    temp = ['']
    contains_escaped_parts = False
    # collapse adjecent text and safetext
    for part in parts:
        if isinstance(part, SafeText):
            if part != '':
                contains_escaped_parts = True
                if isinstance(temp[-1], SafeText):
                    # concat two safetexts
                    temp[-1] += part
                elif isinstance(temp[-1], six.text_type):
                    # concat text with safetext
                    temp[-1] = SafeText(html.conditional_escape(temp[-1]) + part)
                else:
                    # nothing to concat
                    temp.append(part)
        elif isinstance(part, six.text_type):
            if part != '':
                if isinstance(temp[-1], SafeText):
                    # concat safetext with text
                    temp[-1] = SafeText(temp[-1] + html.conditional_escape(part))
                elif isinstance(temp[-1], six.text_type):
                    # concat two texts
                    temp[-1] += part
                else:
                    # nothing to concat
                    temp.append(part)
        elif isinstance(part, SafeJavascriptExpression):
            contains_escaped_parts = True
            temp.append(part)
        elif isinstance(part, JavascriptExpression):
            temp.append(part)
        else:
            raise TypeError(part, type(part))
    # shortcuts
    if len(temp) == 1:
        return temp[0]
    # remove possible empty text from start
    if temp[0] == '':
        temp.pop(0)
    # escape everything if any part was safe
    if contains_escaped_parts:
        temp = map(lambda p: escape(escaper, p), temp)
    # join everything together
    cls = SafeJavascriptExpression if contains_escaped_parts else JavascriptExpression
    return cls('+'.join(map(express, temp)))


def is_attributable(field):
    "Returns True if obj.<field> is valid Javascript, or False if obj['<field>'] should be used."
    if ' ' in field:
        return False
    elif "'" in field or '"' in field:
        return False
    elif '[' in field or ']' in field:
        return False
    elif '.' in field:
        return False
    else:
        return True


def isalpha_or_underscore(string):
    return all(c.isalpha() or c == '_' for c in string)


def isalnum_or_underscore(string):
    return all(c.isalnum() or c == '_' for c in string)


def js_is_variable(expr):
    "Returns True if the given Javascript is a valid variable name."
    return isalpha_or_underscore(expr[0]) and isalnum_or_underscore(expr[1:])


class JavascriptExpression(object):
    """A Javascript expression

    Don't use this class directly, always build Javascript
    with the helper functions `make_jsexpr` and `concaternate`.
    """

    def __init__(self, expression):
        assert isinstance(expression, six.text_type), "Not text %r" % expression
        if expression == '':
            raise ValueError(expression)
        self.expression = expression

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.expression)

    def __eq__(self, other):
        return type(self) is type(other) and self.expression == other.expression

    def __ne__(self, other):
        return type(self) is not type(other) or self.expression != other.expression

    def __getitem__(self, key):
        assert '.' not in key
        if is_attributable(key):
            if js_is_variable(self.expression):
                return make_jsexpr('%%s.%s' % key, self)
            else:
                return make_jsexpr('(%%s).%s' % key, self)
        else:
            if js_is_variable(self.expression):
                return make_jsexpr('%s[%s]', self, key)
            else:
                return make_jsexpr('(%s)[%s]', self, key)


class SafeJavascriptExpression(JavascriptExpression):
    "A Javascript expression type that doesn't need to be escaped."
