from django.core.management.base import BaseCommand
from django.conf import settings
import urllib2
import time
import datetime
from optparse import make_option
from api.handlers import *

class Command(BaseCommand):
    help = "Send REG,PRE,RISK and MAt notifications to the Shared Health Record.  This command should be run every 30 minutes via cron"
    
    def handle(self, **options):
        print "Sending Notification..."
	nots=get_new_nots()
	for x in nots:
		if x=="pre":
			for r in nots[x]:
				try:
					notif=create_preg_notification(r)
					req=create_rhea_request("/ws/rest/v1/patient/NID-%s/encounters" % r.patient.national_id, notif.message)
					print "METHOD: %s    DATA: %s"% (req.get_method(), req.data)
					if req:
						res=get_rhea_response(req)
						if res.code==201:
							try:
								last_not=LastNotification.objects.all().order_by("-id")[0]
								last_not.last_preg=r
								last_not.last_not=notif
								last_not.save()
							except:
								last_not=LastNotification(last_pre=r,last_not=notif)
								last_not.save()
						print "Patient: %s, Response Status: %s" % (r.patient, res.msg)
				except :
					continue
		if x=="risk":
			for r in nots[x]:
				try:
					notif=create_risk_notification(r)
					req=create_rhea_request("/ws/rest/v1/patient/NID-%s/encounters" % r.patient.national_id, notif.message)
					print "METHOD: %s    DATA: %s"% (req.get_method(), req.data)
					if req:
						res=get_rhea_response(req)
						if res.code==201:
							try:
								last_not=LastNotification.objects.all().order_by("-id")[0]
								last_not.last_risk=r
								last_not.last_not=notif
								last_not.save()
							except:
								last_not=LastNotification(last_risk=r,last_not=notif)
								last_not.save()
						print "Patient: %s, Response Status: %s" % (r.patient, res.msg)
				except:
					continue

		if x=="bir":
			for r in nots[x]:
				try:
					notif=create_bir_notification(r)
					req=create_rhea_request("/ws/rest/v1/patient/NID-%s/encounters" % r.patient.national_id, notif.message)
					print "METHOD: %s    DATA: %s"% (req.get_method(), req.data)
					if req:
						res=get_rhea_response(req)
						if res.code==201:
							try:
								last_not=LastNotification.objects.all().order_by("-id")[0]
								last_not.last_bir=r
								last_not.last_not=notif
								last_not.save()
							except:
								last_not=LastNotification(last_bir=r,last_not=notif)
								last_not.save()
						print "Patient: %s, Response Status: %s" % (r.patient, res.msg)
				except:
					continue

		if x=="mat":
			for r in nots[x]:
				try:
					notif=create_mat_notification(r)
					req=create_rhea_request("/ws/rest/v1/patient/NID-%s/encounters" % r.patient.national_id, notif.message)
					print "METHOD: %s    DATA: %s"% (req.get_method(), req.data)
					if req:
						res=get_rhea_response(req)
						if res.code==201:
							try:
								last_not=LastNotification.objects.all().order_by("-id")[0]
								last_not.last_mat=r
								last_not.last_not=notif
								last_not.last_field=r.fields.filter(type__category__name="Death").order_by("-id")[0]
								last_not.save()
							except:
								last_not=LastNotification(last_mat=r,last_not=notif,last_field=r.fields.filter(type__category__name="Death").order_by("-id")[0])
								last_not.save()
						print "Patient: %s, Response Status: %s" % (r.patient, res.msg)
				except:
					continue
		if x=="reg":
			for r in nots[x]:
				try:
					#Need to know excatly wich resource is responsible of CHW registration
					notif=create_reg_notification(r)					
					req=create_rhea_request("/ws/rest/v1/patient/NID-%s/encounters" % r.alias, notif.message)
					print "METHOD: %s    DATA: %s"% (req.get_method(), req.data)
					if req:
						res=get_rhea_response(req)
						if res.code==201:
							try:
								last_not=LastNotification.objects.all().order_by("-id")[0]
								last_not.last_reg=r
								last_not.last_not=notif
								last_not.save()
							except:
								last_not=LastNotification(last_reg=r,last_not=notif)
								last_not.save()
						print "Patient: %s, Response Status: %s" % (r.patient, res.msg)
				except:
					continue
	
	print "Sending Notification Complete."

