import socket
import ssl
import httplib
from ubuzima.models import *
from api.models import *
import urllib2
import hl7
from django.conf import settings
import base64
import time
from ambulances.models import *
from ubuzima.management.commands.checkreminders import Command
from ubuzima.smser import *

conf = settings.RAPIDSMS_APPS["api"]

def get_rhea_connection():
	
        try:
		#conn=RHEAHTTPS(conf["host"], conf["port"], conf["key_file"], conf["cert_file"], conf["ca_file"])#In production with SSL
		conn=urllib2.urlopen("http://%s:%s"%(conf["host"],conf["port"]),conf["timeout"])
		if conn.code==200:
			return True
	except:
		pass
	return False
def create_rhea_request(url,data):
	try:
		#if get_rhea_connection():
		url="https://%s:%s%s"%(conf["host"],conf["port"],url)
		request = urllib2.Request(url, data)
		base64string = base64.encodestring('%s:%s' % (conf["user"], conf["pass"]))[:-1]
		request.add_header("Authorization", "Basic %s" % base64string)
		return request
	except:
		pass
	return False
	
def get_rhea_response(request):
	try:
		response = urllib2.urlopen(request)
	except urllib2.HTTPError, e:
		response=e
	except urllib2.URLError, e:
		response=e		

	incoming=RheaRequest(request=request.headers,data=request.data, response=response, status_reason="%s_%s"%(response.code, response.msg))
	incoming.save()
	return response

def create_preg_notification(report):
	if report.type != ReportType.objects.get(name="Pregnancy"):
		return False	
	try:
		sending_fosa=report.location.code
		sent_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		control_id=report.id
		patient_id=report.patient.national_id
		location=report.location.code.replace("F","")
		chw_id=report.reporter.alias
		admit_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		lmp="%04d%02d%02d"%(report.date.year,report.date.month,report.date.day)
		weight=float(report.fields.get(type__key='mother_weight').value)
		edd="%04d%02d%02d"%(report.show_edd().year,report.show_edd().month,report.show_edd().day)
	
		pre_msg = "MSH|^~\&|RapidSMS|%s|SHR|RwandaMOH|%s||ORU^R01^ORU_R01|%s|D^C|2.5^RWA|||||||||PRE\rPID|||%s^^^^NID||name not available\rPV1|1|Community Health|%s||||%s|||||||||||||||||||||||||||||||||||||%s\rOBR|1|||^Maternal Health Reporting\rOBX|1|TS|^Date of Last Menstrual Period^||%s||||||F\rOBX|2|NM|^Mother's Weight^||%s|k|||||F\rOBX|3|TS|^Estimated Date of Delivery^||%s||||||F%s"%(sending_fosa,sent_date_time,control_id,patient_id,location,chw_id,admit_date_time,lmp,weight,edd,build_obx(report.fields.all().exclude(type__key="mother_weight"),3))
	
		notification = Notification(not_type=NotificationType.objects.get(name="Pregnancy"),message=hl7.parse(pre_msg),report=report)
		notification.save()
		
		
	except Exception,e:
		notification = Notification.objects.get(report=report)
		

	return Notification.objects.get(pk=notification.pk)

def create_risk_notification(report):
	if report.type != ReportType.objects.get(name="Risk"):
		return False	
	try:
		sending_fosa=report.location.code
		sent_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		control_id=report.id
		patient_id=report.patient.national_id
		location=report.location.code.replace("F","")
		chw_id=report.reporter.alias
		admit_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		weight=float(report.fields.get(type__key='mother_weight').value)
		
	
		
		risk_msg="MSH|^~\&|RapidSMS|%s|SHR|RwandaMOH|%s||ORU^R01^ORU_R01|%s|D^C|2.5^RWA|||||||||RISK\rPID|||%s^^^^NID||name not available\rPV1|1|Community Health|%s||||%s|||||||||||||||||||||||||||||||||||||%s\rOBR|1|||^Maternal Health Reporting\rOBX|1|NM|^Mother's Weight^||%s|k|||||F%s"%(sending_fosa,sent_date_time,control_id,patient_id,location,chw_id,admit_date_time,weight,build_obx(report.fields.all().exclude(type__key="mother_weight"),1))

	
		notification=Notification(not_type=NotificationType.objects.get(name="Risk"),message=hl7.parse(risk_msg),report=report)
		notification.save()
		
		
	except Exception,e:
		notification = Notification.objects.get(report=report)
		
	return Notification.objects.get(pk=notification.pk)

