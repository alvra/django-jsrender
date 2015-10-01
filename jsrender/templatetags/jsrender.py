from django import template
from ..translate import Translator
from ..context import TemplateFunction
from ..functions import js_is_variable


class TemplateRenderNode(template.Node):
    def __init__(self, function, arguments, nodelist, varname=None):
        self.function = function
        self.arguments = arguments
        self.nodelist = nodelist
        self.varname = varname

    def render(self, context):
        translator = Translator(self.arguments)
        body = translator.translate(context, self.nodelist)
        func = TemplateFunction(
            self.function, self.arguments, translator.arg_varnames,
            self.nodelist, body, context,
        )
        if self.varname is None:
            return func.script
        else:
            context[self.varname] = func
            return ''


class TemplateExecuteNode(template.Node):
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments

    def render(self, context):
        tpl = context.get(self.name)
        if tpl is None:
            raise template.VariableDoesNotExist(self.name)
        context.update(dict(
            (k, v.resolve(context))
            for k, v in self.arguments.items()
        ))
        x = tpl.render()
        context.pop()
        return x


def template_render(parser, token):
    parts = token.split_contents()
    tag_name = parts[0]
    try:
        function = parts[1]
        rest = parts[2:]
    except (IndexError, ValueError):
        raise template.TemplateSyntaxError(
            "%s tag requires one argument, with an optional 'as varname'"
            % tag_name
        )
    # extract function signature
    if not (function[0] == function[-1] and function[0] in ('"', "'")):
        raise template.TemplateSyntaxError(
            "%s tag's function signature argument should be in quotes"
            % tag_name
        )
    function = function[1:-1]
    if '(' not in function or ')' not in function:
        raise template.TemplateSyntaxError(
            "%s tag's function signature should contain "
            "arguments in parentheses"
            % tag_name
        )
    funcname, argstr = function.split('(', 1)
    argstr = argstr[:-1]
    if argstr == '':
        args = []
    else:
        args = [x.strip() for x in argstr.split(',')]
    if not all(map(js_is_variable, args)):
        raise template.TemplateSyntaxError(
            "%s tag's function signature should contain "
            "valid javascript arguments"
            % tag_name
        )
    # extract varname
    if len(rest) == 0:
        varname = None
    elif len(rest) == 2:
        if rest[0] != 'as':
            raise template.TemplateSyntaxError(
                "%s tag requires one argument, with an optional 'as varname'"
                % tag_name
            )
        else:
            varname = rest[1]
    else:
        raise template.TemplateSyntaxError(
            "%s tag requires one argument, with an optional 'as varname'"
            % tag_name
        )
    # extract subnodes in body
    nodelist = parser.parse(('endjsrender',))
    parser.delete_first_token()
    # done
    return TemplateRenderNode(funcname, args, nodelist, varname)


def template_execute(parser, token):
    parts = token.split_contents()
    tag_name = parts[0]
    try:
        varname = parts[1]
        rest = parts[2:]
    except (IndexError, ValueError):
        raise template.TemplateSyntaxError(
            "%s tag requires one argument, "
            "with optional extra values as 'with x=1'"
            % tag_name
        )
    # check template name
    if varname[0] in '\'"' or varname[-1] in '\'"':
        raise template.TemplateSyntaxError(
            "%s tag's template argument cannot be a string literal"
            % tag_name
        )
    # extract extra arguments
    if len(rest) > 0:
        if (
            rest[0] != 'with' or
            len(rest) == 1 or
            any(r.count('=') != 1 for r in rest[1:])
        ):
            raise template.TemplateSyntaxError(
                "%s tag requires one argument, "
                "with optional extra values as 'with x=1'"
                % tag_name
            )
        arglist = rest[1:]
        args = [a.split('=', 1) for a in arglist]
        arguments = dict((k, template.Variable(v)) for k, v in args)
    else:
        arguments = dict()
    # done
    return TemplateExecuteNode(varname, arguments)


register = template.Library()
register.tag('jsrender', template_render)
register.tag('jsexecute', template_execute)
