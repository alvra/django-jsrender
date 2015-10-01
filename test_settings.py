DEBUG = True
TEMPLATE_DEBUG = DEBUG

SECRET_KEY = 'xxx'

INSTALLED_APPS = (
    'jsrender',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
    },
]
