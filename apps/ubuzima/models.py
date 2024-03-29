from django.db import models
from django.contrib.auth.models import *
from apps.logger.models import IncomingMessage
from apps.reporters.models import Reporter
from apps.locations.models import Location
from django.utils.translation import ugettext as _
import datetime


def fosa_to_code(fosa_id):
    """Given a fosa id, returns a location code"""
    return "F" + fosa_id

def code_to_fosa(code):
    """Given a location code, returns the fosa id"""
    return code[1:]


class FieldCategory(models.Model):
    name = models.CharField(max_length=30, unique=True)
    
    def __unicode__(self):
        return self.name
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )
 

class ReportType(models.Model):
    name = models.CharField(max_length=30, unique=True)
    
    def __unicode__(self):
        return self.name 
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )  

class FieldType(models.Model):
    key = models.CharField(max_length=32, unique=True)
    description = models.TextField(blank=True)
    category = models.ForeignKey(FieldCategory)
    has_value = models.BooleanField(default=False)

    def __unicode__(self):
        return self.key
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )
    
class Patient(models.Model):
    location = models.ForeignKey(Location)
    national_id = models.CharField(max_length=20, unique=True)
    
    
    def __unicode__(self):
        return "%s" % self.national_id
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )
    
    
class Field(models.Model):
    type = models.ForeignKey(FieldType, db_index=True)
    value = models.DecimalField(max_digits=10, decimal_places=5, null=True)
    
    def __unicode__(self):
        if self.value:
            return "%s=%.2f" % (_(self.type.description), self.value)
        else:
            return "%s" % _(self.type.description)
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )
    
