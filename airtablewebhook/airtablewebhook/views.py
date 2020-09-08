from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os
from .tasks import updateRoute, deleteRoute
import base64
import redis 

r= redis.from_url(os.environ.get("REDIS_URL"))

@require_http_methods(["GET","POST"])
@csrf_exempt
def hook_receiver_view(request):
    AUTHENTICATED = False
    if "HTTP_AUTHORIZATION" in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            if auth[0].lower() == "basic":
                uname, passwd = str(base64.b64decode(auth[1].encode()),"utf-8").split(':')
                if uname == os.environ['SALESFORCE_USERNAME'] and passwd == os.environ['SALESFORCE_PASSWORD']:
                    AUTHENTICATED = True
    
    if AUTHENTICATED:
        jsondata = request.body
        data = json.loads(jsondata)

        switcher ={
            "ROUTE_UPDATED" : updateRoute,
            "ROUTE_DELETED" : deleteRoute,
        }
        p = switcher[data["Method"]].delay(data)
        p.get()
        return HttpResponse("Success")
    else:
        return HttpResponse("Username or Password Incorrect", status = 401)

@require_http_methods(["GET","POST"])
def salesforce_callback(request):
    print(request)
    return HttpResponse("Success")