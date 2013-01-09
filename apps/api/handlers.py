from apps.ambulances.models import *
from piston.handler import BaseHandler
from django.contrib.auth import authenticate
from django.http import HttpResponse
from apps.ubuzima.models import *
from ubuzima.management.commands.checkreminders import Command
from apps.reporters.models import *
from piston.utils import require_mime,rc
from django.contrib.auth.models import User
from django.core import serializers
from api.utils import *
from django.http import  QueryDict
from xml.dom.minidom import parseString
from api.hl7toxml import RheaNotification
#RAPIDSMS RESTful API 
#Consumed / Exposed services
#A resource can be just a class, but usually you would want to define at least 1 of 4 methods:

#read :is called on GET requests, and should never modify data (idempotent.)

#create :is called on POST, and creates new objects, and should return them (or rc.CREATED.)

#update :is called on PUT, and should update an existing product and return them (or rc.ALL_OK.)

#delete :is called on DELETE, and should delete an existing object. Should not return anything, just rc.DELETED.

class AlertHandler(BaseHandler):
	allowed_methods = ('GET','POST')
	model = TriggeredAlert
	
	def read(self, request, patient_id=None):
		"""
			Returns a single Alert if `patient_id` is given,
			otherwise a subset.
		"""
        	alerts = TriggeredAlert.objects
        
        	if patient_id:
            		return alerts.filter(report__patient=Patient.objects.get(national_id=patient_id))
        	else:
            		return alerts.all()
	
	#@require_mime('xml','json')
	def create(self, request, patient_id=None):
		
		response = None
		try:
			response = RheaNotification().createIncomingNotification(request)
		except: 
			pass
		
		incoming=RheaRequest(request = request,data=request.raw_post_data, response = response, status_reason="%s_%s" % ("",""))
		incoming.save()
			
		return response		

class PatientHandler(BaseHandler):
	allowed_methods = ('GET')
	model = Patient
	fields=('id','national_id','location')
	
	def read(self, request, patient_id=None):
		"""
			Returns a single Patient if `patient_id` is given,
			otherwise a subset.
		"""
        	pats = Patient.objects
        	
		if patient_id:
			return pats.get(national_id=patient_id)
        	else:
            		return pats.all()

class LocationHandler(BaseHandler):
	allowed_methods = ('GET')
	model = Location
	fields=('id','name','code')

class ReportTypeHandler(BaseHandler):
	allowed_methods = ('GET')
	model = ReportType
	fields=('id','name')
class ReportHandler(BaseHandler):
	allowed_methods = ('GET')
	model = Report
	fields=('id','type','patient','reporter','location','village','date','created')

	def read(self, request, patient_id=None):
		
		return True

class ReporterHandler(BaseHandler):
	allowed_methods = ('GET')
	model = Reporter
	fields=('id','alias','first_name','last_name','location','village','language','groups')
class ReporterGroupHandler(BaseHandler):
	allowed_methods = ('GET')
	model = ReporterGroup
	fields=('title','description')



class TriggeredTextHandler(BaseHandler):
	allowed_methods = ('GET')
	model = TriggeredText
	

	

class UserHandler(BaseHandler):
	allowed_methods = ('GET',)
	model = User

	def read(self, request ):
		
		return request.user.groups.get(name=conf["group"])

class GroupHandler(BaseHandler):
	allowed_methods = ('GET',)
	model = Group

class HttpBasicAuthentication(object):
    """
    Basic HTTP authenticater. Synopsis:
    
    Authentication handlers must implement two methods:
     - `is_authenticated`: Will be called when checking for
        authentication. Receives a `request` object, please
        set your `User` object on `request.user`, otherwise
        return False (or something that evaluates to False.)
     - `challenge`: In cases where `is_authenticated` returns
        False, the result of this method will be returned.
        This will usually be a `HttpResponse` object with
        some kind of challenge headers and 401 code on it.
    """
    def __init__(self, auth_func=authenticate, realm='RapidSMS API'):
        self.auth_func = auth_func
        self.realm = realm

    def is_authenticated(self, request):
        auth_string = request.META.get('HTTP_AUTHORIZATION', None)

        if not auth_string:
            return False
            
        try:
            (authmeth, auth) = auth_string.split(" ", 1)

            if not authmeth.lower() == 'basic':
                return False

            auth = auth.strip().decode('base64')
            (username, password) = auth.split(':', 1)
        except (ValueError, binascii.Error):
            return False

        request.user = self.auth_func(username=username, password=password) or AnonymousUser()
        
        if not request.user in (False, None, AnonymousUser()) and request.user.groups.filter(name=conf["group"]).count() > 0:
        	
        	return True
	else:
        	return False
                
        return not request.user in (False, None, AnonymousUser())
        
    def challenge(self):
        resp = HttpResponse("Authorization Required")
        resp['WWW-Authenticate'] = 'Basic realm="%s"' % self.realm
        resp.status_code = 401
        return resp

    def __repr__(self):
        return u'<HTTPBasic: realm=%s>' % self.realm

	

