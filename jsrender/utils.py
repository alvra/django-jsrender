import os.path
import re


html_escape_function_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'templates',
    'jsrender',
    'html_escape.js',
)

function_def = re.compile(r'function\s*([a-zA-Z_]+)\s*\(')


def html_escape_function(funcname='html_escape'):
    """Returns a Javascript escape function.

    By default, it's called 'html_escape',
    pass a different name to override that.
    """
    with open(html_escape_function_path, 'r') as f:
        content = f.read()
    match = function_def.match(content)
    assert match is not None
    if match.group(1) == funcname:
        return content
    else:
        return 'function %s%s' % (funcname, content[match.end(1):])
