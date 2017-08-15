from __future__ import unicode_literals
import math
from django.utils.timezone import now
from ..datetimeformat import datetime_format_javascript_expressions
from .utils import (
    JavascriptTranslationTestCase,
    falsy_values, truthy_expressable_values, falsy_expressable_values,
)


class FilterTests(JavascriptTranslationTestCase):
    def test_add(self):
        self.assertTranslation(
            '{{ spam|add:"2" }}',
            dict(spam=3),
            {},
        )
        self.assertTranslation(
            '{{ spam|add:"2" }}',
            {},
            dict(spam=3),
        )

    def test_add_variable(self):
        self.assertTranslation(
            '{{ spam|add:ham }}',
            dict(spam=3),
            dict(ham=4),
            '7',
        )
        self.assertTranslation(
            '{{ spam|add:ham }}',
            dict(spam=3, ham=4),
            {},
            '7',
        )
        self.assertTranslation(
            '{{ spam|add:ham }}',
            {},
            dict(spam=3, ham=4),
            '7',
        )

    def test_length(self):
        self.assertTranslation(
            '{{ spam|length }}',
            dict(spam=list(range(10))),
            {},
        )
        self.assertTranslation(
            '{{ spam|length }}',
            {},
            dict(spam=list(range(10))),
        )

    def test_length_add(self):
        self.assertTranslation(
            '{{ spam|length|add:"2" }}',
            dict(spam=list(range(10))),
            {},
        )
        self.assertTranslation(
            '{{ spam|length|add:"2" }}',
            {},
            dict(spam=list(range(10))),
        )

    def test_date(self):
        formatchars = [
            c for c, e
            in datetime_format_javascript_expressions.items()
            if e is not NotImplemented
        ]
        date = now()
        # trucate microseconds since Javascript isn't that precise
        date = date.replace(microsecond=(date.microsecond // 1000) * 1000)
        for formatchar in formatchars:
            with self.subTest(formatchar=formatchar):
                self.assertTranslation(
                    '{{ someday|date:"' + formatchar + '" }}',
                    dict(someday=date),
                    {},
                )
                self.assertTranslation(
                    '{{ someday|date:"' + formatchar + '" }}',
                    {},
                    dict(someday=date),
                )

    def test_date_formatchar_P(self):
        date = now().replace(hour=0, minute=0)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            dict(someday=date),
            {},
            'midnight',
        )
        date = now().replace(hour=12, minute=0)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            {},
            dict(someday=date),
            'noon',
        )
        date = now().replace(hour=6, minute=0)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            {},
            dict(someday=date),
            '6 a.m.',
        )
        date = now().replace(hour=18, minute=0)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            {},
            dict(someday=date),
            '6 p.m.',
        )
        date = now().replace(hour=6, minute=11)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            {},
            dict(someday=date),
            '6:11 a.m.',
        )
        date = now().replace(hour=18, minute=11)
        self.assertTranslation(
            '{{ someday|date:"P" }}',
            {},
            dict(someday=date),
            '6:11 p.m.',
        )

    def test_date_noargs(self):
        self.assertTranslation(
            '{{ someday|date }}',
            dict(someday=now()),
            {},
        )
        self.assertTranslation(
            '{{ someday|date }}',
            {},
            dict(someday=now()),
        )

    def test_date_setting_arg(self):
        settings_formats = [
            'DATE_FORMAT',
            'SHORT_DATE_FORMAT',
            'DATETIME_FORMAT',
            'SHORT_DATETIME_FORMAT',
        ]
        for setting_format in settings_formats:
            with self.subTest(setting_format=setting_format):
                self.assertTranslation(
                    '{{ someday|date:"' + setting_format + '" }}',
                    dict(someday=now()),
                    {},
                )
                self.assertTranslation(
                    '{{ someday|date:"' + setting_format + '" }}',
                    {},
                    dict(someday=now()),
                )

    def test_time_noargs(self):
        self.assertTranslation(
            '{{ someday|time }}',
            dict(someday=now()),
            {},
        )
        self.assertTranslation(
            '{{ someday|time }}',
            {},
            dict(someday=now()),
        )

    def test_time_setting_arg(self):
        settings_formats = [
            'TIME_FORMAT',
        ]
        for setting_format in settings_formats:
            with self.subTest(setting_format=setting_format):
                self.assertTranslation(
                    '{{ someday|time:"' + setting_format + '" }}',
                    dict(someday=now()),
                    {},
                )
                self.assertTranslation(
                    '{{ someday|time:"' + setting_format + '" }}',
                    {},
                    dict(someday=now()),
                )

    def test_date_escaping(self):
        self.assertTranslation(
            '{{ someday|date:">" }}',
            dict(someday=now()),
            {},
            "&gt;"
        )
        self.assertTranslation(
            '{{ someday|date:">" }}',
            {},
            dict(someday=now()),
            "&gt;"
        )

    def test_date_with_variable_format(self):
        self.assertTranslation(
            '{{ someday|date:fmt }}',
            dict(fmt='Y', someday=now()),
            {},
        )
        self.assertTranslation(
            '{{ someday|date:fmt }}',
            dict(fmt='Y'),
            dict(someday=now()),
        )

    def test_default(self):
        # truthy value, literal argument
        for value in truthy_expressable_values:
            for context, tplargs in self.mix_variables(value=value):
                self.assertTranslation(
                    '{{ value|default:"empty" }}',
                    context,
                    tplargs,
                )
        # truthy value, variable argument
        for value in truthy_expressable_values:
            for context, tplargs in self.mix_variables(value=value, other='abc'):
                self.assertTranslation(
                    '{{ value|default:other }}',
                    context,
                    tplargs,
                )
        # falsy value, literal argument
        for value in falsy_values:
            for context, tplargs in self.mix_variables(value=value):
                self.assertTranslation(
                    '{{ value|default:"empty" }}',
                    context,
                    tplargs,
                    "empty"
                )
        # falsy value, variable argument
        for value in falsy_values:
            for context, tplargs in self.mix_variables(value=value, other='abc'):
                self.assertTranslation(
                    '{{ value|default:other }}',
                    context,
                    tplargs,
                    'abc'
                )

    def test_default_if_none(self):
        # truthy value, literal argument
        for value in truthy_expressable_values:
            for context, tplargs in self.mix_variables(value=value):
                self.assertTranslation(
                    '{{ value|default_if_none:"empty" }}',
                    context,
                    tplargs,
                )
        # truthy value, variable argument
        for value in truthy_expressable_values:
            for context, tplargs in self.mix_variables(value=value, other='abc'):
                self.assertTranslation(
                    '{{ value|default_if_none:other }}',
                    context,
                    tplargs,
                )
        # falsy value, literal argument
        for value in falsy_expressable_values:
            for context, tplargs in self.mix_variables(value=value):
                self.assertTranslation(
                    '{{ value|default_if_none:"empty" }}',
                    context,
                    tplargs,
                )
        # falsy value, variable argument
        for value in falsy_expressable_values:
            for context, tplargs in self.mix_variables(value=value, other='abc'):
                self.assertTranslation(
                    '{{ value|default_if_none:other }}',
                    context,
                    tplargs,
                )
        # None value, literal argument
        for context, tplargs in self.mix_variables(value=None):
            self.assertTranslation(
                '{{ value|default_if_none:"empty" }}',
                context,
                tplargs,
            )
        # None value, variable argument
        for context, tplargs in self.mix_variables(value=None, other='abc'):
            self.assertTranslation(
                '{{ value|default_if_none:other }}',
                context,
                tplargs,
            )

    def test_floatformat(self):
        for digits in [None, 0, -1, 1]:
            with self.subTest(digits=digits):
                tpl = (
                    '{{ number|floatformat }}'
                    if digits is None else
                    '{{ number|floatformat:"%s" }}' % digits
                )
                self.assertTranslation(
                    tpl,
                    dict(number=math.pi * 100),
                    {},
                )
                self.assertTranslation(
                    tpl,
                    {},
                    dict(number=math.pi * 100),
                )

    def test_floatformat_with_variable_format(self):
        # NOTE Django does not support passing None in a format string variable
        for digits in [0, -1, 1]:
            with self.subTest(digits=digits):
                self.assertTranslation(
                    '{{ number|floatformat:fmt }}',
                    dict(fmt=digits, number=math.pi * 100),
                    {},
                )
                self.assertTranslation(
                    '{{ number|floatformat:fmt }}',
                    dict(fmt=digits),
                    dict(number=math.pi * 100),
                )
