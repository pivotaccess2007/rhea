#!/usr/bin/env python
# vim: ai ts=4 sts=4 et sw=4

import csv
from datetime import date
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseServerError
from django.template import RequestContext
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.db import transaction, connection

from rapidsms.webui.utils import *
from reporters.models import *
from reporters.utils import *
from sys import getdefaultencoding
from ubuzima.models import *


@permission_required('reports.can_view')
#@require_GET
@require_http_methods(["GET"])
def index(req):
    return render_to_response(req,
        "ubuzima/index.html", {
        "reports": paginated(req, Report.objects.all().order_by("-created"), prefix="rep")
    })

@require_http_methods(["GET"])
def by_patient(req, pk):
    patient = get_object_or_404(Patient, pk=pk)
    reports = Report.objects.filter(patient=patient).order_by("-created")
    
    # look up any reminders sent to this patient
    reminders = []
    for report in reports:
        for reminder in report.reminders.all():
            reminders.append(reminder)

    return render_to_response(req,
                              "ubuzima/patient.html", { "patient":    patient,
                                                        "reports":    paginated(req, reports, prefix="rep"),
                                                        "reminders":  reminders })
    
@require_http_methods(["GET"])
def by_type(req, pk):
    report_type = get_object_or_404(ReportType, pk=pk)
    reports = Report.objects.filter(type=report_type).order_by("-created")
    
    return render_to_response(req,
                              "ubuzima/type.html", { "type":    report_type,
                                                     "reports":    paginated(req, reports, prefix="rep") })
    

@require_http_methods(["GET"])
def view_report(req, pk):
    report = get_object_or_404(Report, pk=pk)
    
    return render_to_response(req,
                              "ubuzima/report.html", { "report":    report })
    
    
@require_http_methods(["GET"])
def by_reporter(req, pk):
    reporter = Reporter.objects.get(pk=pk)
    reports = Report.objects.filter(reporter=reporter).order_by("-created")
    
    return render_to_response(req,
                              "ubuzima/reporter.html", { "reports":    paginated(req, reports, prefix="rep"),
                                                         "reporter":   reporter })
@require_http_methods(["GET"])
def by_location(req, pk):
    location = get_object_or_404(Location, pk=pk)
    reports = Report.objects.filter(location=location).order_by("-created")
    
    return render_to_response(req,
                              "ubuzima/location.html", { "location":   location,
                                                         "reports":   paginated(req, reports, prefix="rep") })
@require_http_methods(["GET"])
def triggers(req):
    triggers = TriggeredText.objects.all()
    
    return render_to_response(req,
                              'ubuzima/triggers.html', { 'triggers': paginated(req, triggers, prefix='trg') } )
    
 
@require_http_methods(["GET"])
def trigger(req, pk):
    trigger = TriggeredText.objects.get(pk=pk)
    
    return render_to_response(req,
                              'ubuzima/trigger.html', { 'trigger': trigger })
    
def apply_report_filters(req, flt, rez):
    rez['date__gte'] = flt['period']['start']
    rez['date__lte'] = flt['period']['end']
    if req.REQUEST.has_key('location'):
        if req.REQUEST['location'] != '0':
            rez['location']  = int(req.REQUEST['location'])
    return rez

def get_stats_track(req, filters):
    rpts  = {'groups__title': 'CHW'}
    if req.REQUEST.has_key('location'):
        rpts['location'] = req.REQUEST['location']
    track = {'births':'Birth', 'pregnancy':'Pregnancy',
            'childhealth':'Child Health', 'risks': 'Risk'}
    cursr = connection.cursor()
    for k in track.keys():
        cursr.execute("""SELECT COUNT(*) FROM ubuzima_report WHERE (SELECT name
        FROM ubuzima_reporttype WHERE id = type_id) = %s""", [track[k]])
        track[k] = cursr.fetchone()[0]
    cursr.execute("""SELECT COUNT(*) FROM reporters_reporter_groups WHERE
            reportergroup_id = (SELECT id FROM reporters_reportergroup WHERE
            title = 'CHW')""")
    track['chws'] = cursr.fetchone()[0]
    return track

@permission_required('reports.can_view')
def view_stats_csv(req, **flts):
    filters = {'period':default_period(req)}
    track = get_stats_track(req, filters)
    rsp   = HttpResponse()
    rsp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
    wrt = csv.writer(rsp, dialect = 'excel-tab')
    wrt.writerows([['Births', 'Pregnancy',
        'Child Health', 'Maternal Risks', 'Community Health Workers']] +
        [[track[x] for x in ['births', 'pregnancy', 'childhealth',
            'risks', 'chws']]])
    return rsp

def cut_date(str):
    stt = [int(x) for x in str.split('/')]
    stt.reverse()
    return date(* stt)

def default_period(req, first = True):
    if req.REQUEST.has_key('start_date') and req.REQUEST.has_key('end_date'):
        return {'start':cut_date(req.REQUEST['start_date']),
                  'end':cut_date(req.REQUEST['end_date'])}
    return {'start':date(2010, 1, 1), 'end':date.today()}

def default_location(req):
    ans = []
    sel = int(req.REQUEST['location']) if req.REQUEST.has_key('location') else 1
    crs = connection.cursor()
    crs.execute("""SELECT DISTINCT location_id, (SELECT name FROM
            locations_location WHERE id = location_id) AS lenom FROM
            ubuzima_report ORDER BY lenom ASC""")
    for loc in crs.fetchall():
        hsh = {'id':loc[0], 'name':loc[1]}
        if int(loc[0]) == sel: hsh['selected'] = True
        ans.append(hsh)
    return ans

