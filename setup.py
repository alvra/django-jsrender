from setuptools import setup


setup(
    name='django-jsrender',
    version='0.1',
    description='Render Django templates into Javascript functions.',
    author='Alexander van Ratingen',
    author_email='alexander@van-ratingen.nl',
    url='https://github.com/AJHMvR/django-jsrender',
    packages=[
        'jsrender',
        'jsrender.templatetags',
        'jsrender.tests',
    ],
    package_data={'': [
        'templates/jsrender/*.js',
        'templates/jsrender/*.html',
    ]},
    install_requires=[
        'django>=1.6',
        'six',
    ],
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ],
)
