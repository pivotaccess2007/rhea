# Create your webui views here.
from rapidsms.webui.utils import render_to_response
from ubuzima.models import *
from api.handlers import *
from ubuzima.views import *

def index(req,**flts):
    template_name="api/index.html"
    try:
        p = UserLocation.objects.get(user=req.user)
    except UserLocation.DoesNotExist,e:
        return render_to_response(req,"404.html",{'error':e})
    filters = {'period':default_period(req),
             'location':default_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    reports=matching_reports(req,filters)
    req.session['track']=[
       {'label':'Pregnancy',          'id':'allpreg',
       'number':len(reports.filter(type=ReportType.objects.get(name = 'Pregnancy')))},
       {'label':'Birth',            'id':'bir',
       'number':len(reports.filter(type=ReportType.objects.get(name = 'Birth')))},
        {'label':'ANC',            'id':'anc',
       'number':len(reports.filter(type=ReportType.objects.get(name = 'ANC')))},
       {'label':'Risk', 'id':'risk',
       'number':len(reports.filter(type=ReportType.objects.get(name = 'Risk')))},
       {'label':'Child Health',           'id':'chihe',
       'number':len(reports.filter(type=ReportType.objects.get(name = 'Child Health')))},]
    lox, lxn = 0, location_name(req)
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        lxn=lxn.name+' '+lxn.type.name+', '+lxn.parent.parent.name+' '+lxn.parent.parent.type.name+', '+lxn.parent.parent.parent.name+' '+lxn.parent.parent.parent.type.name
    if req.REQUEST.has_key('csv'):
        heads=['ReportID','Date','Location','Type','Reporter','Patient','Message']
        htp = HttpResponse()
        htp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
        wrt = csv.writer(htp, dialect = 'excel-tab')
        seq=[]
        for r in reports:
            try:
                seq.append([r.id, r.created,r.location,r.type,r.reporter.alias,r.patient.national_id, r.summary()])
            except Reporter.DoesNotExist:
                continue
        wrt.writerows([heads]+seq)
        return htp
    else:
        return render_to_response(req,
            template_name, {
            "reports": paginated(req, reports, prefix="rep"),'usrloc':UserLocation.objects.get(user=req.user),'start_date':date.strftime(filters['period']['start'], '%d.%m.%Y'),
             'end_date':date.strftime(filters['period']['end'], '%d.%m.%Y'),'filters':filters,'locationname':lxn,'postqn':(req.get_full_path().split('?', 2) + [''])[1]
        })

def alert(req):
	values=alert_type(req)
	template_name="api/alerts.html"
	msg=None
		
	return render_to_response(req, template_name, {'values':values['fs'],'typ':values['typ'],'locations':Location.objects.filter(type__id__in=[4,5]),'msg':msg})

def alert_type(req):

    try:
        alert_type = req.REQUEST['type']
	typ=alert_type
        if alert_type.lower()=='risk':
		try:
			val=int(req.REQUEST['value'])
		except KeyError:
			val=FieldType.objects.filter(category__name="Risk").order_by("key")[0].pk
		return {'fs':FieldType.objects.filter(category__name="Risk").extra(select = {'selected':'ubuzima_fieldtype.id = %d' % (val,)}).order_by('key'),'typ':typ}
        if alert_type.lower()=='reminder':
		try:
			val=int(req.REQUEST['value'])
		except KeyError:
			val=ReminderType.objects.filter(id__in = [4,9]).order_by("name")[0].pk
		return {'fs': ReminderType.objects.filter(id__in = [4,9]).extra(select = {'selected':'ubuzima_remindertype.id = %d' % (val,)}).order_by('name'),'typ':typ}          
    except KeyError, IndexError:
        return {'fs':[],'typ':[]}


def view_alert(req, nid):
	try:
		if nid:
			pat=nid
			alert_type = req.REQUEST['type']
			
			loc=Location.objects.get(pk=int(req.REQUEST['loc']))
			d=datetime.datetime.now()
			sent_date_time="%04d%02d%02d%02d%02d%02d"%(d.year,d.month,d.day,d.hour,d.minute,d.second)
			if alert_type.lower()=='risk':
				key=FieldType.objects.get(pk=int(req.REQUEST['al']))
				alert="MSH|^~\&#|SHR|RwandaMOH|RapidSMS|%s|%s||ORU^R01^ORU_R01||D^C|2.5^RWA|||||||||ALERT\rPID|||%s^^^^NID||\rOBR|1|||^Maternal Health Alert|||||||||||||||||||||||||||||||||||||||||||CHW\rOBX|1|CE|^%s^||%s||||||F" %(loc.code,sent_date_time,pat,key.description,key.key)
			if alert_type.lower()=='reminder':
				key=ReminderType.objects.get(id = int(req.REQUEST['al']))
				alert="MSH|^~\&#|SHR|RwandaMOH|RapidSMS|%s|%s||ORU^R01^ORU_R01||D^C|2.5^RWA|||||||||ALERT\rPID|||%s^^^^NID||\rOBR|1|||^Maternal Health Alert|||||||||||||||||||||||||||||||||||||||||||CHW\rOBX|1|CE|^%s^||%s||||||F" %(loc.code,sent_date_time,pat,key.name,req.REQUEST['value'])	
			url = 'http://localhost:8000/api/patients/%s/alerts/'%pat
			
			shr_req=urllib2.Request(url, alert)
			base64string = base64.encodestring('%s:%s' % ("rhea", "rhea"))[:-1]
			shr_req.add_header("Authorization", "Basic %s" % base64string)
			
	except KeyError,e:
		pass
	
	reponse=urllib2.urlopen(shr_req)
	r = HttpResponse(response.read())

	for header in response.info().keys():
		r[header] = response.info()[header]
	print r

    	return r 
	

#.extra(select = {'selected':'ubuzima_fieldtype.id = %d' % (val,)}).order_by('key')
