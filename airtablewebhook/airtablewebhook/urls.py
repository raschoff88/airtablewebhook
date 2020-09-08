from django.conf.urls import url

from . import views
app_name = 'airtablewebhook'
urlpatterns = [
    url(r'^$', views.hook_receiver_view, name='index'),
]

