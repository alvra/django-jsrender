import unittest
from ..utils import html_escape_function


class UtilTests(unittest.TestCase):
    def test_html_escape_function_arg(self):
        res = html_escape_function('abc')
        self.assertTrue(
            res.startswith('function abc(string) {'),
            "Res %r does no start with 'function abc(string) {'" % res
        )

    def test_html_escape_function_noargs(self):
        res = html_escape_function()
        self.assertTrue(
            res.startswith('function html_escape(string) {'),
            "Res %r does no start with 'function abc(string) {'" % res
        )