class Report(models.Model):
    # Constants for our reminders.  Each reminder will be triggered this many days 
    # before the mother's EDD
    DAYS_ANC2 = 150
    DAYS_ANC3 = 60
    DAYS_ANC4 = 14
    DAYS_SUP_EDD = 14
    DAYS_EDD = 7
    DAYS_ON_THE_DOT = 0
    DAYS_WEEK_LATER = -7

    reporter = models.ForeignKey(Reporter)
    location = models.ForeignKey(Location, db_index=True)
    village = models.CharField(max_length=255, null=True)

    fields = models.ManyToManyField(Field, db_index=True)
    
    patient = models.ForeignKey(Patient)
    type = models.ForeignKey(ReportType)
    
    # meaning of this depends on report type.. arr, should really do this as a field, perhaps as a munged int?
    date_string = models.CharField(max_length=10, null=True)

    # our real date if we have one complete with a date and time
    date = models.DateField(null=True)
    
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )
    def is_unknown_loc(self):
	if self.is_home() or self.is_route() or self.is_hosp():
            return False
        else:
            return True
    
    def __unicode__(self):
        return "Report id: %d type: %s patient: %s date: %s" % (self.pk, self.type.name, self.patient.national_id, self.date_string)
    
    def summary(self):
        summary = ""
        if self.date_string:
            summary += "Date=" + self.date_string

        if self.fields.all():
            if self.date_string: summary += ", "
            summary += ", ".join(map(lambda f: unicode(f), self.fields.all()))

        return summary
    def has_dups(self):
    	if len(Report.objects.filter(type=self.type,patient=self.patient,date=self.date)) > 0:  return True
    	return False
    def rep_fields(self):
    	flds=[]
    	rep_flds=self.fields.all()
	for fld in rep_flds:
    		flds.append(fld)
    	return flds

    def rep_fields_types(self):
    	flds=self.rep_fields()
	types=[]
    	for fld in flds:
		types.append(fld.type)
	return types
    		

    def rep_has_field_type(self, fldt):
    	with_fldt=False
    	if fldt in self.rep_fields_types():
    		with_fldt=True
    	return with_fldt

    def was_vaccinated(self):
    	yes=False
    	vacc=FieldCategory.objects.get(name='Vaccination')
    	vacs=FieldType.objects.filter(category=vacc)
    	for vac in vacs:
    		if self.rep_has_field_type(vac):
    			yes=True
    			break
    	return yes

    def get_vaccine(self):
    	for x in self.fields.all():
    		for vtp in FieldType.objects.filter(category=FieldCategory.objects.get(name='Vaccination')):
    			if x.type==vtp:
    				return x.type 

    def was_vaccinated_with(self,vac):
    	if self.get_vaccine() == vac:
    		return True
    	return False

    
    def is_home(self):
    	yes=False
    	ftp=FieldType.objects.get(key='ho')
    	if self.rep_has_field_type(ftp):
    		yes=True
    	return yes

    def is_hosp(self):
    	yes=False
    	ftp1=FieldType.objects.get(key='hp')
    	ftp2=FieldType.objects.get(key='cl')
    	if self.rep_has_field_type(ftp1) or self.rep_has_field_type(ftp2):
    		yes=True
    	return yes

    def is_route(self):
    	yes=False
    	ftp=FieldType.objects.get(key='or')
    	if self.rep_has_field_type(ftp):
    		yes=True
    	return yes

    def is_maternal_death(self):
    	if self.rep_has_field_type(FieldType.objects.get(key='md')):
    		return True
    	return False

    def is_child_death(self):
    	if self.rep_has_field_type(FieldType.objects.get(key='cd')):
    		return True
    	return False
    def is_newborn_death(self):
    	if self.rep_has_field_type(FieldType.objects.get(key='nd')):
    		return True
    	return False

    def has_no_toilet(self):
    	ftp=FieldType.objects.get(key='nt')
    	if self.rep_has_field_type(ftp):
    		return True
    	return False
    def has_toilet(self):
    	ftp=FieldType.objects.get(key='to')
    	if self.rep_has_field_type(ftp):
    		return True
    	return False

    def has_hw(self):
    	ftp=FieldType.objects.get(key='hw')
    	if self.rep_has_field_type(ftp):
    		return True
    	return False

    def has_no_hw(self):
    	ftp=FieldType.objects.get(key='nh')
    	if self.rep_has_field_type(ftp):
    		return True
    	return False

    def as_verbose_string(self):
        verbose = _("%s Report: ") % self.type.name
        verbose += _("Patient=%s, ") % self.patient
        verbose += _("Location=%s") % self.location
        if self.village:
            verbose += _(" (%s)") % self.village

        summary = self.summary()
        if summary:
            verbose += ", " + self.summary()
        return verbose

    def set_date_string(self, date_string):
        """
        Trap anybody setting the date_string and try to set the date from it.
        """
        self.date_string = date_string

        # try to parse the date.. dd/mm/yyyy
        try:
            self.date = datetime.datetime.strptime(date_string, "%d.%m.%Y").date()
        except ValueError,e:
            # no-op, just keep the date_string value
            pass


    @classmethod
    def get_reports_with_edd_in(cls, date, days, reminder_type):
        """
        Returns all the reports which have an EDD within ``days`` of ``date``.  The results
        will be filtered to not include items which have at least one reminder of the passed
        in type.
        """
        (start, end) = cls.calculate_reminder_range(date, days)

        # only check pregnancy reports
        # TODO: should we check others as well?  not sure what the date means in RISK reports
        # For now we assume everybody needs to register with a pregnancy report first
        preg_type = ReportType.objects.get(pk=4)

        # we only allow one report per patient
        reports = {}

        # filter our reports based on which have not received a reminder yet.
        # TODO: this is simple, but could get slow, at some point it may be worth
        # replacing it with some fancy SQL
        for report in Report.objects.filter(date__gte=start, date__lte=end, type=preg_type):
            if not report.reminders.filter(type=reminder_type):
                reports[report.patient.national_id] = report

        return reports.values()
    
    @classmethod
    def calculate_edd(cls, last_menses):
        """
        Given the date of the last menses, figures out the expected delivery date
        """
            
        # first add seven days
        edd = last_menses + datetime.timedelta(7)

        # figure out if your year needs to be modified, anything later than march will
        # be the next year
        #	if edd.month > 3:
        #	    edd = edd.replace(year=edd.year+1, month=edd.month+9-12)
        #	else:
        #	    edd = edd.replace(month=edd.month+9)
        
        #	return edd

        neufmois = datetime.timedelta(days = 270)
        return edd + neufmois

    @classmethod
    def calculate_last_menses(cls, edd):
        """
        Given an EDD, figures out the last menses date.  This is basically the opposite
        function to calculate_edd
        """
        # figure out if your year needs to be modified, anything earlier than october
        # will be in the previous year
        #   if edd.month <= 9:
        #       last_menses = edd.replace(year=edd.year-1, month=edd.month-9+12)
        #   else:
        #       last_menses = edd.replace(month=edd.month-9)

        # now subtract 7 days
        #   last_menses = last_menses - datetime.timedelta(7)
        
        #   return last_menses
        return edd - datetime.timedelta(days = 277)

    @classmethod
    def calculate_reminder_range(cls, date, days):
        """
        Passed in a day (of today), figures out the range for the menses dates for
        our reminder.  The ``days`` variable is the number of days before delivery
        we want to figure out the date for.  (bracketed by 2 days each way)
        
        """
        # figure out the expected delivery date
        edd = date + datetime.timedelta(days)

        # calculate the last menses
        last_menses = cls.calculate_last_menses(edd)

        # bracket in either direction
        start = last_menses - datetime.timedelta(2)
        end = last_menses + datetime.timedelta(2)
    
        return (start, end)

    def is_risky(self):
        risk = FieldType.objects.filter(key__in =['ps','ds','sl','pc','af','ja','cm','mc','ns','fp','oe','un','ch','sa','co','vo','he','pa','rb','hy','fe','ma','di','ci','sc'])
        preg   = [ReportType.objects.get(name = 'Pregnancy'),ReportType.objects.get(name = 'RISK'),ReportType.objects.get(name = 'ANC')]
        all_risks=[]
        #for me in Report.objects.filter(patient = self.patient, type__in = preg):
	for r in self.fields.all(): 
		if r.type in risk: return True#all_risks.append(r.type)		
    	#if len(all_risks)!=0: return True
        return False

    def is_high_risky_preg(self):
    	risk = FieldType.objects.filter(key__in =['ps','ds','sl','ja','fp','un','sa','co','he','pa','ma','sc'])
    	preg   = [ReportType.objects.get(name = 'Pregnancy'),ReportType.objects.get(name = 'RISK'),ReportType.objects.get(name = 'ANC')]
        all_risks=[]
        for me in Report.objects.filter(patient = self.patient, type__in = preg):
            for r in me.fields.all(): 
    	    	if r.type in risk: all_risks.append(r.type)
    	if len(all_risks)!=0: return True
        return False

    def show_edd(self):
    	return self.calculate_edd(self.date)
    	    
