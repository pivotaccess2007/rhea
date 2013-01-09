#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

from django.conf.urls.defaults import *
from piston.resource import Resource
from api.handlers import *
import api.views as views


auth = HttpBasicAuthentication(realm="RapidSMS API")
user_handler = Resource(UserHandler, authentication=auth)
patient_handler = Resource(PatientHandler,authentication=auth)
alert_handler = Resource(AlertHandler,authentication=auth)
urlpatterns = patterns('',
    url(r'^api$', views.index),
    url(r'^api/patients$', patient_handler),
    url(r'^api/users(?P<emitter_format>.+)$', user_handler,{ 'emitter_format': 'xml' }),
    url(r'^api/patients/(?P<patient_id>\d+)$', patient_handler),
    url(r'^api/patients/alerts$', alert_handler),
    #url(r'^api/patients/(?P<patient_id>\d+)/alerts(?P<emitter_format>.+)$', alert_handler,{ 'emitter_format': 'xml' }),
    url(r'^ws/rest/v1/alerts$', alert_handler,{ 'emitter_format': 'xml' }),
    url(r'^api/client$', views.alert),
    url(r'^api/client/\+?(?P<nid>\d+)$', views.view_alert),
    
    
)
