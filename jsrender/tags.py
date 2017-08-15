from __future__ import unicode_literals
import six
from django.template import defaulttags, TemplateSyntaxError
from django.template.loader_tags import IncludeNode
from django.templatetags import i18n
from django.conf import settings
from django.utils.encoding import force_text
from .functions import mark_safe, express, make_jsexpr, is_jsexpr, JavascriptExpression
from . import datetimeformat
if hasattr(defaulttags, 'LoremNode'):
    LoremNode = defaulttags.LoremNode
else:
    from django.contrib.webdesign.templatetags.webdesign import LoremNode


tag_translators = {}


def register(filter):
    def _decorator(translator):
        assert filter not in tag_translators
        tag_translators[filter] = translator
        return translator
    return _decorator


@register(defaulttags.IfNode)
def translate_tag_if(translator, context, node):
    # Resolve the expressions for all branches.
    # This is needed to see if any branches
    # fall out or are guaranties to be executed
    # because they contain fixed variables.
    branches = []
    for n, (condition, nodelist) in enumerate(node.conditions_nodelists):
        if condition is not None:
            condition_expr = translator.resolve_condition(condition, context)
            if not is_jsexpr(condition_expr):
                # No need to keep the branches that are
                # guarantied not to be executed.
                if condition_expr:
                    # This branch is guarantied to be executed
                    # so the next branches certainly won't be.
                    # Store this one as the 'else' branch
                    # and omit any next branches.
                    branches.append((None, nodelist))
                    break
            else:
                branches.append((condition_expr, nodelist))
        else:
            branches.append((None, nodelist))
    if len(branches) == 0:
        # If there are no branches left that might be executed,
        # there's no need to write anything.
        return
    elif len(branches) == 1 and branches[0][0] is None:
        # If there's only one branch and it's the one
        # of the 'else' tag (condition == None),
        # then just write that one and we're done.
        for part in translator.translate_nodelist(context, branches[0][1]):
            yield part
        return
    for n, (condition, nodelist) in enumerate(branches):
        if n == 0:
            yield 'if(%s){' % express(condition)
        elif condition is not None:
            yield 'else if(%s){' % express(condition)
        else:
            yield 'else{'
        with translator.indented():
            for part in translator.translate_nodelist(context, nodelist):
                yield part
        yield '}'


class ForloopJavascriptExpression(JavascriptExpression):
    "The 'forloop' context value that is introduced by the 'for' tag."

    def __init__(self, varname, sequence, parent=None):
        assert isinstance(varname, JavascriptExpression)
        assert isinstance(sequence, JavascriptExpression)
        assert parent is None or isinstance(parent, ForloopJavascriptExpression)
        self._varname = varname
        self._sequence = sequence
        self._parent = parent

    @property
    def expression(self):
        raise TemplateSyntaxError(
            "Cannot output forloop itself to template, use one of it's arguments"
        )

    def __repr__(self):
        return '<ForloopValue>'

    def __getitem__(self, key):
        if key == 'counter':
            return make_jsexpr('%s+1', self._varname)
        elif key == 'counter0':
            return self._varname
        elif key == 'revcounter':
            return make_jsexpr('%s.length-%s', self._sequence, self._varname)
        elif key == 'revcounter0':
            return make_jsexpr('%s.length-%s-1', self._sequence, self._varname)
        elif key == 'first':
            return make_jsexpr('%s===0', self._varname)
        elif key == 'last':
            return make_jsexpr('%s===%s.length-1', self._varname, self._sequence)
        elif key == 'parentloop' and self._parent is not None:
            return self._parent
        else:
            raise KeyError(key)


