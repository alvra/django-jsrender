import os
import sys
import unittest
import django
try:
    from django import setup
except ImportError:
    # django < 1.7
    setup = None


def main():
    os.environ['DJANGO_SETTINGS_MODULE'] = 'test_settings'
    if setup:
        setup()
    import jsrender.tests
    unittest.main(jsrender.tests)


if __name__ == '__main__':
    main()
