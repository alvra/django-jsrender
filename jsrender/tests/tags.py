from __future__ import unicode_literals
import unittest
import itertools
from ..datetimeformat import datetime_format_javascript_expressions
from .utils import (
    truthy_values, falsy_values,
    JavascriptTranslationTestCase,
    template_from_string,
)

try:
    from unittest import mock
except ImportError:
    # python < 3.3
    import mock  # pip install mock


class TagTests(JavascriptTranslationTestCase):
    def test_if(self):
        for value in truthy_values:
            with self.subTest(true_value=value):
                self.assertTranslation(
                    '{% if spam %}T{% endif %}',
                    dict(spam=value),
                    {},
                    'T'
                )
                self.assertTranslation(
                    '{% if spam %}T{% endif %}',
                    {},
                    dict(spam=value),
                    'T'
                )
        for value in falsy_values:
            with self.subTest(false_value=value):
                self.assertTranslation(
                    '{% if spam %}T{% endif %}',
                    dict(spam=value),
                    {},
                    ''
                )
                self.assertTranslation(
                    '{% if spam %}T{% endif %}',
                    {},
                    dict(spam=value),
                    ''
                )

    def test_if_not(self):
        for value in truthy_values:
            with self.subTest(true_value=value):
                self.assertTranslation(
                    '{% if not spam %}T{% endif %}',
                    dict(spam=value),
                    {},
                    ''
                )
                self.assertTranslation(
                    '{% if not spam %}T{% endif %}',
                    {},
                    dict(spam=value),
                    ''
                )
        for value in falsy_values:
            with self.subTest(false_value=value):
                self.assertTranslation(
                    '{% if not spam %}T{% endif %}',
                    dict(spam=value),
                    {},
                    'T'
                )
                self.assertTranslation(
                    '{% if not spam %}T{% endif %}',
                    {},
                    dict(spam=value),
                    'T'
                )

    def test_if_with_else(self):
        for value in truthy_values:
            with self.subTest(true_value=value):
                self.assertTranslation(
                    '{% if spam %}T{% else %}F{% endif %}',
                    dict(spam=value),
                    {},
                    'T'
                )
                self.assertTranslation(
                    '{% if spam %}T{% else %}F{% endif %}',
                    {},
                    dict(spam=value),
                    'T'
                )
        for value in falsy_values:
            with self.subTest(false_value=value):
                self.assertTranslation(
                    '{% if spam %}T{% else %}F{% endif %}',
                    dict(spam=value),
                    {},
                    'F'
                )
                self.assertTranslation(
                    '{% if spam %}T{% else %}F{% endif %}',
                    {},
                    dict(spam=value),
                    'F'
                )

    def test_if_with_elif(self):
        for spam in [True, False]:
            for ham in [True, False]:
                with self.subTest(spam=spam, ham=ham):
                    self.assertTranslation(
                        '{% if spam %}a{% elif ham %}b{% else %}c{% endif %}',
                        dict(spam=spam, ham=ham),
                        {},
                    )
                    self.assertTranslation(
                        '{% if spam %}a{% elif ham %}b{% else %}c{% endif %}',
                        {},
                        dict(spam=spam, ham=ham),
                    )

    def test_if_with_comparison_operators(self):
        for comparison in ['==', '!=', '>', '<', '>=', '<=']:
            for spam in [1, 2, 3]:
                for ham in [1, 2, 3]:
                    with self.subTest(comparison=comparison, spam=spam, ham=ham):
                        self.assertTranslation(
                            '{% if ham ' + comparison + ' spam %}T{% else %}F{% endif %}',
                            dict(spam=spam, ham=ham),
                            {},
                        )
                        self.assertTranslation(
                            '{% if ham ' + comparison + ' spam %}T{% else %}F{% endif %}',
                            {},
                            dict(spam=spam, ham=ham),
                        )
                        self.assertTranslation(
                            '{% if ham ' + comparison + ' spam %}T{% else %}F{% endif %}',
                            dict(spam=spam),
                            dict(ham=ham),
                        )
                        self.assertTranslation(
                            '{% if ham ' + comparison + ' spam %}T{% else %}F{% endif %}',
                            dict(ham=ham),
                            dict(spam=spam),
                        )

    def test_if_with_not_operator(self):
        for spam in [True, False]:
            with self.subTest(spam=spam):
                self.assertTranslation(
                    '{% if not spam %}T{% else %}F{% endif %}',
                    dict(spam=spam),
                    {},
                )
                self.assertTranslation(
                    '{% if not spam %}T{% else %}F{% endif %}',
                    {},
                    dict(spam=spam),
                )

    def test_if_with_or_operator(self):
        for spam in [True, False]:
            for ham in [True, False]:
                with self.subTest(spam=spam, ham=ham):
                    self.assertTranslation(
                        '{% if ham or spam %}T{% else %}F{% endif %}',
                        dict(spam=spam, ham=ham),
                        {},
                    )
                    self.assertTranslation(
                        '{% if ham or spam %}T{% else %}F{% endif %}',
                        {},
                        dict(spam=spam, ham=ham),
                    )
                    self.assertTranslation(
                        '{% if ham or spam %}T{% else %}F{% endif %}',
                        dict(spam=spam),
                        dict(ham=ham),
                    )
                    self.assertTranslation(
                        '{% if ham or spam %}T{% else %}F{% endif %}',
                        dict(ham=ham),
                        dict(spam=spam),
                    )

    def test_if_with_and_operator(self):
        for spam in [True, False]:
            for ham in [True, False]:
                with self.subTest(spam=spam, ham=ham):
                    self.assertTranslation(
                        '{% if ham and spam %}T{% else %}F{% endif %}',
                        dict(spam=spam, ham=ham),
                        {},
                    )
                    self.assertTranslation(
                        '{% if ham and spam %}T{% else %}F{% endif %}',
                        {},
                        dict(spam=spam, ham=ham),
                    )
                    self.assertTranslation(
                        '{% if ham and spam %}T{% else %}F{% endif %}',
                        dict(spam=spam),
                        dict(ham=ham),
                    )
                    self.assertTranslation(
                        '{% if ham and spam %}T{% else %}F{% endif %}',
                        dict(ham=ham),
                        dict(spam=spam),
                    )

    def test_if_with_in_operators(self):
        for operator in ['in', 'not in']:
            array = [1, 2, 3]
            for obj in [2, 4]:
                with self.subTest(operator=operator, array=array, obj=obj):
                    self.assertTranslation(
                        '{% if obj ' + operator + ' array %}T{% else %}F{% endif %}',
                        dict(array=array, obj=obj),
                        {},
                    )
                    self.assertTranslation(
                        '{% if obj ' + operator + ' array %}T{% else %}F{% endif %}',
                        {},
                        dict(array=array, obj=obj),
                    )
                    self.assertTranslation(
                        '{% if obj ' + operator + ' array %}T{% else %}F{% endif %}',
                        dict(array=array),
                        dict(obj=obj),
                    )
                    self.assertTranslation(
                        '{% if obj ' + operator + ' array %}T{% else %}F{% endif %}',
                        dict(obj=obj),
                        dict(array=array),
                    )

    def test_if_with_filter(self):
        self.assertTranslation(
            '{% if spam|add:"1" %}T{% else %}F{% endif %}',
            dict(spam=1),
            {},
            'T'
        )
        self.assertTranslation(
            '{% if spam|add:"1" %}T{% else %}F{% endif %}',
            {},
            dict(spam=1),
            'T'
        )

        self.assertTranslation(
            '{% if spam|add:"1" %}T{% else %}F{% endif %}',
            dict(spam=-1),
            {},
            'F'
        )
        self.assertTranslation(
            '{% if spam|add:"1" %}T{% else %}F{% endif %}',
            {},
            dict(spam=-1),
            'F'
        )

    def test_if_with_double_filters(self):
        self.assertTranslation(
            '{% if list|length|add:"-1" %}T{% else %}F{% endif %}',
            dict(list='a'),
            {},
            'F'
        )
        self.assertTranslation(
            '{% if list|length|add:"-1" %}T{% else %}F{% endif %}',
            {},
            dict(list='a'),
            'F'
        )

        self.assertTranslation(
            '{% if list|length|add:"1" %}T{% else %}F{% endif %}',
            dict(list='ab'),
            {},
            'T'
        )
        self.assertTranslation(
            '{% if list|length|add:"1" %}T{% else %}F{% endif %}',
            {},
            dict(list='ab'),
            'T'
        )

    def test_if_with_nested_conditions(self):
        tpl = '{% if a or not b and True and not c or d or False %}T{% else %}F{% endif %}'
        for a, b, c, d in itertools.product([True, False], repeat=4):
            values = dict(a=a, b=b, c=c, d=d)
            with self.subTest(**values):
                self.assertTranslation(
                    tpl,
                    values,
                    {},
                )
                self.assertTranslation(
                    tpl,
                    {},
                    values,
                )

    def test_loop(self):
        self.assertTranslation(
            '{% for i in numbers %}{{ i }}{% endfor %}',
            dict(numbers=list(range(5))),
            {},
            '01234',
        )
        self.assertTranslation(
            '{% for i in numbers %}{{ i }}{% endfor %}',
            {},
            dict(numbers=list(range(5))),
            '01234',
        )

    def test_loop_reversed(self):
        self.assertTranslation(
            '{% for i in numbers reversed %}{{ i }}{% endfor %}',
            dict(numbers=list(range(5))),
            {},
            '43210',
        )
        self.assertTranslation(
            '{% for i in numbers reversed %}{{ i }}{% endfor %}',
            {},
            dict(numbers=list(range(5))),
            '43210',
        )

    def test_loop_multivalue(self):
        self.assertTranslation(
            '{% for i, j in numbers %}[{{ i }} {{ j }}]{% endfor %}',
            dict(numbers=[(x, y) for x in range(5) for y in range(5)]),
            {},
        )
        self.assertTranslation(
            '{% for i, j in numbers %}{{ i }}{% endfor %}',
            {},
            dict(numbers=[(x, y) for x in range(5) for y in range(5)]),
        )

    def test_loop_with_empty_tag(self):
        self.assertTranslation(
            '{% for i in numbers %}{{ i }}{% empty %}nothing{% endfor %}',
            dict(numbers=[]),
            {},
            'nothing',
        )
        self.assertTranslation(
            '{% for i in numbers %}{{ i }}{% empty %}nothing{% endfor %}',
            {},
            dict(numbers=[]),
            'nothing',
        )

    def test_loop_forloop(self):
        tpl = '''
        {% for i in numbers %}
          [
            {{ forloop.counter }}
            {{ forloop.counter0 }}
            {{ forloop.revcounter }}
            {{ forloop.revcounter0 }}
            {% if forloop.first %}T{% else %}F{% endif %}
            {% if forloop.last %}T{% else %}F{% endif %}
          ]
        {% endfor %}
        '''
        self.assertTranslation(
            tpl,
            dict(numbers=list(range(5))),
            {},
        )
        self.assertTranslation(
            tpl,
            {},
            dict(numbers=list(range(5))),
        )

    def test_loop_double_forloop(self):
        tpl = '''
        {% for i in numbers %}
          {% for i in numbers %}
            [
              {{ forloop.parentloop.counter }} {{ forloop.counter }}
            ]
          {% endfor %}
        {% endfor %}
        '''
        self.assertTranslation(
            tpl,
            dict(numbers=list(range(5))),
            {},
        )
        self.assertTranslation(
            tpl,
            {},
            dict(numbers=list(range(5))),
        )

    def test_loop_with_filter(self):
        for context, tplargs in self.mix_variables(text='abc', more='def'):
            self.assertTranslation(
                '{% for c in text|add:more %} {{ c }} {% endfor %}',
                context,
                tplargs,
            )

    def test_loop_empty(self):
        for context, tplargs in self.mix_variables(empty=[]):
            self.assertTranslation(
                '{% for c in empty %} {{ c }} {% endfor %}',
                context,
                tplargs,
            )

    def test_now(self):
        formatchars = [
            c for c, e
            in datetime_format_javascript_expressions.items()
            if e is not NotImplemented and
            # no way to test microseconds reliably because of time difference
            # between rendering Django template and Javascript template
            # in the browser
            c != 'u'
        ]
        for formatchar in formatchars:
            with self.subTest(formatchar=formatchar):
                self.assertTranslation(
                    '{% now "' + formatchar + '" %}',
                    {},
                    {},
                )

    def test_now_setting_arg(self):
        settings_formats = [
            'DATE_FORMAT',
            'SHORT_DATE_FORMAT',
            'DATETIME_FORMAT',
            'SHORT_DATETIME_FORMAT',
            'TIME_FORMAT',
        ]
        for setting_format in settings_formats:
            with self.subTest(setting_format=setting_format):
                self.assertTranslation(
                    '{% now "' + setting_format + '" %}',
                    {},
                    {},
                )

    def test_now_with_variable_format(self):
        self.assertTranslation(
            '{% now fmt %}',
            dict(fmt='Y'),
            {},
        )

    def test_now_with_asvar(self):
        self.assertTranslation(
            '{% now "Y" as year %}{{ year }}',
            {},
            {},
        )

    # django does not escape the format string characters for the now tag,
    # while it does for the date/time filters
    @unittest.expectedFailure
    def test_now_escaping(self):
        self.assertTranslation(
            '{% now ">" %}',
            {},
            {},
            "&gt;"
        )

    def test_comment(self):
        self.assertTranslation(
            '{% comment %}HELP!{% endcomment %}',
            {},
            {},
            ""
        )

    def test_include(self):
        self.assertTranslation(
            'a{% include tpl with extra="c" %}d',
            dict(tpl=template_from_string('{{ var }}{{ extra }}'), var='b'),
            {},
            "abcd"
        )

    def test_include_loaded(self):
        with mock.patch('django.template.engine.Engine.find_template') as find:
            find.return_value = template_from_string('b'), None
            self.assertTranslation(
                'a{% include "other.tpl" %}c',
                {},
                {},
                "abc"
            )
            # node the template is loaded twice,
            # once when translating to javascript
            # and then again when performing
            # the standard rendering to compare results with
            find.assert_called_with('other.tpl')

    def test_include_template_attr(self):
        class HasTemplateAttr:
            template = template_from_string('{{ var }}{{ extra }}')

            def render(self):
                raise AssertionError("This should not be called")

        self.assertTranslation(
            'a{% include tpl with extra="c" %}d',
            dict(tpl=HasTemplateAttr(), var='b'),
            {},
            "abcd"
        )

    def test_filter(self):
        self.assertTranslation(
            '{% filter length %}abc{% endfilter %}',
            {},
            {},
            "3"
        )
        self.assertTranslation(
            '{% filter length %}{{ spam }}{% endfilter %}',
            dict(spam='abcd'),
            {},
            "4"
        )
        self.assertTranslation(
            '{% filter length %}{{ spam }}{% endfilter %}',
            {},
            dict(spam='abcd'),
            "4"
        )

    def test_templatetag(self):
        args = [
            'openblock',
            'closeblock',
            'openvariable',
            'closevariable',
            'openbrace',
            'closebrace',
            'opencomment',
            'closecomment',
        ]
        for arg in args:
            with self.subTest(argument=arg):
                self.assertTranslation(
                    '{% templatetag ' + arg + ' %}',
                    {},
                    {},
                )

    def test_lorem(self):
        self.assertTranslation(
            '{% lorem %}',
            {},
            {},
        )
        self.assertTranslation(
            '{% lorem 1 %}',
            {},
            {},
        )
        self.assertTranslation(
            '{% lorem 1 w %}',
            {},
            {},
        )
        # no way to test random argument

    def test_lorem_with_variables(self):
        self.assertTranslation(
            '{% lorem num %}',
            dict(num=1),
            {},
        )
        self.assertTranslation(
            '{% lorem num w %}',
            dict(num=1),
            {},
        )