class TriggeredText(models.Model):
    """ Represents an automated text response that is returned to the CHW, SUP or district SUP based 
        on a set of matching action codes. """

    DESTINATION_CHW = 'CHW'
    DESTINATION_SUP = 'SUP'
    DESTINATION_DIS = 'DIS'
    DESTINATION_AMB = 'AMB'

    DESTINATION_CHOICES = ( (DESTINATION_CHW, "Community Health Worker"),
                            (DESTINATION_SUP, "Clinic Supervisor"),
                            (DESTINATION_DIS, "District Supervisor"),
                            (DESTINATION_AMB, "Ambulance"))
    
    name = models.CharField(max_length=128)
    destination = models.CharField(max_length=3, choices=DESTINATION_CHOICES,
                                   help_text="Where this text will be sent to when reports match all triggers.")

    description = models.TextField()
    
    message_kw = models.CharField(max_length=160)
    message_fr = models.CharField(max_length=160)
    message_en = models.CharField(max_length=160)

    triggers = models.ManyToManyField(FieldType,
                                      help_text="This trigger will take effect when ALL triggers match the report.")

    active = models.BooleanField(default=True)
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )


    def trigger_summary(self):
        return ", ".join(map(lambda t: t.description, self.triggers.all()))
    
    def recipients(self):
        return ", ".join(map(lambda a: a.recipient, self.actions.all()))
    
    def __unicode__(self):
        return self.name

    @classmethod
    def get_triggers_for_report(cls, report):
        """
        Returns which trigger texts match this report.
        It is up to the caller to actually send the messages based on the triggers returned.
        """
        types = []
        for field in report.fields.all():
            types.append(field.type.pk)
               
        # these are the texts which may get activated
        texts = TriggeredText.objects.filter(triggers__in=types).distinct().order_by('id')

        # triggers that should be sent back, one per destination
        matching_texts = []
            
        # for each trigger text, see whether we should be triggered by it
        for text in texts:
            matching = True
            
            for trigger in text.triggers.all():
                found = False

                for field in report.fields.all():
                    if trigger.pk == field.type.pk:
                        found = True
                        break
                    
                # not found?  this won't trigger
                if not found:
                    matching = False
            
            if matching:
                matching_texts.append(text)

        # sort the texts, first by number of triggers (more specific texts should be triggered
        # before vague ones) then by id (earliest triggers should take precedence)
        matching_texts.sort(key=lambda tt: "%04d_%06d" % (len(tt.triggers.all()), 100000 - tt.pk))
        matching_texts.reverse()

        # now build a map containing only one trigger per destination
        per_destination = {}
        for tt in matching_texts:
            if not tt.destination in per_destination:
                per_destination[tt.destination] = tt
                
        # return our trigger texts
        matching_list = per_destination.values()
        matching_list.sort(key=lambda tt: tt.pk)
        return matching_list