def default_district(req):
    ans = []
    sel = int(req.REQUEST['district']) if req.REQUEST.has_key('district') else 1
    if req.REQUEST.has_key('province'):
        par = str(int(req.REQUEST['province']))
    else:
        par = """(SELECT id FROM locations_location B WHERE B.parent_id IS NULL
        ORDER BY name ASC LIMIT 1)"""
    crs = connection.cursor()
    qry = """SELECT DISTINCT id, name FROM locations_location A WHERE
    type_id = (SELECT id FROM locations_locationtype WHERE name = 'District')
    AND parent_id = %s ORDER BY name ASC""" % (par,)
    crs.execute(qry)
    for loc in crs.fetchall():
        hsh = {'id':loc[0], 'name':loc[1]}
        if int(loc[0]) == sel: hsh['selected'] = True
        ans.append(hsh)
    return ans

def default_province(req):
    ans = []
    sel = int(req.REQUEST['province']) if req.REQUEST.has_key('province') else 1
    crs = connection.cursor()
    crs.execute("""SELECT DISTINCT id, name FROM locations_location WHERE
    type_id = (SELECT id FROM locations_locationtype WHERE name = 'Province')
    ORDER BY name ASC""")
    for loc in crs.fetchall():
        hsh = {'id':loc[0], 'name':loc[1]}
        if int(loc[0]) == sel: hsh['selected'] = True
        ans.append(hsh)
    return ans

def pick_hindics_query(req, filters, crs, hindic = None):
    jn      = '%s'
    gt      = ' '
    if req.REQUEST.has_key('location'):
        jn = ' location_id = %d AND '
        gt = int(req.REQUEST['location'])
    qry = (jn % (gt,)).join(["""SELECT DISTINCT type_id FROM ubuzima_report WHERE""",
        """date >= CAST(%s AS DATE) AND date <= CAST(%s AS DATE)"""])
    dfmt = '%Y-%m-%d'
    crs.execute(qry, [date.strftime(filters['period']['start'], dfmt),
                      date.strftime(filters['period']['end'], dfmt)])
    stf     = [str(tid[0]) for tid in crs.fetchall()]
    tids    = ''
    if stf:
        tids = ' AND ubuzima_fieldtype.id IN (%s)' % (', '.join(stf),)
    if hindic:
        tnt = """SELECT id FROM ubuzima_field WHERE type_id = %d%s""" % (hindic, tids)
    else:
        return """SELECT id, description, (SELECT COUNT(*) FROM ubuzima_field WHERE type_id = ubuzima_fieldtype.id%s) AS lecompte FROM ubuzima_fieldtype WHERE (SELECT COUNT(*) FROM ubuzima_field WHERE type_id = ubuzima_fieldtype.id%s) AND NOT has_value ORDER BY lecompte DESC""" % (tids, tids)


@permission_required('reports.can_view')
def view_stats(req, **flts):
    filters = {'period':default_period(req),
             'location':default_location(req),
             'province':default_province(req),
             'district':default_district(req)}
    track   = get_stats_track(req, filters)
    crs     = connection.cursor()
    crs.execute(pick_hindics_query(req, filters, crs))
    hindics = [{'proper_name':x[1], 'instances_count':x[2], 'id':x[0]} for x in crs.fetchall()]
    statflt = apply_report_filters(req, filters, {})
    curpg   = int(req.REQUEST['reqpage']) if req.REQUEST.has_key('reqpage') else 1
    reports = paginated(req, Report.objects.filter(** statflt).order_by('-created'), prefix = 'rep')
    stt = filters['period']['start']
    fin = filters['period']['end']
    lox, lxn, crd = 0, None, {}
    if req.REQUEST.has_key('location') and req.REQUEST['location'] != '0':
        lox = int(req.REQUEST['location'])
        lxn = Location.objects.get(id = lox)
        crd = lxn.parent
        if not crd.longitude: crd = crd.parent
        if not crd.longitude: crd = crd.parent
        if not crd.longitude: crd = crd.parent
        if not crd.longitude: crd = crd.parent
    return render_to_response(req, 'ubuzima/stats.html',
           {'track':track, 'filters':filters,
               'hindics':paginated(req, hindics, prefix = 'hind'),
               'reports':reports,
               'start_date':date.strftime(filters['period']['start'], '%d/%m/%Y'),
               'end_date':date.strftime(filters['period']['end'], '%d/%m/%Y'),
               'coords':crd, 'location': lox, 'locationname':lxn})

@permission_required('reports.can_view')
def view_indicator(req, indic = None, format = 'html'):
    filters = {'period':default_period(req),
             'location':default_location(req)}
    dem     = apply_report_filters(req, filters, {})
    pts     = Report.objects.filter(** dem).order_by('-created')
    heads   = ['Reporter', 'Location', 'Patient', 'Type', 'Date']
    if format == 'csv':
        rsp = HttpResponse()
        rsp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
        wrt = csv.writer(rsp, dialect = 'excel-tab')
        wrt.writerows([heads] +
        [[x.reporter.connection().identity, x.location, x.patient, x.type, x.created] for x in pts])
        return rsp
    return render_to_response(req, ('ubuzima/indicator.html'),
            {'headers': heads, 'patients':paginated(req, pts, prefix = 'ind')})

def view_stats_reports_csv(req):
    filters = {'period':default_period(req),
             'location':default_location(req)}
    statflt = apply_report_filters(req, filters, {})
    reports = Report.objects.filter(** statflt).order_by('-created')
    rsp     = HttpResponse()
    rsp['Content-Type'] = 'text/csv; encoding=%s' % (getdefaultencoding(),)
    wrt = csv.writer(rsp, dialect = 'excel-tab')
    wrt.writerows([[r.created, r.reporter.connection().identity, r.patient, r.location.name, str(r)] for r in reports])
    return rsp
