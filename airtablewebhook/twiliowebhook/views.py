from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from functools import wraps
from twilio import twiml
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import datetime
import os
from simple_salesforce import Salesforce
from airtablewebhook.models import AirtableEntry
from .periodic import phone_format




def validate_twilio_request(f):
    """Validates that incoming requests genuinely originated from Twilio"""
    @wraps(f)
    def decorated_function(request, *args, **kwargs):
    # Create an instance of the RequestValidator class
        validator = RequestValidator(os.environ.get('TWILIO_AUTH_SID'))
        # Validate the request using its URL, POST data,
        # and X-TWILIO-SIGNATURE header
        request_valid = validator.validate(
            request.build_absolute_uri(),
            request.POST,
            request.META.get('HTTP_X_TWILIO_SIGNATURE', ''))

        # Continue processing the request if it's valid, return a 403 error if
        # it's not
        if request_valid:
            return f(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()
    return decorated_function

@require_POST
@csrf_exempt
@validate_twilio_request
def sms(request):
    time=datetime.datetime.today()
    """Twilio Messaging URL - receives incoming messages from Twilio"""
    # Create a new TwiML response

    deliveries = AirtableEntry.objects.all()
    print(request.POST['From'])
    match = next((delivery.stop_name for delivery in deliveries if delivery.stop_phone_number and phone_format(delivery.stop_phone_number)==phone_format(str(request.POST['From']))), None)

    if not match:
        sf = Salesforce(username = os.environ["SALESFORCE_OAUTH_USERNAME"], password = os.environ["SALESFORCE_OAUTH_PASSWORD"], security_token = os.environ['SALESFORCE_SECURITY_TOKEN'])
        result = sf.query(f"SELECT Name FROM Account WHERE Phone = '{phone_format(request.POST['From'])}' LIMIT 1")
        if result["totalSize"] >= 1:
            match = result["records"][0]["Name"]
        else:
            match = request.POST['From']



    message = Mail(
        from_email='info@tribecabeverage.com',
        to_emails='info@tribecabeverage.com',
        subject=f"Text Message from {match}",
        html_content=f"""Text message received at  {time.month}/{time.day}/{time.year}, {time.hour}:{time.minute}:{time.second} from <strong>{match} ({request.POST['From']})</strong>:\n\
        <strong>"{request.POST['Body']}\"</strong>""")
    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    response = sg.send(message)

    resp = MessagingResponse()

    # <Message> a text back to the person who texted us
    body = "For changes in delivery or questions, please email us at support@tribecabeverage.com"

    resp.message(body)

    # Return the TwiML

    return HttpResponse(resp)