class ReminderType(models.Model):
    """
    Simple models to keep track of the differen kinds of reminders.
    """

    name = models.CharField(max_length=255)

    message_kw = models.CharField(max_length=160)
    message_fr = models.CharField(max_length=160)
    message_en = models.CharField(max_length=160)

    def __unicode__(self):
        return self.name
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

class Reminder(models.Model):
    """
    Logs reminders that have been sent.  We use this both for tracking and so that we do
    not send more than one reminder at a time.
    """
    reporter = models.ForeignKey(Reporter)
    report = models.ForeignKey(Report, related_name="reminders", null=True)
    type = models.ForeignKey(ReminderType)
    date = models.DateTimeField()

    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

    def __unicode__(self):
			return "Reminder Type:%s   Sent:(%s)   Patient:%s   Location:%s   Reporter:%s" % (self.type, self.date,self.report.patient if self.report else None,self.reporter.location, self.reporter.connection().identity)

    @classmethod
    def get_expired_reporters(cls, today):
        # we'll check anybody who hasn't been seen in between 15 and 45 days
        expired_start = today - datetime.timedelta(45)
        expired_end = today - datetime.timedelta(15)

        # reporter reminder type
        expired_type = ReminderType.objects.get(pk=6)

        reporters = set()

        for reporter in Reporter.objects.filter(connections__last_seen__gt = expired_start,
                                                connections__last_seen__lt = expired_end):
            # get our most recent reminder
            reminders = Reminder.objects.filter(reporter=reporter, type=expired_type).order_by('-date')

            # we've had a previous reminder
            if reminders:
                last_reminder = reminders[0]
                # if we were last seen before the reminder, we've already been reminded, skip over
                if reporter.last_seen() < last_reminder.date:
                    continue

            # otherwise, pop this reporter on
            reporters.add(reporter)

        return reporters

class HealthTarget(models.Model):
    name        = models.TextField()
    description = models.TextField()
    positive    = models.BooleanField()
    target      = models.IntegerField()
    
    def __unicode__(self):
        return self.description

    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

class LocationShorthand(models.Model):
    'Memoization of locations, so that they are more-efficient in look-up.'

    original = models.ForeignKey(Location, related_name = 'locationslocation')
    district = models.ForeignKey(Location, related_name = 'district')
    province = models.ForeignKey(Location, related_name = 'province')

    def __unicode__(self):
        return str(self.original)

    def __int__(self):
        return self.id

    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

class Refusal(models.Model):
    'This represents refusals to give a health agent information. We keep instead a reference to the reporter, in order to follow up, if necessary.'

    reporter = models.ForeignKey(Reporter, related_name = 'jilted_reporter')
    refid    = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
        return self.reporter.connection().identity

    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

class ErrorNote(models.Model):
    '''This model is used to record errors made by people sending messages into the system, to facilitate things like studying which format structures are error-prone, and which reporters make the most errors, and other things like that.'''

    errmsg  = models.TextField()
    errby   = models.ForeignKey(Reporter, related_name = 'erring_reporter')
    created = models.DateTimeField(auto_now_add = True)

    def __unicode__(self):
        return '%s (%s): "%s"' % (str(self.errby.connection().identity), str(self.created), str(self.errmsg))

    def __int__(self):
        return self.id
    class Meta:
        
        # define a permission for this app to use the @permission_required
        # in the admin's auth section, we have a group called 'manager' whose
        # users have this permission -- and are able to see this section
        permissions = (
            ("can_view", "Can view"),
        )

class UserLocation(models.Model):
	"""This model is used to help the system to know where the user who is trying to access this information is from"""
	user=models.ForeignKey(User)
	location=models.ForeignKey(Location)
	def __unicode__(self):
		return '%s : "%s"' % (str(self.user), str(self.location))

	def __int__(self):
		return self.id
	class Meta:
        
		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)

class TriggeredAlert(models.Model):
    """
                        Logs alerts that have been sent. """
    reporter = models.ForeignKey(Reporter)
    report = models.ForeignKey(Report, related_name="alerts", null=True)
    trigger=models.ForeignKey(TriggeredText)
    date = models.DateTimeField(auto_now_add=True)
    def __unicode__(self):
		return '%s : "%s"' % (str(self.id), str(self.trigger))

    def __int__(self):
    	return self.id
    class Meta:
        
		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)