@register(defaulttags.ForNode)
def translate_tag_for(translator, context, node):
    sequence = node.sequence
    # get the value we're looping over
    sequence_expr = translator.resolve_expression(sequence, context)
    if not is_jsexpr(sequence_expr):
        yield translator.write(node.render(context))
    else:
        # if the sequnce_expr is complex (ie: has filters),
        # store it in a variable and work with that
        if len(sequence.filters) > 0:
            newvar = translator.get_varname()
            yield translator.assign(newvar, sequence_expr)
            sequence_expr = make_jsexpr(newvar)
        # create the 'if' condition for empty loops if needed
        if node.nodelist_empty:
            yield 'if(%s.length==0){' % express(sequence_expr)
            with translator.indented():
                for part in translator.translate_nodelist(context, node.nodelist_empty):
                    yield part
            yield '}else{'
            translator.indent()
        # create the 'for' statement
        loop_varname = translator.get_varname()
        loop_var = make_jsexpr(loop_varname)
        if node.is_reversed:
            for_format = 'for(var %(n)s=%(seq)s.length-1;%(n)s>=0;%(n)s--){'
        else:
            for_format = 'for(var %(n)s=0;%(n)s<%(seq)s.length;%(n)s++){'
        yield for_format % dict(n=loop_varname, seq=express(sequence_expr))
        with translator.indented():
            context.push()
            # assign the loopvars
            loop_varnames = [translator.get_varname() for _ in node.loopvars]
            if len(loop_varnames) == 1:
                js = make_jsexpr('%s[%s]', sequence_expr, loop_var)
                yield translator.assign(loop_varnames[0], js)
                context[node.loopvars[0]] = make_jsexpr(loop_varnames[0])
            else:
                for n, vn in enumerate(loop_varnames):
                    yield translator.assign(
                        vn,
                        make_jsexpr('%s[%s][%s]', sequence_expr, loop_var, n),
                    )
                    context[node.loopvars[n]] = make_jsexpr(vn)
            # add the 'forloop' variable
            prev_forloop = context.get('forloop', None)
            context['forloop'] = ForloopJavascriptExpression(loop_var, sequence_expr, prev_forloop)
            # write the loop body
            for part in translator.translate_nodelist(context, node.nodelist_loop):
                yield part
            context.pop()
        # end loop
        yield '}'
        # finish the 'if' condition for empty loops if needed
        if node.nodelist_empty:
            translator.dedent()
            yield '}'


@register(defaulttags.NowNode)
def translate_tag_now(translator, context, node):
    if getattr(node, 'asvar', None) is not None:
        tempvar = translator.get_varname()
        yield 'var %s = "";' % tempvar
        newnode = defaulttags.NowNode(node.format_string)
        with translator.redirect_writing(tempvar):
            for part in translate_tag_now(translator, context, newnode):
                yield part
        context[node.asvar] = make_jsexpr(tempvar)
        return
    assert not is_jsexpr(node.format_string)
    if is_jsexpr(node.format_string):
        raise NotImplementedError(
            "Cannot translate now tags "
            "with variable format strings to Javascript"
        )
    varname = translator.get_varname()
    yield translator.assign(varname, make_jsexpr('new Date()'))
    format_string = node.format_string
    if format_string.endswith('_FORMAT'):
        format_string = six.text_type(getattr(settings, format_string))
    format_string = six.text_type(format_string)
    format_iterator = iter(format_string)
    for char in format_iterator:
        if char == '\\':
            yield translator.write(six.next(format_iterator))
        else:
            output = datetimeformat.get_datetime_format_javascript_expression(char)
            if output is None:
                yield translator.write(char)
            else:
                yield translator.write(mark_safe(make_jsexpr(
                    force_text(output),
                    x=make_jsexpr(varname)
                )))


@register(IncludeNode)
def translate_tag_include(translator, context, node):
    template = node.template.resolve(context)
    if is_jsexpr(template):
        raise NotImplementedError(
            "Cannot translate include tags "
            "with variable templates to Javascript"
        )
    if not callable(getattr(template, 'render', None)):
        # not a regular template, try loading it
        template = context.template.engine.get_template(template)
    elif hasattr(template, 'template'):
        # this branch is includes to mirror the implementation
        # of django's IncludeNode.render(...)
        template = template.template
    nodelist = template.nodelist
    values = {
        name: var.resolve(context)
        for name, var in node.extra_context.items()
    }
    if node.isolated_context:
        context = context.new()
    with context.push(values):
        for part in translator.translate_nodelist(context, nodelist):
            yield part


@register(defaulttags.FilterNode)
def translate_tag_filter(translator, context, node):
    tempvar = translator.get_varname()
    yield translator.assign(tempvar, '')
    with translator.redirect_writing(tempvar):
        for part in translator.translate_nodelist(context, node.nodelist):
            yield part
    with context.push(var=make_jsexpr(tempvar)):
        yield translator.write(translator.resolve_expression(node.filter_expr, context))


@register(LoremNode)
def translate_tag_lorem(translator, context, node):
    count = translator.resolve_expression(node.count, context)
    if is_jsexpr(count):
        raise NotImplementedError(
            "Cannot translate lorem tags "
            "with variable counts to Javascript"
        )
    yield translator.write(node.render(context))


@register(defaulttags.CommentNode)
@register(defaulttags.CsrfTokenNode)
@register(defaulttags.DebugNode)
@register(defaulttags.TemplateTagNode)
@register(defaulttags.URLNode)
@register(defaulttags.VerbatimNode)
@register(defaulttags.WithNode)
@register(i18n.TranslateNode)
@register(i18n.BlockTranslateNode)
def translate_static_tag(translator, context, node):
    text = node.render(context)
    if text != '':
        yield translator.write(text)


@register(defaulttags.LoadNode)
def translate_invalid_tag(translator, context, node):
    raise TemplateSyntaxError(
        "Node %s is not allowed inside a javascript template."
        % node.__class__
    )
