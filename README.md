# Django-Jsrender

This is a Django app to translate parts of your standard Django templates
directly and identically into Javascript, and thus, avoiding the need for
a second template library in Javascript.


## Introduction

Let's start with an example.

```html
{% load jsrender %}

<h1>Hello {{ name }}</h1>

<script>
    {% jsrender "greet()" %}
        Welcome {{ name }}
    {% jsrender %}
</script>
```

When rendering this template, the `jsrender`
tag will translate its content into a Javascript function which returns
exactly the same result as rendering its content directly
(ie. without the `jsrender` tag).
Its only required argument is the Javascript function signature.
The rest of the template, of course, is rendered as normal.
This will render into something equivalent to the following,
when given a context where `name` equals `you`.

```html
<h1>Hello you</h1>

<script>
    function greet() {
        return "Welcome you";
    }
</script>
```

Admittedly, that was a silly example as its result could be achieved much simpler,
so let's introduce variables to the Javascript function to make this
a bit more interesting and useful.

```html
{% load jsrender %}
<script>
    {% jsrender "greet(name)" %}
        Welcome {{ name }}
    {% endjsrender %}
</script>
```

Notice we added the name variable to the Javscript function signature
in the `jsrender` tag.
Now, anytime you reference this variable `name` inside the `jsrender` tag,
it won't be taken from the template context (even if it's in the context)
but from the argument you pass to the Javascript function.
The result is equivalent to the following.
(Note that the name is escaped, as it would be if rendered by Django.)

```html
<script>
    function greet(name) {
        return "Welcome " + html_escape(name);
    }
</script>
```

One thing these simple examples didn't show, was that you can use
nearly all Django template features when creating Javascript functions.
This includes things like attribute access (ie. `user.name`),
control flow using `if` and `for` tags,
and most of the other builtin tags and filters.



## Goals and Limitations

This library aims to be fully compatible with the entire Django
template language, and any and all builtin and third-party tags and filters,
as long as they make sense and are possible inside Javascript and on the client side.

Ideally, you should be able to take an existing template,
place it in `jsrender` tags, and be able to use it on the clientside.
The result should be a simple function which produces exactly the same
result as the original template, when given the same arguments.

The resulting Javascript function is made as compact as possible
to avoid the need to compress it furthermore. This means the Javascript
code is not very readable. To aid debugging the function or its arguments, a somewhat
more readable version is created when the Django `DEBUG` setting is set to true.

That said, translation of Django templates to Javascript does pose limitations.
Note that you can still use all of these features outside of the `jsrender` tag.

  * The equivalence of the Django and Javascript templates
    relies on the assumtion that corresponding value types in Python and Javascript
    have the exact same behavior. For most simple values, this will
    hold true under most circumstances. But care must be taken
    in cases where this assumptions fails.

    For example, number comparisions behave identical.
    Whereas, even simple things like comparing numbers to strings
    can behave very different.

    Another notable difference is in the representation of values.
    This is usually not a issue since you rarely want to
    display types like lists or dictionairies directly to users,
    and when you do, the exact formatting doesn't usually matter.
    For most common use cases, this can easily be worked around.

    This app does not try to abstract any such differences away, and,
    thus, when writing a Django template that will be translated
    and then used as Javascript, one must always be aware of such
    differences.
    For the most part, translation uses the most logical equivalent
    expressions in Javascript, without ever preforming any 'magic'.
    This keeps the Javascript function minimal, but also more predictable.
    As a guideline, is probably best to restrict arguments
    to simple json encodable data.
    This also means that, occasionally, some knowledge of the Javascript
    generated in translation is required.

    Refer to the section on common pitfalls for more information.

  * Variables in tags or filters where rendering depends on
    information that is unavailable in the client.

    This includes, but is not limited to, the following.
    Implementations of Javascript translation for third-party or custom
    tags and filters, are also affected by this.

      * Variable url generation.
        You can use the `url` tag just fine, but any variable arguments
        are taken from the context instead of from Javascript function arguments.
      * Variable translation.
        As with the `url` tag, the `trans` and `blocktrans` tags
        take their arguments from the context.
      * Server local times.
        Any local date or time that must be generated in Javascript
        will be in the timezone of the client instead of the server.
      * Variable timezones in any way.
        All dates and times must be convertable to the user timezone on the server.
        The generated Javascript will not handle timezone conversion.
      * Variable static files.
        As with the `url` tag, the `static` tag
        takes its arguments from the context.
      * Server side debug information using the `debug` tag.
      * Server side includes using the `ssi` tag.
        This tag is deprecated anyway.

  * Variable template structures.

    Using `extends` and `block` tags, it's possible to construct
    templates which extend from variable other templates.
    Such constructs are not allowed inside Javascript templates.

  * Loading template tags using the `load` tag.

    You should use this tag at the start of your template
    outside of the Javascript function definition.