class AncStats(models.Model):
	"""This is useful for increase the querying on DB for the information of long period"""
	report=models.ForeignKey(Report,unique=True)
	is_anc1=models.BooleanField(default=False)#ANC1 for preg or ANC2,ANC3,ANC4,DP for ANC
	is_stard = models.BooleanField(default=False)
	is_anc2= models.BooleanField(default=False)
	is_anc3=models.BooleanField(default=False)
	is_anc4=models.BooleanField(default=False)
	is_dp=models.BooleanField(default=False)
	recent_preg=models.ForeignKey(Report,related_name='recentpregnancy')#This recent pregnancy allows to check if the patient has attended all ANCs
	has_all=models.BooleanField(default=False)#Does the patient attended all ANCs for the recent pregnancy
	original = models.ForeignKey(Location, related_name = 'isanteri')
	district = models.ForeignKey(Location, related_name = 'akarere')
	province = models.ForeignKey(Location, related_name = 'intara')
	created = models.DateTimeField(null=False)
	def __unicode__(self):
		return str(self.report)

	def __int__(self):
		return self.id

	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)

class PregStat(models.Model):
	"""This is useful for increase the querying on DB for the information of long period"""
	report=models.ForeignKey(Report,unique=True)
	is_high_risk=models.BooleanField(default=False)
	is_risk=models.BooleanField(default=False)
	has_toilet = models.BooleanField(default=False)
	has_hand_wash= models.BooleanField(default=False)
	edd=models.DateField(null=False)
	recent_preg=models.ForeignKey(Report,related_name='recent_preg')#This recent pregnancy allows to check if the patient has attended all ANCs
	original = models.ForeignKey(Location, related_name = 'preg_isanteri')
	district = models.ForeignKey(Location, related_name = 'preg_akarere')
	province = models.ForeignKey(Location, related_name = 'preg_intara')
	created = models.DateTimeField(null=False)
	def __unicode__(self):
		return str(self.report)

	def __int__(self):
		return self.id

	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)


class GlobalStatistic(models.Model):
	"""I need to start to field and back to report instead of report back to fields because in a report has got many fields you need another kind of filtering which reduce the querying speed"""

	field=models.ForeignKey(Field,unique=True)
	report=models.ForeignKey(Report)
	report_type=models.ForeignKey(ReportType, db_index=True)
	key = models.CharField(max_length=32, db_index=True)
	unknown_loc=models.BooleanField(default=False)
	original = models.ForeignKey(Location, related_name = 'global_stats_isanteri', db_index=True)
	district = models.ForeignKey(Location, related_name = 'global_stats_akarere', db_index=True)
	province = models.ForeignKey(Location, related_name = 'global_stats_intara', db_index=True)
	created = models.DateTimeField(null=False, db_index=True)
	def __unicode__(self):
		return str(self.field)

	def __int__(self):
		return self.id

	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)

class LastRecord(models.Model):
	""" be aware of last record to update statistics tables"""	
	report=models.ForeignKey(Report, unique=True)
	preg=models.ForeignKey(Report, unique=True, related_name ="last_pregnancy")
	anc=models.ForeignKey(Report, unique=True, related_name ="last_anc")
	birth=models.ForeignKey(Report, unique=True, related_name ="last_birth")
	chihe=models.ForeignKey(Report, unique=True, related_name ="last_chihe")	
	risk=models.ForeignKey(Report, unique=True, related_name ="last_risk")	
	field=models.ForeignKey(Field, unique=True)
	report_field=models.IntegerField(unique=True)
	
	def __unicode__(self):
		return str(self.report)

	def __int__(self):
		return self.id

	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)
	"""
class FacilityType(models.Model):
	name = models.CharField(max_length=100)
    
    
	class Meta:
		verbose_name = "Type"
    
	def __unicode__(self):
		return self.name

class HealthFacility(models.Model):
	fosa_type = models.ForeignKey(FacilityType)
	fosa_name = models.CharField(max_length=32)
	fosa_code = models.CharField(max_length=30, unique=True)
	province_code = models.CharField(max_length=30, unique=True)
	province_name = models.CharField(max_length=32)
	district_code = models.CharField(max_length=30, unique=True)
	district_name = models.CharField(max_length=32)
	sector_code = models.CharField(max_length=30, unique=True)
	sector_name = models.CharField(max_length=32)
	cell_code = models.CharField(max_length=30, unique=True)
	cell_name = models.CharField(max_length=32)
	village_code = models.CharField(max_length=30, unique=True)
	village_name = models.CharField(max_length=32)
	latitude  = models.DecimalField(max_digits=8, decimal_places=6, blank=True, null=True, help_text="The physical latitude of this location")
	longitude = models.DecimalField(max_digits=8, decimal_places=6, blank=True, null=True, help_text="The physical longitude of this location")

"""

