from __future__ import unicode_literals
import unittest
import six
from django.utils.safestring import SafeText
from ..functions import (
    escape, mark_safe, concatenate, is_attributable,
    JavascriptExpression, SafeJavascriptExpression
)
from .utils import JsrenderTestCase


class EscapeTests(JsrenderTestCase):
    def test_string(self):
        tests = {
            'abc': 'abc',
            'a>b': 'a&gt;b',
        }
        for test, result in tests.items():
            self.assertEqual(escape(None, test), result)

    def test_string_twice(self):
        tests = {
            'abc': 'abc',
            'a>b': 'a&gt;b',
        }
        for test, result in tests.items():
            first = escape(None, test)
            second = escape(None, first)
            self.assertEqual(second, result)

    def test_safestring(self):
        tests = [
            'abc',
            'a>b',
        ]
        for test in tests:
            self.assertEqual(escape(None, SafeText(test)), test)

    def test_jsexpr(self):
        tests = {
            'abc': 'escape(abc)',
        }
        for test, result in tests.items():
            e = escape('escape', JavascriptExpression(test))
            self.assertEqual(e.expression, result)

    def test_jsexpr_twice(self):
        tests = {
            'abc': 'escape(abc)',
        }
        for test, result in tests.items():
            first = escape('escape', JavascriptExpression(test))
            second = escape('escape', first)
            self.assertEqual(second.expression, result)

    def test_safejsexpr(self):
        tests = [
            'abc',
            'a>c',
            'escape(a)',
        ]
        for test in tests:
            e = escape('escape', SafeJavascriptExpression(test))
            self.assertEqual(e.expression, test)

    def test_invalid_values(self):
        invalids = [
            True,
            None,
        ]
        for value in invalids:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    escape(None, value)


class MarkSafeTests(unittest.TestCase):
    def test_string(self):
        string = 'a>c'
        result = mark_safe(string)
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, string)

    def test_jsexpr(self):
        expr = 'a>c'
        result = mark_safe(JavascriptExpression(expr))
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, expr)

    def test_safe_string(self):
        string = SafeText('a>c')
        self.assertIs(mark_safe(string), string)

    def test_safe_jsexpr(self):
        jsexpr = SafeJavascriptExpression('a>c')
        self.assertIs(mark_safe(jsexpr), jsexpr)

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            mark_safe(1)


class ConcaternationTests(unittest.TestCase):
    string_parts = ['a', 'b', 'c']
    jsexpr_expression_parts = ['"a"', '"b"', '"c"']
    safe_string_parts = list(map(SafeText, string_parts))
    jsexpr_parts = list(map(JavascriptExpression, jsexpr_expression_parts))
    safe_jsexpr_parts = list(map(SafeJavascriptExpression, jsexpr_expression_parts))

    def test_empty(self):
        self.assertEqual(concatenate('e', []), '')

    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            concatenate('e', ['a', 1])

    def test_single_string(self):
        result = concatenate('e', ['abc'])
        self.assertIsInstance(result, six.text_type)
        self.assertEqual(result, 'abc')

    def test_single_safe_string(self):
        result = concatenate('e', [SafeText('abc')])
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, 'abc')

    def test_single_jsexpr(self):
        result = concatenate('e', [JavascriptExpression('abc')])
        self.assertIsInstance(result, JavascriptExpression)
        self.assertEqual(result.expression, 'abc')

    def test_single_safe_jsexpr(self):
        result = concatenate('e', [SafeJavascriptExpression('abc')])
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, 'abc')

    def test_unsafe_strings(self):
        result = concatenate('e', self.string_parts)
        self.assertIsInstance(result, six.text_type)
        self.assertEqual(result, 'abc')

    def test_unsafe_jsexprs(self):
        result = concatenate('e', self.jsexpr_parts)
        self.assertIsInstance(result, JavascriptExpression)
        self.assertEqual(result.expression, '+'.join(self.jsexpr_expression_parts))

    def test_safe_strings(self):
        result = concatenate('e', self.safe_string_parts)
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, 'abc')

    def test_safe_jsexprs(self):
        result = concatenate('e', self.safe_jsexpr_parts)
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, '+'.join(self.jsexpr_expression_parts))

    def test_unsafe_mixed(self):
        result = concatenate('e', ['a', JavascriptExpression('b')])
        self.assertIsInstance(result, JavascriptExpression)
        self.assertEqual(result.expression, '"a"+b')

    def test_safe_mixed(self):
        result = concatenate('e', [SafeText('a'), SafeJavascriptExpression('b')])
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, '"a"+b')

    def test_mix_safe_unsafe_string(self):
        result = concatenate('e', ['>', SafeText('<')])
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, '&gt;<')

    def test_mix_unsafe_safe_string(self):
        result = concatenate('e', [SafeText('>'), '<'])
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, '>&lt;')

    def test_mix_safe_unsafe_jsexpr(self):
        result = concatenate('e', [JavascriptExpression('a'), SafeJavascriptExpression('b')])
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, 'e(a)+b')

    def test_mix_safe_jsexpr_unsafe_string(self):
        result = concatenate('e', ['>', SafeJavascriptExpression('b')])
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, '"&gt;"+b')

    def test_mix_safe_string_unsafe_jsexpr(self):
        result = concatenate('e', [JavascriptExpression('a'), SafeText('>')])
        self.assertIsInstance(result, SafeJavascriptExpression)
        self.assertEqual(result.expression, 'e(a)+">"')

    def test_string_collapse_in_between_jsexpr(self):
        result = concatenate('e', [JavascriptExpression('a'), 'b', 'c', JavascriptExpression('d')])
        self.assertIsInstance(result, JavascriptExpression)
        self.assertEqual(result.expression, 'a+"bc"+d')

    def test_ignore_empty_string(self):
        result = concatenate('e', ['a', '', 'b'])
        self.assertIsInstance(result, six.text_type)
        self.assertEqual(result, 'ab')

    def test_ignore_empty_safe_string(self):
        result = concatenate('e', map(SafeText, ['a', '', 'b']))
        self.assertIsInstance(result, SafeText)
        self.assertEqual(result, 'ab')


