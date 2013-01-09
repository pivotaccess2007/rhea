from django.core import management
from django.db import connection
from ubuzima.models import *
from locations.models import *
from reporters.models import * 


def loc_short_deletion():
	table='ubuzima_locationshorthand'
	try:
		cursor = connection.cursor()
		cursor.execute("drop table %s" % table)
		cursor.close()
	except Exception,e:
		raise e
		#pass
	return True
	
def hc_loc_short_creation():
	management.call_command('syncdb')
	hc=Location.objects.filter(type__in=[LocationType.objects.get(name='Health Centre'),LocationType.objects.get(name='Hospital')])
	hc=hc.exclude(id__in = [int(x.original.id) for x in LocationShorthand.objects.all()])
	anc,dst,prv,loc=[],None,None,None
	for hece in hc:
		anc,dst,prv,loc=[],None,None,None
		anc=Location.ancestors(hece)
		for an in anc:
			if an.type.name=='District': dst=an
			elif an.type.name=='Province': prv=an
		if prv is None or dst is None: return False
		loc=hece
		ls=LocationShorthand(original=loc, district=dst, province=prv)
		ls.save()
	return True

#deletion of all fields within  report
def rep_fields_del(rep):
	for f in rep.fields.all():
		f.delete()
	return "Deletion of fields from Report:%s"%rep
#deletion of all reminders within  report
def rep_reminders_del(rep):
	for rm in rep.reminders.all():
		rm.delete()
	return "Deletion of reminders according to Report:%s"%rep

#deletion of a report from the reporter
def report_del(rep):
	rep_fields_del(rep)
	rep_reminders_del(rep)
	rep.delete()
	return True

#deletion of reminders of a reporter
def reporter_rem_del(reporter):
	for rm in reporter.reminder_set.all():
		rm.delete()
	return "Deletion of reminders according to Reporter:%s"%reporter

#deletion of Refusal Report of a Reporter
def reporter_ref_del(reporter):
	for rep in reporter.jilted_reporter.all():
		rep.delete()
	return "Deletion of Refusals reports from Reporter:%s"%reporter
#deletion of errors of a reporter
def reporter_err_del(reporter):
	for rep in reporter.erring_reporter.all():
		rep.delete()
	return "Deletion of Errors made by Reporter:%s"%reporter

#deletion of groups of a reporter
def reporter_grps_del(reporter):
	crs = connection.cursor()
	crs.execute('DELETE from reporters_reporter_groups where reporter_id=%s'%reporter.pk)
	crs.close()
	return "Deletion of groups of Reporter:%s"%reporter

#deletion of a connection of a reporter
def reporter_conn_del(phone):
	conn=PersistantConnection.objects.get(identity=phone)
	conn.delete()
	return "Deletion of connection open by Reporter:%s with this phone number:%s"%(conn.reporter.alias,conn.identity)

#deletion of all connections the reporter has opened so far
def reporter_conns_del(reporter):
	for conn in reporter.connections.all():
		conn.delete()
	return "Deletion of connections open by Reporter:%s"%reporter

#Deletion of a reporter

def reporter_del(reporter):
	reporter_rem_del(reporter)
	reporter_ref_del(reporter)
	reporter_err_del(reporter)
		
	for rep in reporter.report_set.all():
		report_del(rep)

	reporter_conns_del(reporter)
	reporter_grps_del(reporter)
	reporter.delete()
	return True

#This function helps generating ANC stats,by fetching all pregs and ancs from the database from record 1...n.

#retrieve recent pregnancy from the patient records
def get_recent_preg(report):
	try:
		reps=Report.objects.filter(patient=report.patient,type=ReportType.objects.get(name='Pregnancy'))
		return reps.get(created=max([x.created for x in reps]))
	except Exception:	pass
	return report
	
#build anc field to populate ANC stats for memoization
def is_anc1_report(r):
	if r.type==ReportType.objects.get(name='Pregnancy'):	return True
	return False
def is_anc2_report(r):
	try:
		if r.fields.get(type=FieldType.objects.get(key='anc2')):	return True
	except Exception:	pass
	return False
def is_anc3_report(r):
	try:
		if r.fields.get(type=FieldType.objects.get(key='anc3')):	return True
	except Exception:	pass
	return False
def is_anc4_report(r):
	try:
		if r.fields.get(type=FieldType.objects.get(key='anc4')):	return True
	except Exception:	pass
	return False
def is_ancdp_report(r):
	try:
		if r.fields.get(type=FieldType.objects.get(key='dp')):	return True
	except Exception:	pass
	return False
def is_standard_anc1(r):
	try:
		if r.type==ReportType.objects.get(name='Pregnancy') and r.date and (r.created.date() - r.date) < datetime.timedelta(140):	return True
		else:	return False
	except exception: pass
	return False
def has_attend_all_anc(r):
	try:	
		if len(Report.objects.filter(created__gte=get_recent_preg(r).created, patient=r.patient,type__name='ANC')) >= 3:	return True
		else:	return False
	except Exception: pass
	return False