def create_bir_notification(report):
	if report.type != ReportType.objects.get(name="Birth"):
		return False	
	try:
		sending_fosa=report.location.code
		sent_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		control_id=report.id
		patient_id=report.patient.national_id
		location=report.location.code.replace("F","")
		chw_id=report.reporter.alias
		admit_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		birth_date="%04d%02d%02d"%(report.date.year,report.date.month,report.date.day)
		weight=float(report.fields.get(type__key='child_weight').value)
		
			
		bir_msg="MSH|^~\&|RapidSMS|%s|SHR|RwandaMOH|%s||ORU^R01^ORU_R01|%s|D^C|2.5^RWA|||||||||BIR\rPID|||%s^^^^NID||name not available\rPV1|1|Community Health|%s||||%s|||||||||||||||||||||||||||||||||||||%s\rOBR|1|||^Maternal Health Reporting\rOBX|1|TS|^Birth Date^||%s||||||F\rOBX|2|NM|^Baby Weight^||%s|k|||||F%s"%(sending_fosa,sent_date_time,control_id,patient_id,location,chw_id,admit_date_time,birth_date,weight,build_obx(report.fields.all().exclude(type__key="child_weight"),2))

	
		notification=Notification(not_type=NotificationType.objects.get(name="Birth"),message=hl7.parse(bir_msg),report=report)
		notification.save()
		
		
	except Exception,e:
		notification = Notification.objects.get(report=report)
		
	return Notification.objects.get(pk=notification.pk)

def create_mat_notification(report):
	#if report.type != ReportType.objects.get(name="Death"):
		#return False	
	try:
		sending_fosa=report.location.code
		sent_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		control_id=report.id
		patient_id=report.patient.national_id
		location=report.location.code.replace("F","")
		chw_id=report.reporter.alias
		admit_date_time="%04d%02d%02d%02d%02d%02d"%(report.created.year,report.created.month,report.created.day,report.created.hour,report.created.minute,report.created.second)
		death_date="%04d%02d%02d"%(report.date.year,report.date.month,report.date.day)
				
		mat_msg="MSH|^~\&|RapidSMS|%s|SHR|RwandaMOH|%s||ORU^R01^ORU_R01|%s|D^C|2.5^RWA|||||||||MAT\rPID|||%s^^^^NID||name not available||||||||||||||||||||||||%s\rPV1|1|Community Health|%s||||%s|||||||||||||||||||||||||||||||||||||%s\rOBR|1|||^Maternal Health Reporting%s"%(sending_fosa,sent_date_time,control_id,patient_id,admit_date_time,location,chw_id,admit_date_time,build_obx(report.fields.filter(type__category__name="Death"),0))

		notification=Notification(not_type=NotificationType.objects.get(name="Death"),message=hl7.parse(mat_msg),report=report)
		notification.save()
		
		
	except Exception,e:
		notification = Notification.objects.get(report=report,not_type=NotificationType.objects.get(name="Death"))
		
	return Notification.objects.get(pk=notification.pk)

