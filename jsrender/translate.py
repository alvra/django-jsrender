from __future__ import unicode_literals
import operator
from contextlib import contextmanager
import six
from django.conf import settings
from django.template import defaulttags
from django.template.base import FilterExpression, TextNode, VariableNode
from django.template.smartif import TokenBase, Literal
from .functions import (
    as_javascript, express, escape, mark_safe,
    concatenate, make_jsexpr, is_jsexpr, is_escaped,
)
from .tags import tag_translators
from .filters import filter_translators


def get_next_varname(v, recurse=False):
    "Get the next unique Javascript variable name in order, given the previous."
    if len(v) == 1:
        if v == 'z':
            return 'A'
        elif v == 'Z':
            if recurse:
                return '0'
            else:
                return 'aa'
        elif v == '9':
            assert recurse
            return 'aa'
        else:
            return six.unichr(ord(v) + 1)
    else:
        pre, last = v[:-1], v[-1]
        next = get_next_varname(last, recurse=True)
        if len(next) == 1:
            return pre + next
        else:
            # We can improve this and allow for arbitrary many variables
            # but this should be plenty for most reasonable uses.
            raise ValueError('Out of variable names')


class Translator(object):
    "Translates Django template nodelists into Javascript function bodies."

    html_escape_function = getattr(settings, 'JSRENDER_ESCAPE_FUNCTION', 'html_escape')

    comparison_operator_functions = {
        '==': operator.__eq__,
        '!=': operator.__ne__,
        '>=': operator.__ge__,
        '<=': operator.__le__,
        '>': operator.__gt__,
        '<': operator.__lt__,
    }
    comparison_operator_expressions = {
        '==': '%s===%s',
        '!=': '%s!=%s',
        '>=': '%s>=%s',
        '<=': '%s<=%s',
        '>': '%s>%s',
        '<': '%s<%s',
    }

    tag_translators = tag_translators
    filter_translators = filter_translators

    def __init__(
            self,
            arguments,
            html_escape_function=None, joiner=None, indentation=None, debug=None):
        """Create a new translator.

        Translation is based on the Javascript template arguments,
        which are considered dynamic when creating the Javascript function.
        As such, they are not required to be given in the template context,
        if they are, their context values will be ignored.
        All other variables found when translating the nodelist
        should be present in the template context.

        The optional debug argument can be used to override the global
        django DEBUG setting, which affects only the markup of the
        resulting Javascript function body to be more readable.
        With debug set to False, instead, the resulting Javascript code
        will be as compact as possible.
        """
        self.arguments = arguments
        self.current_varname = 'a'
        self.result_varname = self.get_varname()
        self.arg_varnames = [self.get_varname() for _ in self.arguments]
        if html_escape_function is not None:
            self.html_escape_function = html_escape_function
        self.indentation_text = indentation
        self.joiner = joiner
        self.debug = debug
        if self.debug is None:
            self.debug = settings.DEBUG
        if self.indentation_text is None:
            self.indentation_text = '  ' if self.debug else ''
        if self.joiner is None:
            self.joiner = '\n' if self.debug else ''
        self.indentation_level = 0

    def get_invalid_varnames(self):
        "Returns a set of varnames to skip."
        return set(['if', 'else', 'while', 'for', 'var', 'function', self.html_escape_function])

    def get_varname(self):
        "Obtain a new unique variable name."
        invalids = self.get_invalid_varnames()
        varname = self.current_varname
        while varname in invalids:
            varname = get_next_varname(varname)
        # set current varname to the next one for the following invocation
        self.current_varname = get_next_varname(varname)
        return varname

    @contextmanager
    def redirect_writing(self, varname):
        """A context manager to redirect writing the output to the given
        variable instead of to the Javascript function output.

        This is useful for tags that have the option to output to
        a variable like for example `{% now "Y" as year %}`.
        Every write (using `translator.write`) that is yielded
        during the context manager, is instead written to the variable.
        """
        old_varname = self.result_varname
        self.result_varname = varname
        yield
        self.result_varname = old_varname

    def indent(self):
        """Increase the indentation by one level.

        Make sure to restore the indentation level later using dedent(),
        Implementations are recommended to use the indented() context manager
        to ensure indentation is restored.
        """
        self.indentation_level += 1

    def dedent(self):
        """Decrease the indentation by one level.

        Only use when the indentation level has previously
        been increased using indent().
        """
        self.indentation_level -= 1
        if self.indentation_level < 0:
            raise AssertionError("Too many dedents")

    @contextmanager
    def indented(self):
        """A context manager to indent part of the Javascript by one level."""
        self.indent()
        yield
        self.dedent()

    @property
    def indentation(self):
        "Returns the current indentation level."
        return self.indentation_text * self.indentation_level

    def indent_line(self, line):
        "Indent a line according to the current indentation level."
        assert isinstance(line, six.text_type)
        return '%s%s' % (self.indentation, line)

    def escape(self, x):
        "Escape a Javascript expression or text."
        return escape(self.html_escape_function, x)

    def concatenate(self, x):
        "Build a new Javascript expression by concatenating expressions and text."
        return concatenate(self.html_escape_function, x)

    def write(self, x):
        "Make the Javascript function output a value or expression."
        if is_jsexpr(x):
            w = self.escape(x).expression
        elif isinstance(x, six.text_type):
            if x == '':
                return ''
            w = as_javascript(self.escape(x))
        elif isinstance(x, six.binary_type):
            raise TypeError(x)
        else:
            w = '"%s"' % self.escape(as_javascript(x))
        return '%s+=%s;' % (self.result_varname, w)

    def assign(self, varname, x):
        "Assign a variable a value in the Javascript function body."
        return 'var %s=%s;' % (varname, express(x))

    def resolve_expression(self, expression, context):
        "Resolves an expression into a value."
        if isinstance(expression, Literal):
            expression = expression.value
        assert isinstance(expression, FilterExpression)
        value = expression.var.resolve(context)
        for func, args in expression.filters:
            args = [a.resolve(context) if l else a for l, a in args]
            value = self.translate_filter(value, func, args)
        return value

    def resolve_condition(self, condition, context):
        "Resolves a condition into a value."
        if isinstance(condition, defaulttags.TemplateLiteral):
            return self.resolve_expression(condition, context)
        assert isinstance(condition, TokenBase) and type(condition).__name__ == 'Operator'
        first_var, second_var = condition.first, condition.second
        first = self.resolve_condition(first_var, context)
        second = self.resolve_condition(second_var, context) if second_var is not None else None
        if condition.id in self.comparison_operator_functions:
            if is_jsexpr(first) or is_jsexpr(second):
                js = self.comparison_operator_expressions[condition.id]
                return make_jsexpr(js, first, second)
            else:
                func = self.comparison_operator_functions[condition.id]
                return func(first, second)
        elif condition.id == 'not':
            assert second is None
            if is_jsexpr(first):
                return make_jsexpr('!(%s)', first)
            else:
                return not first
        elif condition.id == 'and':
            if is_jsexpr(first) and is_jsexpr(second):
                return make_jsexpr('%s&&%s', first, second)
            elif is_jsexpr(first):
                if second:
                    return first
                else:
                    return False
            elif is_jsexpr(second):
                if first:
                    return second
                else:
                    return False
            else:
                return first and second
        elif condition.id == 'or':
            if is_jsexpr(first) and is_jsexpr(second):
                return make_jsexpr('%s||%s', first, second)
            elif is_jsexpr(first):
                if second:
                    return True
                else:
                    return first
            elif is_jsexpr(second):
                if first:
                    return True
                else:
                    return second
            else:
                return first or second
        elif condition.id in ['in', 'not in']:
            if is_jsexpr(first) or is_jsexpr(second):
                return make_jsexpr(
                    '(%%s).indexOf(%%s)%s-1' % ('!=' if condition.id == 'in' else '=='),
                    second,
                    first,
                )
            else:
                if condition.id == 'in':
                    return first in second
                else:
                    return first not in second
        else:  # pragma: no cover
            raise NotImplementedError(
                "Javascript translation is not implemented for "
                "'%s' operators in 'if' blocks." % condition.id
            )

    def translate(self, context, nodelist):
        """The public translation method to translate a nodelist,
        given the template context, into a Javascript function body.
        """
        # the list holding the Javascript bits
        x = []

        # add the template arguments to the context
        context.push()
        for arg, varname in zip(self.arguments, self.arg_varnames):
            context[arg] = make_jsexpr(varname)

        # declare, fill and return the Javascript variable
        # to build the template in
        x.append(self.indent_line('var %s="";' % self.result_varname))
        x.extend(map(self.indent_line, self.translate_nodelist(context, nodelist)))
        x.append(self.indent_line("return %s;" % self.result_varname))

        # remove the template arguments from the context again
        context.pop()

        return self.joiner.join(x)

    def translate_nodelist(self, context, nodelist):
        """Returns an iterable of lines of the translation of the list of nodes.

        This can be used in tag translation implementations to translate subnodes.
        """
        for node in nodelist:
            pre_level = self.indentation_level
            for part in self.translate_node(context, node):
                if not isinstance(part, six.text_type):
                    raise TypeError("Non text %r from %r" % (part, node))
                if part != '':
                    yield part
            post_level = self.indentation_level
            if pre_level != post_level:
                raise AssertionError(
                    "Indentation level not restored by %r, going from %s to %s"
                    % (node, pre_level, post_level)
                )

    def translate_node(self, context, node):
        """Returns an iterable of lines of the translation of the node.

        This can be used in tag translation implementations to translate a subnode.
        """
        if isinstance(node, TextNode):
            text = node.render(context)
            yield self.write(mark_safe(text))
        elif isinstance(node, VariableNode):
            value = self.resolve_expression(node.filter_expression, context)
            if value != '':
                yield self.write(value)
        elif type(node) in self.tag_translators:
            translator = self.tag_translators[type(node)]
            for part in translator(self, context, node):
                yield part
        elif hasattr(node, 'render_javascript'):
            # third-party template nodes can be made compatible
            # by implementing a method 'render_javascript'
            # that builds itself rendered into a Javascript expression
            for part in node.render_javascript(self, context):
                yield part
        else:
            raise NotImplementedError(
                "Javascript translation is not implemented for "
                "%r nodes." % node.__class__
            )

    def translate_filter(self, value, func, args):
        "Translate a filter into Javascript."
        # if the arguments are not expressions,
        # we can apply the filter function directly
        if (
            not is_jsexpr(value) and
            all(not is_jsexpr(a) for a in args)
        ):
            return func(value, *args)
        # otherwise, translate the filter's functionality into javascript
        translator = None
        # first check if we know any translations for it
        try:
            translator = self.filter_translators[func]
        except KeyError:
            pass
        # then ask the filter itself
        if translator is None:
            try:
                # third-party filters can be made compatible
                # by implementing a callable attribute 'render_javascript'
                # that returns itself rendered into a Javascript expression
                return func.render_javascript(value, *args)
            except AttributeError:
                raise NotImplementedError(
                    "Javascript translation is not implemented for "
                    "%s filters." % func
                )
        # translate the filter
        result = translator(value, *args)
        if isinstance(result, list):
            return self.concatenate(result)
        else:
            return result
