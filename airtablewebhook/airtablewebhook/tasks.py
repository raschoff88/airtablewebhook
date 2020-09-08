from __future__ import absolute_import, unicode_literals
from .SalesforceEventHandler import handleRouteUpdate, handleRouteDelete
from celery import shared_task
from djangowebsite.celery import app


@shared_task
def updateRoute(request):
    return handleRouteUpdate(request)

@shared_task
def deleteRoute(request):
    return handleRouteDelete(request)

'''
from .periodic import pollAirtableForUpdates
@shared_task
def updateAirtable():
    return pollAirtableForUpdates()
'''
@shared_task
def add(x, y):
    return x + y

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every 30 minutes
    sender.add_periodic_task(
        crontab(minute=30),
        runUpdatesOnAirtable.s()
    )
    sender.add_periodic_task(
        crontab(hour = 3),
        runDailyReport.s()
    )

from .periodic import pollAirtableForUpdates, updateDailyReport
@app.task
def runUpdatesOnAirtable():
    return pollAirtableForUpdates()

@app.task
def runDailyReport():
    return updateDailyReport()

