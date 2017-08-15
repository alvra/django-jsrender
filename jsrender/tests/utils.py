from __future__ import unicode_literals
import unittest
import itertools
import six
import contextlib
try:
    import execjs
except ImportError:
    execjs = None
from django.template import Engine, Context
from ..functions import express
from ..translate import Translator
from ..utils import html_escape_function


# truthy and falsy values in both Python and Javascript
truthy_values = [
    True,
    1,
]
falsy_values = [
    False,
    0,
]

# truthy and falsy values that are expressed the same in both Python and Javascript
truthy_expressable_values = [
    'a',
    1,
]
falsy_expressable_values = [
    '',
    0,
]


def template_from_string(template_string):
    return Engine(libraries={
        'jsrender': 'jsrender.templatetags.jsrender',
    }).from_string(template_string)


def nodelist_from_string(template_string):
    template = template_from_string(template_string)
    return template.nodelist


class JsrenderTestMixin(object):
    def subTest(self, *args, **kwargs):
        if hasattr(unittest.TestCase, 'subTest'):
            return super().subTest(*args, **kwargs)
        else:
            @contextlib.contextmanager
            def noop():
                try:
                    yield
                except AssertionError as e:
                    six.raise_from(AssertionError("%s [with %s]" % (
                        e,
                        ', '.join('%s=%r' % x for x in kwargs.items()),
                    )), e)
            return noop()

    def assertRaisesRegex(self, *args, **kwargs):
        if hasattr(unittest.TestCase, 'assertRaisesRegex'):
            return super().assertRaisesRegex(*args, **kwargs)
        else:
            # compatibility with python 2
            return super(JsrenderTestMixin, self).assertRaisesRegexp(*args, **kwargs)

    def mix_variables(self, **kwargs):
        # three options; variable in context, template argument or both
        mix = itertools.product([1, 2, 3], repeat=len(kwargs))
        for choices in mix:
            context = dict()
            tplargs = dict()
            for choice, (name, value) in zip(choices, kwargs.items()):
                if 1 & choice:
                    context[name] = value
                if 2 & choice:
                    tplargs[name] = value
            with self.subTest(context=context, tplargs=tplargs):
                yield (context, tplargs)


class TranslationMixin(JsrenderTestMixin):
    translator_class = Translator
    html_escape_function = 'escape'

    def get_translator(self, arguments):
        return self.translator_class(
            arguments,
            html_escape_function=self.html_escape_function,
            debug=True,
        )

    def assertJsEqual(self, js1, js2, msg=None):
        self.assertMultiLineEqual(
            js1.replace('\n', '').replace(';', ';\n'),
            js2.replace('\n', '').replace(';', ';\n'),
            msg
        )


class JavascriptTranslationMixin(TranslationMixin):
    maxDiff = 1024

    @classmethod
    def get_html_escape_function(cls):
        return html_escape_function(cls.html_escape_function)

    def setUp(self):
        if execjs is None:
            raise unittest.SkipTest(
                "PyExecJs must be installed to run these tests.")
        try:
            self.javascript_runtime = execjs.get()
        except execjs.RuntimeUnavailableError as e:
            raise six.raise_from(
                unittest.SkipTest(
                    "PyExecJs could not find a javascript runtime."),
                e)

    def execute_javascript(self, js):
        # this is slightly convoluted
        # since execjs expects an expression
        # instead of statements, so we wrap the
        # statements in an anonymous function
        code = '(function(){%s; return %s})()' % (
            self.get_html_escape_function(),
            js)
        return self.javascript_runtime.eval(code)

    def assertTranslationResultEqual(self, result, expected, script):
        try:
            self.assertMultiLineEqual(result, expected)
        except AssertionError as e:
            raise AssertionError(
                '%s\n---[ Javascript ]---\n%s\n---' % (
                    e,
                    script,
                )
            )

    def assertTranslation(self, template, context, arguments, expect=None):
        # build stuff needed to translate
        translator = self.get_translator(arguments.keys())
        template = template_from_string(template)
        nodelist = template.nodelist
        # translate
        translator.indent()
        translate_context = Context(context)
        with translate_context.bind_template(template):
            translated = translator.translate(translate_context, nodelist)
        # build javascript
        func_arguments = map(express, arguments.values())
        script = '(function(\n  %s\n){\n%s\n})(\n  %s\n)' % (
            ',\n  '.join(translator.arg_varnames),
            translated,
            ',\n  '.join(func_arguments),
        )
        # execute javascript
        result = self.execute_javascript(script)
        # render template itself
        new_context = Context(context)
        new_context.update(arguments)  # arguments takes precent over context
        expected_result = template.render(new_context)
        # now check that the Javascript function has the same result as the Django template
        self.assertTranslationResultEqual(result, expected_result, script)
        # if an expectation is given, check that too
        if expect is not None:
            self.assertTranslationResultEqual(result, expect, script)


class JsrenderTestCase(JsrenderTestMixin, unittest.TestCase):
    pass


class TranslationTestCase(TranslationMixin, unittest.TestCase):
    pass


class JavascriptTranslationTestCase(JavascriptTranslationMixin, unittest.TestCase):
    pass