def anc_stats_gen():
#table anc_stats was created only_for this purpose
	table='ubuzima_ancstats'
	try:
		cursor = connection.cursor()
		cursor.execute("drop table %s" % table)
		cursor.close()
		management.call_command('syncdb')
		reports=Report.objects.filter(type__in=[ReportType.objects.get(name='Pregnancy'),ReportType.objects.get(name='ANC')])
		for r in reports:
			stat=AncStats(report=r, is_anc1=is_anc1_report(r), is_stard =is_standard_anc1(r),is_anc2=is_anc2_report(r),is_anc3=is_anc3_report(r),is_anc4=is_anc4_report(r),is_dp=is_ancdp_report(r), recent_preg=get_recent_preg(r), has_all=has_attend_all_anc(r), original =r.location, district = LocationShorthand.objects.get(original=r.location).district ,province = LocationShorthand.objects.get(original=r.location).province, created = r.created)
			stat.save()
			l=LastRecord.objects.all().order_by("-id")[0]
			l.anc=r
			l.save()
	except Exception,e:
		raise e
		#pass
	return True

def anc_stats_up():

	try:
		reports=Report.objects.filter(type__in=[ReportType.objects.get(name='Pregnancy'),ReportType.objects.get(name='ANC')],pk__gt=get_last_record().anc.pk)
		for r in reports:
			stat,created=AncStats.objects.get_or_create(report=r, is_anc1=is_anc1_report(r), is_stard =is_standard_anc1(r),is_anc2=is_anc2_report(r),is_anc3=is_anc3_report(r),is_anc4=is_anc4_report(r),is_dp=is_ancdp_report(r), recent_preg=get_recent_preg(r), has_all=has_attend_all_anc(r), original =r.location, district = LocationShorthand.objects.get(original=r.location).district ,province = LocationShorthand.objects.get(original=r.location).province, created = r.created)
			stat.save()
			l=LastRecord.objects.all().order_by("-id")[0]
			l.anc=r
			l.save()
	except Exception,e:
		raise e
		#pass
	return True





#ndaje hano nkemure 504 error

#get all fields types
def get_keys():
	keys={}
	for k in FieldType.objects.all():
		keys[k.key]={'description':k.description,'id':k.id,'category':k.category,'has_value':k.has_value}
	return keys

#get all reports fields
def get_report_fields():
	rpfs={}
	cursor = connection.cursor()
	cursor.execute('select * from ubuzima_report_fields')
	for r in cursor.fetchall():
		rpfs[r[2]]={'id':r[0],'report':r[1],'field':r[2]}
	cursor.close()
	return rpfs #the keys are field ids, which means we have the report and the field of each field.

#get all new reports fields, those not in global statistics!
def get_new_report_fields():
	rpfs={}
	cursor = connection.cursor()
	cursor.execute('select * from ubuzima_report_fields where id > %s' % get_last_record().report_field)
	for r in cursor.fetchall():
		rpfs[r[2]]={'id':r[0],'report':r[1],'field':r[2]}
	cursor.close()
	return rpfs
	
#generate the table of last global statistics of ubuzima App

def global_stats_gen():
	table='ubuzima_globalstatistic'
	try:
		cursor = connection.cursor()
		cursor.execute("drop table %s" % table)
		management.call_command('syncdb')
		cursor = connection.cursor()
		
		cursor.execute('select * from ubuzima_report_fields')

		for r in cursor.fetchall():

			rpt=Report.objects.get(pk=r[1])
			f=Field.objects.get(pk=r[2])
			stat=GlobalStatistic( field = f, report = rpt, report_type = rpt.type , key = f.type.key ,unknown_loc=rpt.is_unknown_loc(), original =rpt.location, district = LocationShorthand.objects.get(original=rpt.location).district ,province = LocationShorthand.objects.get(original=rpt.location).province, created = rpt.created)
			stat.save()
			#print stat
			l=LastRecord.objects.all().order_by("-id")[0]
			l.report=rpt
			l.report_field=r[0]
			l.field=f
			l.save()
		cursor.close()
	except Exception,e:
		raise e
		#pass
	return True

#check for last records of our database this helps to populate these statistics tables every 5 minutes.
def get_last_report_field():
	rpfs={}
	cursor = connection.cursor()
	cursor.execute('SELECT * FROM `ubuzima_report_fields` WHERE `id` = ( SELECT max( id ) FROM ubuzima_report_fields ) ')
	for r in cursor.fetchall():
		rpfs[r[2]]={'id':r[0],'report':r[1],'field':r[2]}
	cursor.close()
	return rpfs

def get_last_record():
	try:
		last_record=LastRecord.objects.all().order_by("-id")[0]
		
	except Exception,e:
		last_record,created=LastRecord.objects.get_or_create(report=Report.objects.all()[0],field=Report.objects.all()[0].fields.all()[0],report_field=Report.objects.all()[0].fields.all()[0].id, preg=Report.objects.filter(type__name="Pregnancy")[0], anc=Report.objects.filter(type__name="ANC")[0], birth=Report.objects.filter(type__name="Birth").order_by("-id")[0], chihe=Report.objects.filter(type__name="Child Health")[0], risk=Report.objects.filter(type__name="Risk")[0])
		
	last_record.save()
		
	return last_record		

