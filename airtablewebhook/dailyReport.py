import os
import django
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangowebsite.settings')
django.setup()

from airtablewebhook.tasks import runUpdatesOnAirtable


if __name__ == '__main__':
    try:
        runUpdatesOnAirtable()
    except Exception as e:
        message = Mail(
            from_email='info@tribecabeverage.com',
            to_emails='info@tribecabeverage.com',
            subject='Overnight Airtable Updating Error',
            html_content=f""" sent on  {time.month}/{time.day}/{time.year}, {time.hour}:{time.minute}:{time.second}
                An error occured when updating in the morning: {e}""")
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)