class IsAttributableTests(JsrenderTestCase):
    def test_attributables(self):
        attributable_fields = [
            'field',
            'a',
            '1',
        ]
        for field in attributable_fields:
            with self.subTest(field=field):
                self.assertTrue(is_attributable(field))

    def test_not_attributables(self):
        not_attributable_fields = [
            'a b',
            "lil'guy",
            'Big"Man',
            '[weird]',
            'turtle.turtle',
        ]
        for field in not_attributable_fields:
            with self.subTest(field=field):
                self.assertFalse(is_attributable(field))


class JavascriptExpressionTests(unittest.TestCase):
    def test_equality(self):
        self.assertTrue(JavascriptExpression('a') == JavascriptExpression('a'))
        self.assertTrue(SafeJavascriptExpression('a') == SafeJavascriptExpression('a'))
        self.assertFalse(JavascriptExpression('a') == JavascriptExpression('b'))
        self.assertFalse(SafeJavascriptExpression('a') == SafeJavascriptExpression('b'))
        self.assertFalse(JavascriptExpression('a') == SafeJavascriptExpression('a'))
        self.assertFalse(SafeJavascriptExpression('a') == JavascriptExpression('a'))

    def test_inequality(self):
        self.assertFalse(JavascriptExpression('a') != JavascriptExpression('a'))
        self.assertFalse(SafeJavascriptExpression('a') != SafeJavascriptExpression('a'))
        self.assertTrue(JavascriptExpression('a') != JavascriptExpression('b'))
        self.assertTrue(SafeJavascriptExpression('a') != SafeJavascriptExpression('b'))
        self.assertTrue(JavascriptExpression('a') != SafeJavascriptExpression('a'))
        self.assertTrue(SafeJavascriptExpression('a') != JavascriptExpression('a'))

    def test_invalid_empty(self):
        with self.assertRaises(ValueError):
            JavascriptExpression('')

    def test_getitem(self):
        jsexpr = JavascriptExpression('a')
        self.assertIsInstance(jsexpr['b'], JavascriptExpression)
        self.assertEqual(jsexpr['b'].expression, 'a.b')

    def test_getitem_non_variable(self):
        jsexpr = JavascriptExpression('1')
        self.assertIsInstance(jsexpr['b'], JavascriptExpression)
        self.assertEqual(jsexpr['b'].expression, '(1).b')

    def test_getitem_not_attributable(self):
        jsexpr = JavascriptExpression('a')
        self.assertIsInstance(jsexpr['c d'], JavascriptExpression)
        self.assertEqual(jsexpr['c d'].expression, 'a["c d"]')

    def test_getitem_not_attributable_non_variable(self):
        jsexpr = JavascriptExpression('1')
        self.assertIsInstance(jsexpr['c d'], JavascriptExpression)
        self.assertEqual(jsexpr['c d'].expression, '(1)["c d"]')

    def test_getitem_from_variable_with_underscore(self):
        jsexpr = JavascriptExpression('var_a')
        self.assertIsInstance(jsexpr['b'], JavascriptExpression)
        self.assertEqual(jsexpr['b'].expression, 'var_a.b')

    def test_repr(self):
        jsexpr = JavascriptExpression('a')
        self.assertEqual(repr(jsexpr), '<JavascriptExpression a>')
        jsexpr = SafeJavascriptExpression('a')
        self.assertEqual(repr(jsexpr), '<SafeJavascriptExpression a>')
