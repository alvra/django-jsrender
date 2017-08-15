from __future__ import unicode_literals
import unittest
import operator
import string
from django.template import (
    defaulttags, Context, Node,
    Variable, VariableDoesNotExist, TemplateSyntaxError,
)
from django.utils.timezone import now
from ..functions import JavascriptExpression
from ..datetimeformat import datetime_format_javascript_expressions
from .utils import (
    TranslationTestCase, JavascriptTranslationTestCase,
    template_from_string, nodelist_from_string
)


class VariableResolutionTests(TranslationTestCase):
    def test_standard_lookup(self):
        c = Context(dict(
            a=123,
            b='bla',
            c=dict(d=32),
            e='bla\'bi',
        ))
        self.assertEqual(Variable('a').resolve(c), 123)
        self.assertEqual(Variable('b').resolve(c), 'bla')
        self.assertEqual(Variable('c').resolve(c), dict(d=32))
        self.assertEqual(Variable('c.d').resolve(c), 32)
        self.assertEqual(Variable('e').resolve(c), 'bla\'bi')

    def test_expression_lookup(self):
        c = Context(dict(
            a=JavascriptExpression('var_a'),
        ))
        self.assertEqual(Variable('a').resolve(c), JavascriptExpression('var_a'))
        self.assertEqual(Variable('a.spam').resolve(c), JavascriptExpression('var_a.spam'))

        c.push()
        c['a'] = dict(spam=21)
        self.assertEqual(Variable('a').resolve(c), dict(spam=21))
        self.assertEqual(Variable('a.spam').resolve(c), 21)
        c.pop()

        self.assertEqual(Variable('a').resolve(c), JavascriptExpression('var_a'))
        self.assertEqual(Variable('a.spam').resolve(c), JavascriptExpression('var_a.spam'))