def create_reg_notification(reporter):
	try:
		g=reporter.groups.get(title="CHW")
		d=datetime.datetime.now()		
		sending_fosa=reporter.location.code
		sent_date_time="%04d%02d%02d%02d%02d%02d"%(d.year,d.month,d.day,d.hour,d.minute,d.second)
		control_id=reporter.id
		reporter_id=reporter.alias
		location=reporter.location.code.replace("F","")
		village=reporter.village
		lang=reporter.language.upper()
						
		reg_msg=reg="MSH|^~\&|RapidSMS|%s|SHR|RwandaMOH|%s||ORU^R01^ORU_R01|%s|D^C|2.5^RWA|||||||||REG\rSTF||%s||Community Health Worker||||^%s\rORG|1||||^^^^^%s\rLAN|1|%s"%(sending_fosa,sent_date_time,control_id,reporter_id,village,location,lang)

		notification=Notification(not_type=NotificationType.objects.get(name="Registration"),message=hl7.parse(reg_msg),report=reporter.report_set.all()[0])
		notification.save()
		
		
	except Exception,e:
		notification = Notification.objects.get(report=reporter.report_set.all()[0])
		
	return Notification.objects.get(pk=notification.pk)


def create_alert(data):
	allalerts,alerts,reminders={},[],[]
	msg=hl7.parse(data)
	
	patient=get_patient(msg.segment('PID')[3][0])
	if patient is None:
		patient=Patient(national_id=(msg.segment('PID')[3][0]),location=Location.objects.get(code=msg.segment('MSH')[5][0]))
		patient.save()
	try:
		reporter=get_reporter(None ,patient)
	except:
		reporter=Reporter.objects.filter(location=Location.objects.get(code=msg.segment('MSH')[5][0]),groups__pk=2)[0]
		
	report=create_report("SHR Alert", patient, reporter)
	report.save()
	fs=[x.key for x in FieldType.objects.filter(category__name="Risk")]
	for m in msg.segments('OBX'):

		description=m[3][1]#Description
		value=m[5][0]#Value
		
		if msg.segment('MSH')[20][0].lower()=="ALERT".lower() and value.lower() in fs:
			f=Field(type=FieldType.objects.get(key=value.lower()))
			f.save()
			report.fields.add(f)
		#if value.lower()=="chw":
			#remi=Reminder( reporter=reporter, report=report, type =ReminderType.objects.get(pk=6) ,date=datetime.datetime.now())
			#remi.save()
			#reminders.append(remi)
		if "anc" in value.lower():
			remi=Reminder( reporter=reporter, report=report, type =ReminderType.objects.get(pk=9) ,date=datetime.datetime.now())
			remi.save()
			reminders.append(remi)
		if value.lower()=="edd":
			remi=Reminder( reporter=reporter, report=report, type =ReminderType.objects.get(pk=4) ,date=datetime.datetime.now())
			remi.save()
			reminders.append(remi)
			
			
			
	for trigger in TriggeredText.get_triggers_for_report(report):
		alert=TriggeredAlert(reporter=report.reporter, report=report, trigger=trigger)
		alert.save()
		alerts.append(alert)	
			
		#create alert here
	allalerts={'alerts':alerts,'reminders':reminders}
	return allalerts

def create_report(report_type_name, patient, reporter):
        """Convenience for creating a new Report object from a reporter, patient and type """
        
        report_type = ReportType.objects.get(name=report_type_name)
        report = Report(patient=patient, reporter=reporter, type=report_type,
                        location=reporter.location, village=reporter.village)
        return report

def get_reporter(alias=None,patient=None):
	"""Takes care of searching our DB for the passed in reporter alias.  Equality is determined
           using the alias only (IE, dob doesn't come into play).  This will look for an existing reporter in that location if no alias."""
           
        # try to look up the patent by id
        try:
            reporter = Reporter.objects.get(alias=alias)
        except Reporter.DoesNotExist:
            # not found?  create the patient instead
            reporter = Report.objects.filter(patient=patient).order_by("-id")[0].reporter
                
        return reporter

def get_patient(national_id):
                   
        # try to look up the patent by id
        try:
            patient = Patient.objects.get(national_id=national_id)
        except Patient.DoesNotExist:
            # not found?  create the patient instead
            patient = None
                
        return patient