#update the global statistics

def update_global_stats():
	
	try:
		cursor = connection.cursor()
		cursor.execute('select * from ubuzima_report_fields where id > %s' % get_last_record().report_field)
		for r in cursor.fetchall():
			rpt=Report.objects.get(pk=r[1])
			f=Field.objects.get(pk=r[2])
			stat,created = GlobalStatistic.objects.get_or_create( field = f, report = rpt, report_type = rpt.type , key = f.type.key ,unknown_loc=rpt.is_unknown_loc(), original =rpt.location, district = LocationShorthand.objects.get(original=rpt.location).district ,province = LocationShorthand.objects.get(original=rpt.location).province, created = rpt.created)
			stat.save()
			l=LastRecord.objects.all().order_by("-id")[0]
			l.report=rpt
			l.report_field=r[0]
			l.field=f
			l.save()
		cursor.close()
	except Exception,e:
		
		raise e
		#pass
	return True

def preg_stats_gen():
	
	table='ubuzima_pregstat'
	try:
		cursor = connection.cursor()
		cursor.execute("drop table if exists %s" % table)
		cursor.close()
		management.call_command('syncdb')
		pregs=Report.objects.filter(type__name="Pregnancy")
		for r in pregs:
			if not r.date:
				r.date=datetime.date(2010,4,1)
				r.save()
			stat=PregStat(report = r, is_high_risk= r.is_high_risky_preg(), is_risk=r.is_risky(), has_toilet=r.has_toilet(), has_hand_wash=r.has_hw(),  edd=r.show_edd(), recent_preg=Report.objects.filter(patient=r.patient,type__name="Pregnancy",date=max([x.date for x in Report.objects.filter(patient=r.patient, type__name='Pregnancy')])).order_by("-created")[0] , original =r.location, district = LocationShorthand.objects.get(original=r.location).district ,province = LocationShorthand.objects.get(original=r.location).province, created = r.created)
			stat.save()
			l=LastRecord.objects.all().order_by("-id")[0]
			l.preg=r
			l.save()
	except Exception, e:
		raise e
	return True
def preg_stats_up():
	try:
		pregs=Report.objects.filter(type__name="Pregnancy",pk__gt=get_last_record().preg.pk)
		
		for r in pregs:
			if not r.date:
				r.date=datetime.date(2010,4,1)
				r.save()
			stat,created=PregStat.objects.get_or_create(report = r, is_high_risk= r.is_high_risky_preg(), is_risk=r.is_risky(), has_toilet=r.has_toilet(), has_hand_wash=r.has_hw(),  edd=r.show_edd(), recent_preg=Report.objects.filter(patient=r.patient,type__name="Pregnancy",date=max([x.date for x in Report.objects.filter(patient=r.patient, type__name='Pregnancy')])).order_by("-created")[0] , original =r.location, district = LocationShorthand.objects.get(original=r.location).district ,province = LocationShorthand.objects.get(original=r.location).province, created = r.created)
			
			stat.save()
			l=LastRecord.objects.all().order_by("-id")[0]
			l.preg=r
			l.save()
	except Exception, e:
		raise e
	return True

def models_up():
	try:
		for r in Reporter.objects.filter(district__id=0,province__id=0):
			if r.location==None: continue
			r.district=LocationShorthand.objects.get(original=r.location).district
			r.province=LocationShorthand.objects.get(original=r.location).province
			r.save()
			
		for p in Patient.objects.filter(district__id=0,province__id=0):
			if p.location==None: continue
			p.district=LocationShorthand.objects.get(original=p.location).district
			p.province=LocationShorthand.objects.get(original=p.location).province
			p.created=datetime.datetime.now()
			p.save()
			
		for rt in Report.objects.filter(district__id=0,province__id=0):
			if rt.location==None: continue
			rt.district=LocationShorthand.objects.get(original=rt.location).district
			rt.province=LocationShorthand.objects.get(original=rt.location).province
			rt.save()
			
	except Exception, e:
		raise e
	return True

def generate_ubuzima_stats():
	
	try:
		management.call_command('syncdb')
		get_last_record()
		p,a,g=preg_stats_gen(),anc_stats_gen(),global_stats_gen()
		if p and a and g:
			loc_short_deletion()
			hc_loc_short_creation()
	except Exception, e:
		pass

	return True

def syncdb_ubuzima_db():
	
	try:
		get_last_record()
		
		p,a,g=preg_stats_up(),anc_stats_up(),update_global_stats()
		
		if p and a and g:
			print "Ok stats"
			
	except Exception, e:
		loc_short_deletion()
		hc_loc_short_creation()
		pass
	return True

def stats_tables_exists():
	tables=['ubuzima_ancstats','ubuzima_globalstatistic','ubuzima_pregstat','ubuzima_lastrecord']
	cursor = connection.cursor()
	cursor.execute("SHOW TABLES")
	ans=[]
	for r in cursor.fetchall():
		ans.append(r[0])
	for t in tables:
		if t not in ans and 'ubuzima_lastrecord' not in ans:
			return False
			break
	return True
	
#end of 504 kemuka
	


	



		
	 