class QuickTranslateTests(TranslationTestCase):
    """Quick sanity checks for translation.

    These tests are not replacements for the ones from TranslateTests,
    but can be helpful when selenium is not available or when you need to iterate quickly.
    """

    def get_translator(self, arguments):
        return self.translator_class(
            arguments,
            html_escape_function=self.html_escape_function,
            joiner='',
            indentation='',
            debug=True,
        )

    def test_making_varnames(self):
        t = self.get_translator([])
        t.html_escape_function = 'escape'
        varnames = set()
        invalids = t.get_invalid_varnames()
        self.assertIn(t.html_escape_function, invalids)
        with self.assertRaisesRegex(ValueError, "Out of variable names"):
            while True:
                varname = t.get_varname()
                self.assertNotIn(varname, varnames)
                self.assertNotIn(varname, invalids)
                varnames.add(varname)

    def test_making_varnames_with_invalids(self):
        t = self.get_translator([])
        self.assertIn(t.html_escape_function, t.get_invalid_varnames())
        t.get_invalid_varnames = lambda: set('klmn')
        varnames = set()
        invalids = t.get_invalid_varnames()
        with self.assertRaisesRegex(ValueError, "Out of variable names"):
            while True:
                varname = t.get_varname()
                self.assertNotIn(varname, varnames)
                self.assertNotIn(varname, invalids)
                varnames.add(varname)

    def test_write_bytes(self):
        t = self.get_translator([])
        with self.assertRaises(TypeError):
            t.write(b'abc')

    def test_text(self):
        tpl = "hello world"
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+="hello world";return a;',
        )

    def test_text_no_escaping(self):
        tpl = "hello<br/>world"
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+="hello<br/>world";return a;',
        )

    def test_variable(self):
        tpl = "hello {{ spam }}"
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(spam='abc')), nodelist),
            'var a="";a+="hello ";a+="abc";return a;',
        )

        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+="hello ";a+=escape(b);return a;',
        )

        # if both the jsrender argument and a context variable
        # with the same name are set, the argument takes precedent
        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(dict(spam='abc')), nodelist),
            'var a="";a+="hello ";a+=escape(b);return a;',
        )

    def test_variable_integer(self):
        tpl = "{{ number }}"
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(number=1)), nodelist),
            'var a="";a+="1";return a;',
        )

        t = self.get_translator(['number'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+=escape(b);return a;',
        )

    def test_missing_variable(self):
        tpl = "hello {{ spam }}"
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        with self.assertRaises(VariableDoesNotExist):
            t.translate(Context(), nodelist)

    def test_variable_escaping(self):
        tpl = "hello {{ spam }}"
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(spam='a<br/>c')), nodelist),
            'var a="";a+="hello ";a+="a&lt;br/&gt;c";return a;',
        )

    def test_variable_lookup(self):
        tpl = "hello {{ spam.ham }}"
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(spam=dict(ham='abc'))), nodelist),
            'var a="";a+="hello ";a+="abc";return a;',
        )

        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+="hello ";a+=escape(b.ham);return a;',
        )

        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(dict(spam=dict(ham='abc'))), nodelist),
            'var a="";a+="hello ";a+=escape(b.ham);return a;',
        )

    def test_missing_variable_lookup(self):
        tpl = "hello {{ spam.ham }}"
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        with self.assertRaises(VariableDoesNotExist):
            t.translate(Context(), nodelist)

    def test_invalid_tags(self):
        invalids = [
            ('load', 'jsrender'),
        ]
        t = self.get_translator([''])
        for tag, arg in invalids:
            with self.subTest(tag=tag):
                tpl = '{% ' + tag + ' ' + arg + '  %}'
                nodelist = nodelist_from_string(tpl)
                with self.assertRaises(TemplateSyntaxError):
                    t.translate(Context(), nodelist)

    def test_tag_loop_try_output_forloop(self):
        tpl = '{% for val in list %}{{ forloop }}{% endfor %}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator(['list'])
        with self.assertRaises(TemplateSyntaxError):
            t.translate(Context(), nodelist)

    def test_tag_loop_try_nonexisting_forloop_attribute(self):
        tpl = '{% for val in list %}{{ forloop.doesnotexist }}{% endfor %}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator(['list'])
        with self.assertRaisesRegex(
            VariableDoesNotExist,
            "Failed lookup for key \[doesnotexist\] in [u]?'<ForloopValue>'"
        ):
            t.translate(Context(), nodelist)

    def test_tag_now(self):
        for letter in string.ascii_letters:
            expr = datetime_format_javascript_expressions.get(letter)
            is_noop = expr is None
            is_implemented = expr is not NotImplementedError
            with self.subTest(letter=letter, is_noop=is_noop, is_implemented=is_implemented):
                tpl = '{% now "' + letter + '" %}'
                nodelist = nodelist_from_string(tpl)
                t = self.get_translator([])
                if expr is None:
                    self.assertJsEqual(
                        t.translate(Context(), nodelist),
                        'var a="";var b=new Date();a+="' + letter + '";return a;',
                    )
                elif expr is NotImplemented:
                    with self.assertRaises(NotImplementedError):
                        t.translate(Context(dict(someday=now())), nodelist)
                else:
                    self.assertJsEqual(
                        t.translate(Context(), nodelist),
                        'var a="";var b=new Date();a+=%s;return a;' % (expr % dict(x='b')),
                    )

    # django does not support passing a variable format string to the now tag,
    # it just assumes it starts and ends with quotes and interprets
    # the rest as the formst string literal
    @unittest.expectedFailure
    def test_tag_now_with_variable_format(self):  # pragma: no cover
        tpl = '{% now fmt %}'
        tpl = '{% extends fmt %}'
        nodelist = nodelist_from_string(tpl)
        node = nodelist[0]
        self.assertIsInstance(node, defaulttags.NowNode)
        fmt = node.format_string
        self.assertIsInstance(fmt, Variable)
        self.assertIsInstance(fmt.var, 'fmt')
        t = self.get_translator(['fmt'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(dict()), nodelist)

    def test_tag_now_escaped_char(self):
        tpl = '{% now "\\Y" %}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";var b=new Date();a+="Y";return a;',
        )

    def test_include_isolated(self):
        tpl = '{% include tpl only %}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator([])
        tpl = template_from_string('{{ var }}')
        with self.assertRaises(VariableDoesNotExist):
            t.translate(Context(dict(tpl=tpl, var=1)), nodelist)

    def test_tag_lorem_with_variables(self):
        tpl = '{% lorem num %}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator(['num'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(), nodelist)

    def test_not_implemented_tag(self):
        # make a 'tag type' that's not implemented
        class ThirdPartyNode(Node):
            pass
        t = self.get_translator([])
        with self.assertRaises(NotImplementedError):
            list(t.translate_node(Context(), ThirdPartyNode()))

    def test_compatible_tag(self):
        # make a 'tag type' that's not implemented
        # but has a render_javascript method to be compatible
        class CompatibleNode(Node):
            def render_javascript(self, translator, context):
                yield (translator, context)
        context = Context()
        translator = self.get_translator([])
        result = list(translator.translate_node(context, CompatibleNode()))
        self.assertEqual(len(result), 1)
        self.assertIs(result[0][0], translator)
        self.assertIs(result[0][1], context)

    def test_compatible_tag_returning_non_text(self):
        # make a 'tag type' that's not implemented
        # but has a render_javascript method to be compatible
        class ErroneousCompatibleNode(Node):
            def render_javascript(self, translator, context):
                yield 1  # not text!
        context = Context()
        translator = self.get_translator([])
        node = ErroneousCompatibleNode()
        with self.assertRaisesRegex(
            TypeError,
            "Non text 1 from "
            "<jsrender.tests.[a-zA-Z._<>]+.ErroneousCompatibleNode object at 0x[0-9a-f]+>"
        ):
            list(translator.translate_nodelist(context, [node]))

    def test_compatible_tag_unbalenced_indentation(self):
        # make a 'tag type' that's not implemented
        # but has a render_javascript method to be compatible
        class ErroneousCompatibleNode(Node):
            def render_javascript(self, translator, context):
                yield 'a'
                translator.indent()  # unbalenced!
        context = Context()
        translator = self.get_translator([])
        node = ErroneousCompatibleNode()
        with self.assertRaisesRegex(
            AssertionError,
            "Indentation level not restored by "
            "<jsrender.tests.[a-zA-Z._<>]+.ErroneousCompatibleNode object at 0x[0-9a-f]+>, "
            "going from 0 to 1"
        ):
            list(translator.translate_nodelist(context, [node]))

    def test_compatible_tag_too_many_dedents(self):
        # make a 'tag type' that's not implemented
        # but has a render_javascript method to be compatible
        class ErroneousCompatibleNode(Node):
            def render_javascript(self, translator, context):
                yield 'a'
                translator.dedent()  # dedent before indent!
        context = Context()
        translator = self.get_translator([])
        node = ErroneousCompatibleNode()
        with self.assertRaisesRegex(AssertionError, "Too many dedents"):
            list(translator.translate_nodelist(context, [node]))

    def test_filter_add(self):
        tpl = '{{ spam|add:"2" }}'
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(spam=3)), nodelist),
            'var a="";a+="5";return a;',
        )

        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+=escape(b+2);return a;',
        )

    def test_filter_add_variable(self):
        tpl = '{{ spam|add:ham }}'
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator([])
        self.assertJsEqual(
            t.translate(Context(dict(spam=3, ham=4)), nodelist),
            'var a="";a+="7";return a;',
        )

        t = self.get_translator(['spam', 'ham'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+=escape(b+c);return a;',
        )

        t = self.get_translator(['spam'])
        self.assertJsEqual(
            t.translate(Context(dict(ham=4)), nodelist),
            'var a="";a+=escape(b+4);return a;',
        )

        t = self.get_translator(['ham'])
        self.assertJsEqual(
            t.translate(Context(dict(spam=3)), nodelist),
            'var a="";a+=escape(3+b);return a;',
        )

    def test_filter_date(self):
        for letter in string.ascii_letters:
            expr = datetime_format_javascript_expressions.get(letter)
            is_noop = expr is None
            is_implemented = expr is not NotImplementedError
            with self.subTest(letter=letter, is_noop=is_noop, is_implemented=is_implemented):
                tpl = '{{ someday|date:"' + letter + '" }}'
                nodelist = nodelist_from_string(tpl)
                t = self.get_translator(['someday'])
                if expr is None:
                    self.assertJsEqual(
                        t.translate(Context(), nodelist),
                        'var a="";a+="' + letter + '";return a;',
                    )
                elif expr is NotImplemented:
                    with self.assertRaises(NotImplementedError):
                        t.translate(Context(dict(someday=now())), nodelist)
                else:
                    self.assertJsEqual(
                        t.translate(Context(), nodelist),
                        'var a="";a+=(%s);return a;' % (expr % dict(x='b')),
                    )

    def test_filter_date_escaped_char(self):
        tpl = '{{ someday|date:"\\Y" }}'
        nodelist = nodelist_from_string(tpl)
        t = self.get_translator(['someday'])
        self.assertJsEqual(
            t.translate(Context(), nodelist),
            'var a="";a+="Y";return a;',
        )

    def test_filter_date_with_variable_format(self):
        tpl = '{{ someday|date:format }}'
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator(['format', 'someday'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(dict()), nodelist)

        t = self.get_translator(['format'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(dict(someday=now())), nodelist)

    def test_filter_floatformat_with_variable_format(self):
        tpl = '{{ number|floatformat:format }}'
        nodelist = nodelist_from_string(tpl)

        t = self.get_translator(['format', 'number'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(dict()), nodelist)

        t = self.get_translator(['format'])
        with self.assertRaises(NotImplementedError):
            t.translate(Context(dict(number=1)), nodelist)

    def test_calling_fixed_filter(self):
        # make a 'filter function' that's not implemented
        def func(v, a):
            return (v, a)
        # see if it works with static values
        translator = self.get_translator([])
        value = object()
        arg = object()
        v, a = translator.translate_filter(value, func, (arg,))
        self.assertIs(v, value)
        self.assertIs(a, arg)

    def test_not_implemented_filter(self):
        # make a 'filter function' that's not implemented
        func = operator.__add__
        t = self.get_translator([])
        with self.assertRaises(NotImplementedError):
            t.translate_filter(1, func, [JavascriptExpression('2')])
        with self.assertRaises(NotImplementedError):
            t.translate_filter(JavascriptExpression('1'), func, [2])

    def test_compatible_filter(self):
        # make a 'filter function' that's not implemented
        # but has a render_javascript callable attribute to be compatible
        def compatible_filter(value, arg):
            return 'Got %s and %s' % (value, arg)
        # try with pure values
        translator = self.get_translator([])
        result = translator.translate_filter(1, compatible_filter, (2,))
        self.assertEqual(result, 'Got 1 and 2')
        # try with js exprs
        compatible_filter.render_javascript = lambda v, a: (v, a)
        value = JavascriptExpression('v')
        arg = JavascriptExpression('a')
        v, a = translator.translate_filter(value, compatible_filter, (arg,))
        self.assertIs(v, value)
        self.assertIs(a, arg)


class TranslateTests(JavascriptTranslationTestCase):
    def test_text(self):
        self.assertTranslation(
            "hello world",
            {},
            {},
        )

    def test_text_no_escaping(self):
        self.assertTranslation(
            "hello<br/>world",
            {},
            {},
        )

    def test_variable(self):
        self.assertTranslation(
            "hello {{ name }}",
            dict(name='spam'),
            {},
        )
        self.assertTranslation(
            "hello {{ name }}",
            {},
            dict(name='spam'),
        )
        # if both the jsrender argument and a context variable
        # with the same name are set, the argument takes precedent
        self.assertTranslation(
            "hello {{ name }}",
            dict(name='spam'),
            dict(name='ham'),
            expect='hello ham',
        )

    def test_variable_escaping(self):
        self.assertTranslation(
            "hello {{ name }}",
            dict(name='<br/>spam'),
            {},
        )
        self.assertTranslation(
            "hello {{ name }}",
            {},
            dict(name='<br/>spam'),
        )

    def test_variable_lookup(self):
        self.assertTranslation(
            "hello {{ user.name }}",
            dict(user=dict(name='abc')),
            {},
        )
        self.assertTranslation(
            "hello {{ user.name }}",
            {},
            dict(user=dict(name='abc')),
        )
        # if both the jsrender argument and a context variable
        # with the same name are set, the argument takes precedent
        self.assertTranslation(
            "hello {{ user.name }}",
            dict(user=dict(name='abc')),
            dict(user=dict(name='def')),
            expect='hello def',
        )

    def test_if_with_length_filter(self):
        self.assertTranslation(
            '{% if spam|length %}yes{% endif %}',
            dict(spam=list(range(10))),
            {},
            "yes"
        )
        self.assertTranslation(
            '{% if spam|length %}yes{% endif %}',
            {},
            dict(spam=list(range(10))),
            "yes"
        )
        self.assertTranslation(
            '{% if spam|length %}yes{% endif %}',
            dict(spam=[]),
            {},
            ""
        )
        self.assertTranslation(
            '{% if spam|length %}yes{% endif %}',
            {},
            dict(spam=[]),
            ""
        )

    def test_loop_with_if_not_forloop_last(self):
        self.assertTranslation(
            '{% for i in spam %}{% if not forloop.last %}y{% else %}n{% endif %}{% endfor %}',
            dict(spam=list(range(3))),
            {},
            "yyn"
        )
        self.assertTranslation(
            '{% for i in spam %}{% if not forloop.last %}y{% else %}n{% endif %}{% endfor %}',
            {},
            dict(spam=list(range(3))),
            "yyn"
        )