def get_new_nots():
	nots={}
	try:	
		nots['pre']=Report.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_preg.pk, type__name="Pregnancy")
	except:
		nots['pre']=Report.objects.filter(type__name="Pregnancy")
	try:
		nots['risk']=Report.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_risk.pk, type__name="Risk")
	except:
		nots['risk']=Report.objects.filter(type__name="Risk")
	try:
		nots['bir']=Report.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_bir.pk, type__name="Birth")
	except:
		nots['bir']=Report.objects.filter(type__name="Birth")
	try:
		nots['mat']=Report.objects.filter( pk__in = [x.report_set.get().pk for x in Field.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_field.pk, type__category__name="Death")])
	except:
		nots['mat']=Report.objects.filter(pk__in = [x.report_set.get().pk for x in Field.objects.filter(type__category__name="Death")])
	try:
		
		nots['reg']=Reporter.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_reg.pk)
	except:
		nots['reg']=Reporter.objects.all()
	try:
		nots['noti']=Notification.objects.filter(pk__gt=LastNotification.objects.all().order_by("-id")[0].last_not.pk)
	except:
		nots['noti']=Notification.objects.all()
	return nots

def build_obx(fields,i):
	obx=""
	#i=0  by building fields dynamically
	for x in fields:
		i=i+1
		if x.value:
			obx=obx+"\rOBX|%s|NM|^%s^||%s||||||F"%(i,x.type.description,x.value)
		else:
			obx=obx+"\rOBX|%s|CE|^%s^||%s||||||F"%(i,x.type.description,x.type.key)
	return obx


def send_sms_via_httptester(connection,message):
	conf = settings.RAPIDSMS_APPS["httptester"]
	url = "http://%s:%s/%s/%s?backend=%s&direction=out" % (
		conf["host"], 
                conf["port"],
                urllib2.quote(connection.identity.strip()), 
                urllib2.quote(message),
                urllib2.quote(connection.backend.slug))
	
	f = urllib2.urlopen(url, timeout=10)
	
	if f.getcode() / 100 != 2:
		print "Error delivering message to URL: %s" % url
		raise RuntimeError("Got bad response from router: %d" % f.getcode())

	# do things at a reasonable pace
	time.sleep(.2)
def send_alerts(alert):
	
	report=alert.report
	message="Umubyeyi ufite irangamuntu numero %s utuye mu mudugudu wa %s afite ikibazo cya %s(%s). Gerageza urebe uko wamufasha uyu mubyeyi."%(alert.report.patient.national_id,alert.report.village,alert.report.fields.all()[0].type.description,alert.report.fields.all()[0].type.key)
	
	send_sms_via_httptester(alert.report.reporter.connection(),message)# in testing only, remove this in production
	
	Command().send_message(report.reporter.connection(),message)#in production
	
	if alert.trigger.destination==TriggeredText.DESTINATION_SUP:
		message="Umubyeyi ufite irangamuntu numero %s utuye mu mudugudu wa %s afite ikibazo cya %s(%s). Gerageza urebe uko wamufasha uyu mubyeyi. "%(alert.report.patient.national_id,alert.report.village,alert.report.fields.all()[0].type.description,alert.report.fields.all()[0].type.key)
		Command().send_message(Reporter.objects.filter(location=alert.report.reporter.location, groups__pk=2)[0].connection(),message)#in production
		send_sms_via_httptester(Reporter.objects.filter(location=alert.report.reporter.location, groups__pk=2)[0].connection(),message)# in testing only, remove this in production

	if alert.trigger.destination == TriggeredText.DESTINATION_AMB:
		curloc=alert.reporter.location
		while curloc:
			ambs = AmbulanceDriver.objects.filter(location = curloc)						
			if len(ambs) < 1:
				curloc = curloc.parent
				continue
			for amb in ambs:
				message="Umubyeyi ufite irangamuntu numero %s utuye mu mudugudu wa %s afite ikibazo cya %s(%s). Gerageza ufatanye n' Umujyanama ukoresha telephoni numero %s urebe uko mwamufasha uyu mubyeyi. "%(alert.report.patient.national_id,alert.report.village,alert.report.fields.all()[0].type.description,alert.report.fields.all()[0].type.key,alert.reporter.connection().identity)
				print amb.phonenumber,PersistantConnection(identity=amb.phonenumber,\
				backend=PersistantBackend.objects.get(title="Kannel"))
				send_sms_via_httptester(PersistantConnection(identity=amb.phonenumber,\
				backend=PersistantBackend.objects.get(title="Kannel")),message)# in testing only, remove this in production
				Command().send_message(PersistantConnection(identity=amb.phonenumber,\
				backend=PersistantBackend.objects.get(title="Kannel")),message)#in production
				
			break
	