All other Django template tags and filters should be translatable
to equivalent constructs in Javascript on the clientside,
although, not everything is currently implemented.
Please submit a pull request if you find anything's missing.


## Documentation


### Requirements

This pure python module supports both version 2 and 3,
including alternative implementations like Pypy, as long as it's supported by Django.

In addition to requiring Django, it depends on the Python module `six` to support both
Python 2 and 3 in one codebase (as does Django itself). Installing with pip will also install
this dependency, although you probably got it along with Django.

  * Python (2.6, 2.7, 3.3, 3.4 or 3.5)
  * Django (1.6 or later)
  * Six



### Installation

Install with pip.

```shell
$ pip install django-jsrender
```

Or, alternatively, run `setup.py install` inside this directory.

Then update your django setting file to include this app
as installed to be able to use its template tags and templates.
(If you don't need its tags or templates, eg. because you're doing
the translation in your views, you don't need to do this.)

```python
# settings.py

INSTALLED_APPS = (
    # other apps
    'jsrender',
)
```

To escape text, this app relies on a Javascript function that must
be available on any page that renders Javascript template functions.
Set the `JSRENDER_ESCAPE_FUNCTION` setting to the name of your
escape function, or stick with the default name `html_escape`.

```python
# settings.py

JSRENDER_ESCAPE_FUNCTION = 'you_escape_function_name'
```

Make sure the escape function is available (by this name) on the client for
rendering translated templates to work.
For example, by including it in your base template.

```html
<!doctype html>
<html>
  <head>
    {% include "jsrender/html_escape.html" %}
  </head>
  <body>
    ...
  </body>
</html>
```

Refer to the section on escaping for more options on where
to obtain this function from, how to include it and more.

That's it! Just don't forget to load the template tags inside your templates.

```html
{% load jsrender %}

...
```



### Usage

This app provides two template tags. The first, `jsrender` is used
to render its content into a Javascript function. It takes one required argument;
the signature (both name and arguments) of the function to output.

```html
{% load jsrender %}
<script>
  {% jsrender "print_sudoku(sudoku, empty_value)" %}
    <table>
      {% for row in sudoku %}
        <tr>
          {% for value in row %}
            {% if value %}
              <td>{{ value }}</td>
            {% else %}
              <td class="empty">{{ empty_value|default:"&nbsp;" }}</td>
            {% endif %}
          {% endfor %}
        </tr>
      {% endfor %}
    </table>
  {% endjsrender %}
</script>
```

Optionally, you can render the Javascript function into a context variable.
You can then output the function anywhere you like
using the variable name.

```html
{% load jsrender %}

{% jsrender "foobar(ham, spam)" as jsfunc %}
    ...
{% endjsrender %}

<script>
  {{ jsfunc }}
</script>
```

With the Javascript function in a context variable, you can also render it
as the original Django template using the `jsexecute` tag.
The result is the same as if you removed the `jsrender` tags.
The Javascript function arguments are taken from the context by default,
or can be passed into the `jsexecute` tag.

```html
{% load jsrender %}

{% jsrender "foobar(ham, spam)" as jsfunc %}
    ...
{% endjsrender %}

<script>
  {{ jsfunc }}
</script>

{# takes ham and spam from the context #}
{% jsexecute jsfunc %}

{# takes ham from the context, and sets spam to 2 (regardless of context) #}
{% jsexecute jsfunc with spam=2 %}

{# sets ham and spam 1 and 2, regardless of context #}
{% jsexecute jsfunc with ham=1 spam=2 %}
```



### Common pitfalls

When writing Django templates that will be translated into Javascript,
always keep in mind the differences between Python and Javascript.
Use simple json encodable data to keep differences minimal,
and, in case of doubt, view the translation functions for tags and filters
in their respective files for details on their implementations.


#### A word on debugging Javascript templates

Set the Django `DEBUG` setting to true to obtain identical,
but somewhat more readable more Javascript functions when debugging them.
This will output every statement on a single line and includes indentation,
so the line numbers in your error messages will be a lot more helpful.



#### Iteration

Python allows you to iterate over many types, including builtins, using
the iterator protocol. In Javascript translation, iteration is preformed
by taking the length of the iterable (`iterable.length`), going over
every integer index from zero up to that length.

This means that iteration is reserved to Javascript Arrays,
and other objects that have a length property and can be indexed.



#### Boolean representation

The Python value `True` is represented as `true`
(no capitalization) in Javascript.

So, instead of `{{ boolean }}`, you should use
`{% if boolean %}True{% else %}False{% endif %}`
or `{{ boolean|yesno:"True,False" }}`



### Escaping

To escape text in Javascript functions, they rely on an external escaping function.
The name of this function can be changed by setting the Django setting
`JSRENDER_ESCAPE_FUNCTION`, it defaults to `html_escape`.

An implementation of this function can be found in `jsrender/templates/jsrender/html_escape.js`,
or with script tags around it in `jsrender/templates/jsrender/html_escape.html`.
This function can also be obtained in Python by calling `jsrender.utils.js_escape_function`,
optionally with the name you'd like the escape function to have.

Make sure you include this function, or your own implementation,
in all pages that render Javascript template functions, or else
calling these functions will not work.



### Custom filters

Filters can be made compatible by setting the `render_javascript` attribute
on the filter function itself. This attribute should be a function
that takes a value and any filter arguments, and returns a 
string (of type `six.text_type`) of its translation to a Javascript expression
of applying the filter to the value given the arguments.

When both the value and arguments are known, ie. they are context variables,
the filter is applied directly to them and there is no need
for translation to Javascript. However, if it depends on Javascript function
arguments, ie. they are context variables (if either the value of,
or an argument to the filter is an argument to the Javascript function,
or the result of applying another filter to one), the result needs to be
translated to a Javascript expression.

For example, in the following template, the filter values and arguments
can be taken from the context and we can apply the filter directly.
Thus, the `render_javascript` filter attribute of the filter (in this case `default`) does
not need to handle this case. Every filter is already compatible when
used this way.

```html
{% jsrender "example()" %}
    {{ value|default:"empty" }}
{% endjsrender %}
```

This changes when we pass Javascript function arguments, or anything
deriving thereof, to the filter,
as in the following examples. In this case, the filter must
be compatible.

```html
{% jsrender "example1(value)" %}
    {{ value|default:"empty" }}
{% endjsrender %}

{% jsrender "example2(alternative)" %}
    {{ value|default:alternative }}
{% endjsrender %}

{% jsrender "example3(value, alternative)" %}
    {{ value|default:alternative }}
{% endjsrender %}
```

The `render_javascript` filter attribute receives for the value
and each argument, either an object representing a Javascript expression,
or a regular Python value from the context or from applying another filter.
Then, it must again return either one of those.

To check if a value is a Javascript expression instead of a regular value,
implementations can use the `is_jsexpr` function from `jsrender.functions`.
To construct a Javascript expression, they can then use `make_jsexpr`
(also from `jsrender.functions`),
which takes a percent-format string and substutions and returns a Javascript expression.

By default, when outputting the result of a filter, the result is escaped
like it is in Django templates. If a translation returns an expression
or string value which is already escaped, it can mark it safe using `mark_safe`
from `jsrender.functions` to prevent double escaping.

```python
from django import template
from jsrender.functions import make_jsexpr
from jsrender.filters import register

django_register = template.Library()

@register.filter
def filter_multiply(value, arg):
    return value * arg

def translate_filter_multiply(value, arg):
    return make_jsexpr('%s*%s', value, arg)

filter_multiply.render_javascript = translate_multiply_filter
```

To see more examples of filter translation, have a look at the `jsrender/filters.py`
file to see how the builtin Django filters are implemented.



### Third-party filters

Third-party filters can be made compatible the same way as custom filters,
but sometimes it's not an option to set attributes on them directly.
To enable translation for these filters, there is the alternative
to register translation functions by decorating them with
`jsrender.filters.register`, passing the filter itself
as an argument to the decorator.

```python
from third_party import multiply_filter
from jsrender.functions import make_jsexpr
from jsrender.filters import register

@register(multiply_filter)
def translate_filter_multiply(value, arg):
    return make_jsexpr('%s*%s', value, arg)
```



### Custom tags

Tags can be made compatible by implementing the
`render_javascript` method on the template node.
This method receives two arguments, the Javascript translator
and the context, and should return an iterable of strings
(of type `six.text_type`) of its translation to lines of Javascript.

Translation can make use of several helper functions from `jsrender.functions`.
These include the helpers described for translating custom filters,
please refer to that part of the documentation for more information about
`is_jsexpr`, `make_jsexpr` and `mark_safe`.

  * `is_jsexpr(object)`

    Returns True if the argument is a Javascript expression.

  * `make_jsexpr(format_string, *args, **kwargs)`

    Returns a Javascript expression built by substituting
    the arguments in the format string.

    ```python
    make_jsexpr('Math.PI')
    make_jsexpr('%s + %s', value, another_value)
    make_jsexpr('%(x)s + %(y)s', x=value, y=another_value)
    ```

  * `mark_safe(value_or_expression)`

    Mark a value or Javascript expression as safe to avoid double escaping.

  * `express(value_or_expression)`

    Express a Python value in Javascript.

    ```python
    express(1) == '1'
    express([1, 2, 3]) == '[1,2,3]'
    express(datetime(...)) == 'new Date(...)'
    express(make_jsexpr('Math.PI')) == 'Math.PI'
    ```

Furthermore, the translator exposes a number of helpers.

  * `translator.resolve_expression(expression, context)`

    Resolves a template expression (ie. a template variable with optional filters)
    into a value or Javascript expression object.
    All filters that take variables should use this
    instead of `expression.resolve(context)` to resolve expressions.
    

  * `translator.write(text_or_expression)`

    Returns a Javascript expression to add the argument to the
    output. The argument can either be a string literal,
    or a Javascript expression.

  * `translator.assign(variable_name, value_or_expression)`

    Returns a Javascript expression to assign a value or Javascript expression
    to a variable.
    Variable names should be obtained from `translator.get_varname()`.

  * `translator.get_varname()`

    Returns a new unique variable name.

  * `translator.translate_nodelist(nodelist)`

    Returns an iterable of lines of the translation of the list of nodes.
    This can be used to translate subnodes.

  * `translator.redirect_writing(variable_name)`

    A context manager to redirect writing the output to the given
    variable instead of to the Javascript function output.

    This is useful for tags that have the option to output to
    a variable like for example `{% now "Y" as year %}`.
    Every write (using `translator.write`) that is yielded
    during the context manager, is instead written to the variable.

Additionally, to output more readable Javascript functions in debug mode,
translation functions can control indentation. This is entirely optional
and has no effect unless in debug mode.

  * `translator.indented`

    A context manager to indent part of the Javascript.
    Everything yielded during this context manager is indented one level.
    Afterwards, the original indentation level is restored.

  * `translator.indent()`

    Increase the indentation by one level.
    Make sure to restore the indentation level later using `dedent()`,
    Implementations are recommended to use the `indented()` context manager
    to ensure indentation is restored.

  * `translator.dedent()`

    Decrease the indentation by one level.
    Only use when the indentation level has previously
    been increased using `indent()`.

For example, a simple tag might have a `render_javascript` method like this.

```python
    class LessThanTwoNode(Node):
        ...

        def render_javascript(self, translator, context):
            yield 'if(number<2){'
            with translator.indented():
                yield translator.write('less than two')
            yield '}else{'
            with translator.indented():
                yield translator.write('at least two')
            yield '}'
```

To see more examples of these functions or tag translation in general,
have a look at the `jsrender/tags.py` file
to see how the builtin Django tags are implemented.



### Third-party tags

As with third-party filters, third-party tag translation functions
can also be registered. Decorate them with the `jsrender.tags.register`,
passing the tag's node type as an argument to the decorator.

```python
from third_party import MultiplyNode
from jsrender.functions import make_jsexpr
from jsrender.tags import register

@register(MultiplyNode)
def translate_tag_multiply(translator, context, node):
    yield make_jsexpr('%s*%s', node.first_argument, node.second_argument)
```



## License

See LICENSE file.
