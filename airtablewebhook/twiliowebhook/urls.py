from django.urls import re_path
from .views import sms 
urlpatterns=[
    re_path(r'^sms/$',sms)
]