def receive_reminders(reminder):
	message = "Umubyeyi ufite irangamuntu numero %s agomba kujya ku bitaro kubonana na muganga. Gerageza umwibutse kandi urebe uko wamufasha. Murakoze!" % reminder['patient']['nid']
	#print message
	return message

def send_reminder_message(reminder):

	try:
		message = receive_reminders(reminder)
		identity  = None
		try:	identity = Reporter.objects.get(alias = reminder['reporter']['nid']).connection().identity
			
		except:
			try:	identity = Reporter.objects.filter(location__code = 'F%s' % reminder['facility']['code'], groups__in = \
					ReporterGroup.objects.filter( title = 'Supervisor'))[0].connection().identity
			except:	identity = '0788660270'
		
		#print "Didier : %s" % identity
		try:
			Smser().send_message_via_kannel(identity, message)
		except:
			Smser().send_message_via_gsm(identity, message)
	except:
		return False
	return True



def send_reminders(rem):
	report=rem.report
	
	reminder_type = rem.type
	if reminder_type == ReminderType.objects.get(pk=6):
		# look up the supervisors for the reporter's location
		sups = Reporter.objects.filter(location=report.reporter.location, groups__pk=2)
		for sup in sups:
			# determine the right messages to send for this reporter
			message = reminder_type.message_kw
			if sup.language == 'en':
				message = reminder_type.message_en
			elif sup.language == 'fr':
				message = reminder_type.message_fr

			message = message % report.patient.national_id
			Command().send_message(sup.connection(),message)#in production
			send_sms_via_httptester(sup.connection(), message)# in testing only, remove this in production

	else:
		message = reminder_type.message_kw
		if report.reporter.language == 'en':
			message = reminder_type.message_en
		elif report.reporter.language == 'fr':
			message = reminder_type.message_fr

		message = message % report.patient.national_id
		Command().send_message(report.reporter.connection(),message)#in production
		send_sms_via_httptester(report.reporter.connection(), message)# in testing only, remove this in production
	

class RHEAHTTPS(httplib.HTTPSConnection):
    """ Class to make a HTTPS connection, with support for full client-based SSL Authentication"""

    def __init__(self, host, port, key_file, cert_file, ca_file, timeout=None):
        httplib.HTTPSConnection.__init__(self, host, key_file=key_file, cert_file=cert_file)
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.timeout = timeout

    def connect(self):
        """ Connect to a host on a given (SSL) port.
            If ca_file is pointing somewhere, use it to check Server Certificate.

            Redefined/copied and extended from httplib.py:1105 (Python 2.6.x).
            This is needed to pass cert_reqs=ssl.CERT_REQUIRED as parameter to ssl.wrap_socket(),
            which forces SSL to check server certificate against our client certificate.
        """
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        # If there's no CA File, don't force Server Certificate Check
        if self.ca_file:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ca_certs=self.ca_file, cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, cert_reqs=ssl.CERT_NONE)


