from django.test import SimpleTestCase
from django.template import Context, VariableDoesNotExist, TemplateSyntaxError
from ..templatetags.jsrender import TemplateRenderNode, TemplateFunction
from .utils import TranslationMixin, template_from_string, nodelist_from_string


class TemplateTagTests(TranslationMixin, SimpleTestCase):
    def test_define_tag(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename()" %}hello{% endjsrender %}
        """
        ctx = {}
        t = template_from_string(tpl)
        defnode = t.nodelist[3]
        self.assertIsInstance(defnode, TemplateRenderNode)
        self.assertEqual(defnode.function, 'thename')
        self.assertEqual(defnode.arguments, [])
        self.assertEqual(defnode.varname, None)

        c = Context(ctx)
        res = t.render(c)

        self.assertJsEqual(
            res.strip(),
            '<script>'
            'function thename()'
            '{var a="";a+="hello";return a;}'
            '</script>'
        )

        self.assertJsEqual(
            res.strip(),
            '<script>'
            'function thename()'
            '{var a="";a+="hello";return a;}'
            '</script>'
        )

    def test_define_tag_with_arguments(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename(arg, bal)" %}hello {{ arg }}{% endjsrender %}
        """
        ctx = {}
        t = template_from_string(tpl)
        defnode = t.nodelist[3]
        self.assertIsInstance(defnode, TemplateRenderNode)
        self.assertEqual(defnode.function, 'thename')
        self.assertEqual(defnode.arguments, ['arg', 'bal'])
        self.assertEqual(defnode.varname, None)

        c = Context(ctx)
        res = t.render(c)

        self.assertJsEqual(
            res.strip(),
            '<script>'
            'function thename(b,c)'
            '{var a="";a+="hello ";a+=html_escape(b);return a;}'
            '</script>'
        )

        self.assertJsEqual(
            res.strip(),
            '<script>'
            'function thename(b,c)'
            '{var a="";a+="hello ";a+=html_escape(b);return a;}'
            '</script>'
        )

    def test_define_tag_as_variable(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename(arg, bal)" as spam %}hello {{ arg }}{% endjsrender %}
        {{ spam }}
        """
        ctx = {}
        t = template_from_string(tpl)
        defnode = t.nodelist[3]
        self.assertIsInstance(defnode, TemplateRenderNode)
        self.assertEqual(defnode.function, 'thename')
        self.assertEqual(defnode.arguments, ['arg', 'bal'])
        self.assertEqual(defnode.varname, 'spam')

        c = Context(ctx)
        res = t.render(c)

        func = ctx['spam']
        self.assertIsInstance(func, TemplateFunction)
        self.assertEqual(func.funcname, 'thename')
        self.assertEqual(func.arguments, ['arg', 'bal'])
        self.assertEqual(func.varnames, ['b', 'c'])
        self.assertJsEqual(func.body, 'var a="";a+="hello ";a+=html_escape(b);return a;')
        self.assertEqual(repr(func), '<TemplateFunction thename(arg, bal)>')
        self.assertMultiLineEqual(str(func), func.script)
        self.assertMultiLineEqual(res.strip(), func.script.strip())

        self.assertJsEqual(
            res.strip(),
            '<script>'
            'function thename(b,c)'
            '{var a="";a+="hello ";a+=html_escape(b);return a;}'
            '</script>'
        )

    def test_define_tag_missing_quotes_around_signature(self):
        tpl = """
        {% load jsrender %}

        {% jsrender thename(arg, bal) %}hello {{ arg }}{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag's function signature argument "
            "should be in quotes"
        ):
            nodelist_from_string(tpl)

    def test_define_tag_missing_parentheses_around_arguments(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename" %}hello {{ arg }}{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag's function signature should "
            "contain arguments in parentheses"
        ):
            nodelist_from_string(tpl)

    def test_define_tag_invalid_no_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender %}hello {{ arg }}{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag requires one argument, "
            "with an optional 'as varname'"
        ):
            nodelist_from_string(tpl)

    def test_define_tag_invalid_extra_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename(arg, bal)" ham %}hello {{ arg }}{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag requires one argument, "
            "with an optional 'as varname'"
        ):
            nodelist_from_string(tpl)

    def test_define_tag_invalid_two_extra_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename(arg, bal)" ham spam %}hello {{ arg }}{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag requires one argument, "
            "with an optional 'as varname'"
        ):
            nodelist_from_string(tpl)

    def test_define_tag_invalid_signature_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "thename(1)" %}hello{% endjsrender %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsrender tag's function signature should "
            "contain valid javascript arguments"
        ):
            nodelist_from_string(tpl)

    def test_render_tag(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "greetme()" as greeting %}hello{% endjsrender %}

        {% jsexecute greeting %}
        """
        ctx = {}
        t = template_from_string(tpl)
        defnode = t.nodelist[3]
        self.assertIsInstance(defnode, TemplateRenderNode)
        self.assertEqual(defnode.function, 'greetme')
        self.assertEqual(defnode.arguments, [])
        self.assertEqual(defnode.varname, 'greeting')

        c = Context(ctx)
        res = t.render(c)

        func = ctx['greeting']
        self.assertIsInstance(func, TemplateFunction)
        self.assertEqual(func.funcname, 'greetme')
        self.assertEqual(func.arguments, [])
        self.assertEqual(func.varnames, [])
        self.assertJsEqual(func.body, 'var a="";a+="hello";return a;')
        self.assertEqual(repr(func), '<TemplateFunction greetme()>')
        self.assertMultiLineEqual(str(func), func.script)

        self.assertEqual(res.strip(), "hello")

    def test_render_tag_with_extra_variables(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "greetme(where)" as greeting %}hello {{ where }}{% endjsrender %}

        {% jsexecute greeting with where="World" %}
        """
        ctx = {}
        t = template_from_string(tpl)
        defnode = t.nodelist[3]
        self.assertIsInstance(defnode, TemplateRenderNode)
        self.assertEqual(defnode.function, 'greetme')
        self.assertEqual(defnode.arguments, ['where'])
        self.assertEqual(defnode.varname, 'greeting')

        c = Context(ctx)
        res = t.render(c)

        func = ctx['greeting']
        self.assertIsInstance(func, TemplateFunction)
        self.assertEqual(func.funcname, 'greetme')
        self.assertEqual(func.arguments, ['where'])
        self.assertEqual(func.varnames, ['b'])
        self.assertJsEqual(func.body, 'var a="";a+="hello ";a+=html_escape(b);return a;')
        self.assertEqual(repr(func), '<TemplateFunction greetme(where)>')
        self.assertMultiLineEqual(str(func), func.script)

        self.assertEqual(res.strip(), "hello World")

    def test_render_tag_invalid_no_arguments(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "greetme(where)" as greeting %}hello {{ where }}{% endjsrender %}

        {% jsexecute %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsexecute tag requires one argument, "
            "with optional extra values as 'with x=1'"
        ):
            nodelist_from_string(tpl)

    def test_render_tag_invalid_extra_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "greetme(where)" as greeting %}hello {{ where }}{% endjsrender %}

        {% jsexecute greeting ham %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsexecute tag requires one argument, "
            "with optional extra values as 'with x=1'"
        ):
            nodelist_from_string(tpl)

    def test_render_tag_invalid_literal_argument(self):
        tpl = """
        {% load jsrender %}

        {% jsrender "greetme(where)" as greeting %}hello {{ where }}{% endjsrender %}

        {% jsexecute "greeting" %}
        """
        with self.assertRaisesRegex(
            TemplateSyntaxError,
            "jsexecute tag's template argument cannot be a string literal"
        ):
            nodelist_from_string(tpl)

    def test_render_tag_missing_template(self):
        tpl = """
        {% load jsrender %}

        {% jsexecute greeting with where="World" %}
        """
        ctx = {}
        t = template_from_string(tpl)
        c = Context(ctx)

        with self.assertRaisesRegex(VariableDoesNotExist, "greeting"):
            t.render(c)
