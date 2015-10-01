from __future__ import unicode_literals
import unittest
import tempfile
import itertools
import six
import contextlib
try:
    import selenium
    import selenium.webdriver
    import selenium.common.exceptions
except ImportError:
    selenium = None
from django.template import Template, Context
from django.core.exceptions import ImproperlyConfigured
from django.template.base import get_library
from django.template.debug import DebugLexer, DebugParser
try:
    from django.test import override_settings
except ImportError:
    # django < 1.7
    from django.test.utils import override_settings
from django.conf import settings
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


def conditional_override_settings(condition, **settings):
    if condition:
        return override_settings(**settings)
    else:
        return lambda x: x


def skipUnlessSelenium():
    return unittest.skipIf(selenium is None, "Selenium must be installed to run these tests.")


def compile_template_string(template_string, load=[]):
    origin = None
    lexer_class, parser_class = DebugLexer, DebugParser
    lexer = lexer_class(template_string, origin)
    parser = parser_class(lexer.tokenize())
    if load:
        for taglib in load:
            lib = get_library(taglib)
            parser.add_library(lib)
    nodelist = parser.parse()
    template = Template('')
    template.nodelist = nodelist
    return template


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


class SeleniumTranslationMixin(TranslationMixin):
    maxDiff = 1024
    default_drivers = [
        'PhantomJS',
        'Firefox',
        'Chrome',
    ]

    @classmethod
    def get_selenium_driver_names(cls):
        driver_name = getattr(settings, 'SELENIUM_DRIVER', None)
        if driver_name is None:
            return cls.default_drivers
        else:
            return [driver_name]

    @classmethod
    def get_selenium_driver(cls, *names):
        if not names:
            names = cls.get_selenium_driver_names()
        for name in names:
            driver_class = getattr(selenium.webdriver, name)
            try:
                return driver_class()
            except selenium.common.exceptions.WebDriverException:
                pass
        raise ImproperlyConfigured(
            "No selenium browser found, tried: %s"
            % ', '.join(names)
        )

    @classmethod
    def get_html_escape_function(cls):
        return html_escape_function(cls.html_escape_function)

    @classmethod
    def setUpClass(cls):
        # start driver
        driver = cls.get_selenium_driver()
        # load page
        tmpfile = tempfile.NamedTemporaryFile('w')
        html = '''
        <!DOCTYPE html>
        <html>
            <head>
                <script>
                    %s
                </script>
            </head>
            <body>
            <textarea></textarea>
            </body>
        </html>
        ''' % cls.get_html_escape_function()
        tmpfile.write(html)
        tmpfile.flush()
        driver.get("file://" + tmpfile.name)
        # save driver and file on class
        cls.driver = driver
        cls.tmpfile = tmpfile
        # get dom element to render to, and save
        cls.renderelement = driver.find_element_by_tag_name('textarea')

    @classmethod
    def tearDownClass(cls):
        cls.tmpfile.close()
        cls.driver.close()
        cls.driver.quit()

    def assertTranslationResultEqual(self, result, expected, function, arguments):
        try:
            self.assertMultiLineEqual(result, expected)
        except AssertionError as e:
            raise AssertionError(
                '%s\n---[ Function ]---\n%s\n---[ Call ]---\nresult = jstemplate(%s);' % (
                    e,
                    function,
                    ', '.join(arguments),
                )
            )

    def assertTranslation(self, template, context, arguments, expect=None, load=[]):
        # build stuff needed to translate
        translator = self.get_translator(arguments.keys())
        template = compile_template_string(template, load)
        nodelist = template.nodelist
        # translate
        translator.indent()
        translate_context = Context(context)
        if hasattr(translate_context, 'bind_template'):
            # django >= 1.8
            with translate_context.bind_template(template):
                translated = translator.translate(translate_context, nodelist)
        else:
            # django < 1.8
            translated = translator.translate(translate_context, nodelist)
        # build function
        function = 'function jstemplate(%s){\n%s\n}' % (
            ','.join(translator.arg_varnames),
            translated,
        )
        # execute function to page element
        func_arguments = map(express, arguments.values())
        script = '''
        function test(){
            var el = document.getElementsByTagName('textarea')[0];
            %s
            var result = jstemplate(%s);
            el.value = result;
        }
        test();
        ''' % (
            function,
            ','.join(func_arguments),
        )
        try:
            self.driver.execute_script(script)
        except selenium.common.exceptions.WebDriverException as e:
            raise
            six.raise_from(Exception(
                "Error rendering jstemplate: %r\n%s\n%s"
                % (e.msg, function, func_arguments)
            ), e)
        # get result from page element
        result = self.renderelement.get_attribute('value')
        # render template itself
        new_context = Context(context)
        new_context.update(arguments)  # arguments takes precent over context
        expected_result = template.render(new_context)
        # now check that the Javascript function has the same result as the Django template
        self.assertTranslationResultEqual(result, expected_result, function, func_arguments)
        # if an expectation is given, check that too
        if expect is not None:
            self.assertTranslationResultEqual(result, expect, function, func_arguments)


class JsrenderTestCase(JsrenderTestMixin, unittest.TestCase):
    pass


class TranslationTestCase(TranslationMixin, unittest.TestCase):
    pass


class SeleniumTranslationTestCase(SeleniumTranslationMixin, unittest.TestCase):
    pass
