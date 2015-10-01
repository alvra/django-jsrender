from django.utils.html import mark_safe


class TemplateFunction(object):
    def __init__(self, funcname, arguments, varnames, nodelist, body, context):
        self.funcname = funcname
        self.arguments = arguments
        self.varnames = varnames
        self._nodelist = nodelist
        self.body = body
        self._context = context

    def __str__(self):
        return self.script

    def __unicode__(self):
        return self.script

    def __repr__(self):
        return '<TemplateFunction %s(%s)>' % (
            self.funcname,
            ', '.join(self.arguments),
        )

    @property
    def function(self):
        return mark_safe('function %s(%s){%s}' % (
            self.funcname,
            ','.join(self.varnames),
            self.body,
        ))

    @property
    def script(self):
        return mark_safe('<script>%s</script>' % self.function)

    def render(self):
        return self._nodelist.render(self._context)
