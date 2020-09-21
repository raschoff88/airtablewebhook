from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangowebsite.settings')

app = Celery('djangowebsite')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'add-every-30-mins': {
        'task': 'airtablewebhook.tasks.runUpdatesOnAirtable',
        'schedule': 1800.0,
    },
    #'add-every-morning-at-3':{
    #    'task': 'airtablewebhook.tasks.runDailyReport',
    #    'schedule': crontab(hour = 7)
    #}
}

app.conf.timezone = 'EST'