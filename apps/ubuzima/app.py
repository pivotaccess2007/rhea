
import rapidsms

from rapidsms.parsers.keyworder import Keyworder
import re
from apps.ambulances.models import *
from apps.locations.models import Location
from apps.ubuzima.models import *
from apps.reporters.models import *
from django.utils.translation import ugettext as _
from django.utils.translation import activate, get_language
from decimal import *
from exceptions import Exception
import traceback
from datetime import *
from time import *
from django.db.models import Q


class App (rapidsms.app.App):
    
    # map of language code to language name
    LANG = { 'en': 'English',
             'fr': 'French',
             'rw': 'Kinyarwanda' }
    
    keyword = Keyworder()
    
    def start (self):
        """Configure your app in the start phase."""
    	
        pass
   

    def parse (self, message):
        """Parse and annotate messages in the parse phase."""
    	
        pass
    
    
    	

    def handle (self, message):
        """Add your main application logic in the handle phase."""
        results = self.keyword.match(self, message.text)
        
        # do we know this reporter?
        rpt = getattr(message, 'reporter', None)
        if rpt:
            activate(message.reporter.language)
        else:
            activate('rw')
        
        if results:
            try:
                func, captures = results
                return func(self, message, *captures)
            except Exception, e:
                self.debug("Error: %s %s" % (e, traceback.format_exc()))
                print "Error: %s %s" % (e, traceback.format_exc())
                if rpt:
                    err = ErrorNote(errmsg = message.text, errby = rpt)
                    err.save()
                message.respond(_("Unknown Error, please check message format and try again."))
                return True
        else:
            if rpt:
                err = ErrorNote(errmsg = message.text, errby = rpt)
                err.save()
            self.debug("NO MATCH FOR %s" % message.text)
            message.respond(_("Unknown keyword, please check message format and try again."))
            return True
    
    def cleanup (self, message):
        """Perform any clean up after all handlers have run in the
           cleanup phase."""
        pass

    def outgoing (self, message):
        """Handle outgoing message notifications."""
        pass

    def stop (self):
        """Perform global app cleanup when the application is stopped."""
        pass
    
    @keyword("\s*(sup|reg)(.*)")
    def sup_or_reg(self, message, keyword, rest):
        """Handles both incoming REG and SUP commands, creating the appropriate Reporter object, 
           stashing away the attributes and making the connection with this phone number. """
           
        self.debug("SUP message: %s" % message.text)
        m = re.search("^\s*(\w+)\s+(\d+)\s+(\d+)(.*)$", message.text, re.IGNORECASE)
        if not m:
            # give appropriate error message based on the incoming message type
            if keyword.lower() == 'SUP':
                message.respond(_("The correct message format is: SUP YOUR_ID CLINIC_ID LANG VILLAGE"))
            else:
                message.respond(_("The correct message format is: REG YOUR_ID CLINIC_ID LANG VILLAGE"))
            return True

        received_nat_id = m.group(2)
        
        if len(received_nat_id) != 16:
            message.respond(_("Error.  National ID must be exactly 16 digits, you sent the id: %(nat_id)s") % 
                            { "nat_id": received_nat_id } )
            return True
        
        received_clinic_id = m.group(3)
        optional_part = m.group(4)
        
        # do we already have a report for our connection?
        # if so, just update it
        if not getattr(message, 'reporter', None):
    	    try:
		    rep= Reporter.objects.get(alias=received_nat_id)
		    message.reporter=rep
    	    except Exception, e:
            # there were invalid reporter, respond and exit
            	message.respond(_("Please contact your Health Centre to register your National ID"))
            	return True
            
        # connect this reporter to the connection
        message.persistant_connection.reporter = message.reporter
        message.persistant_connection.save()
        
        # read our clinic
        clinic = Location.objects.filter(code=fosa_to_code(received_clinic_id))
        
        # not found?  That's an error
        if not clinic:
            message.respond(_("Unknown Health Clinic ID: %(clinic)s") % \
                            { "clinic": received_clinic_id})
            return True
        
        clinic = clinic[0]
        
        # set the location for this reporter
        message.reporter.location = clinic
        
        # set the group for this reporter based on the incoming keyword
        group_title = 'Supervisor' if (keyword.lower() == 'sup') else 'CHW' 
        
        group = ReporterGroup.objects.get(title=group_title)
        message.reporter.groups.add(group)
        
        m2 = re.search("(\s*)(fr|en|rw)(\s.*)", optional_part, re.IGNORECASE)
    
        lang = "rw"
        if m2:
            lang = m2.group(2).lower()
                        
            # build our new optional part, which is just the remaining stuff
            optional_part = ("%s %s" % (m2.group(1), m2.group(3))).strip()

        # save away the language
        message.reporter.language = lang

        # and activate it
        activate(lang)
    	
        # if we actually have remaining text, then save that away as our village name
        if optional_part:
            message.reporter.village = optional_part
            
        # save everything away
        message.reporter.save()
    	#create a Registration Report 
    	report=Report(reporter=message.reporter,location=clinic,village=message.reporter.village,type=ReportType.objects.get(name="Registration"),patient=Patient.objects.get_or_create(national_id=received_nat_id,location=clinic)[0])
    	report.save()
        message.respond(_("Thank you for registering at %(clinic)s") % \
                        { 'clinic': clinic.name } )
        
        return True
        
    @keyword("\s*who")
    def who(self, message):
        """Returns what we know about the sender of this message.  This is used primarily for unit
           testing though it may prove usefu in the field"""
           
        if getattr(message, 'reporter', None):
            if not message.reporter.groups.all():
                message.respond(_("You are not in a group, located at %(location)s, you speak %(language)s") % \
                    { 'location': message.reporter.location.name, 'language': App.LANG[message.reporter.language] } )          
            else:
                location = message.reporter.location.name
                if message.reporter.village:
                    location += " (%s)" % message.reporter.village

                message.respond(_("You are a %(group)s, located at %(location)s, you speak %(language)s") % \
                    { 'group': message.reporter.groups.all()[0].title, 'location': location, 'language': App.LANG[message.reporter.language] } )
            
        else:
            message.respond(_("We don't recognize you"))
        return True
    
    
    def parse_dob(self, dob_string):
        """Tries to parse a string into some kind of date representation.  Note that we don't use Date objects
           to store things away, because we want to accept limited precision dates, ie, just the year if 
           necessary."""
           
        # simple #### date.. ie, 1987 or 87
        m3 = re.search("^(\d+)$", dob_string)
    
        if m3:
            value = m3.group(1)
            
            # two digit date, guess on the first digits based on size
            if len(value) == 2:
                if int(value) <= date.today().year % 100:
                    value = "20%s" % value
                else:
                    value = "19%s" % value
                                
            # we have a four digit date, does it look reasonable?
            if len(value) == 4:
                return value
                    
        # full date: DD.MM.YYYY
        m3 = re.search("^(\d+)\.(\d+)\.(\d+)$", dob_string) 
        if m3:
            dd = m3.group(1)
            mm = m3.group(2)
            yyyy = m3.group(3)
            
            # print "%s = '%s' '%s' '%s'" % (dob_string, dd, mm, yyyy)
            
            # make sure we are in the right format
            if len(dd) > 2 or len(mm) > 2 or len(yyyy) > 4: 
                raise Exception(_("Invalid date format, must be in the form: DD.MM.YYYY"))

            # invalid month
            if int(mm) > 12 or int(mm) < 1:
                raise Exception(_("Invalid date format, must be in the form: DD.MM.YYYY"))
            
            # invalid day
            if int(dd) > 31 or int(dd) < 1:
                raise Exception(_("Invalid date format, must be in the form: DD.MM.YYYY"))
            
            # is the year in the future
            if int(yyyy) > int(date.today().year):
                raise Exception(_("Invalid date, cannot be in the future."))
		    #is the the date in future
    	    dob="%02d.%02d.%04d" % (int(dd), int(mm), int(yyyy))
    	    if datetime.strptime(dob,"%d.%m.%Y").date() > date.today():
    	    	raise Exception(_("Invalid date, cannot be in the future."))
            
            # Otherwise, parse into our format
            return "%02d.%02d.%04d" % (int(dd), int(mm), int(yyyy))
            
        return None
    
    def read_fields(self, code_string, accept_date=False, weight_is_mothers=False):
        """Tries to parse all the fields according to our set of action and movement codes.  We also 
           try to figure out if certain fields are dates and stuff them in as well. """
        
        # split our code string by spaces
        codes = code_string.split()
        fields = []
        invalid_codes = []
        num_mov_codes = 0
        
        # the dob we might extract from this
        dob = None
        
        # for each code
        for code in codes:
            try:
                # first try to look up the code in the DB
                field_type = FieldType.objects.get(key=code.lower())
                fields.append(Field(type=field_type))
                7
                # if the action code is a movement code, increment our counter of movement codes
                # messages may only have one movement code
                if field_type.category.id == 4:
                    num_mov_codes += 1

            # didn't recognize this code?  then it is a scalar value, run some regexes to derive what it is
            except FieldType.DoesNotExist:
                m1 = re.search("(\d+\.?\d*)(k|kg|kilo|kilogram)", code, re.IGNORECASE)
                m2 = re.search("(\d+\.?\d*)(c|cm|cent|centimeter)", code, re.IGNORECASE)
                
                # this is a weight
                if m1:
                    field_type = FieldType.objects.get(key="child_weight" if not weight_is_mothers else "mother_weight")
                    value = Decimal(m1.group(1))
                    field = Field(type=field_type, value=value)
                    fields.append(field)
                    
                # this is a length
                elif m2:
                    field_type = FieldType.objects.get(key="muac")
                    value = Decimal(m2.group(1))
                    field = Field(type=field_type, value=value)
                    fields.append(field)
                    
                # unknown
                else:
                    # try to parse as a dob
                    date = self.parse_dob(code)

                    if accept_date and date:
                        dob = date
                    else:
                        invalid_codes.append(code)

        # take care of any error messaging
        error_msg = ""
        if len(invalid_codes) > 0:
            error_msg += _("Unknown action code: %(invalidcode)s.  ") % \
                { 'invalidcode':  ", ".join(invalid_codes)}
            
        if num_mov_codes > 1:
            error_msg += unicode(_("You cannot give more than one location code"))
        
        if error_msg:
            error_msg = _("Error.  %(error)s") % { 'error': error_msg }
            
            # there's actually an error, throw it over the fence
            raise Exception(error_msg)
        
        return (fields, dob)
    
    def get_or_create_patient(self, reporter, national_id):
        """Takes care of searching our DB for the passed in patient.  Equality is determined
           using the national id only (IE, dob doesn't come into play).  This will create a 
           new patient with the passed in reporter if necessary."""
           
        # try to look up the patent by id
        try:
            patient = Patient.objects.get(national_id=national_id)
        except Patient.DoesNotExist:
            # not found?  create the patient instead
            patient = Patient.objects.create(national_id=national_id,
                                             location=reporter.location)
                
        return patient
    
    def create_report(self, report_type_name, patient, reporter):
        """Convenience for creating a new Report object from a reporter, patient and type """
        
        report_type = ReportType.objects.get(name=report_type_name)
        report = Report(patient=patient, reporter=reporter, type=report_type,
                        location=reporter.location, village=reporter.village)
        return report
    
    def run_triggers(self, message, report):
        """Called whenever we get a new report.  We run our triggers, figuring out if there 
           are messages to send out to supervisors.  We return the message that should be sent
           to the reporter themselves, or None if there is no matching trigger for the reporter."""
        # find all matching triggers
        triggers = TriggeredText.get_triggers_for_report(report)

        # the message we'll send back to the reporter
        reporter_message = None

        # for each one
        for trigger in triggers:
            lang = get_language()
            alert=TriggeredAlert(reporter=report.reporter, report=report, trigger=trigger)
            alert.save()
            curloc = report.location
            if trigger.destination == TriggeredText.DESTINATION_AMB:
                while curloc:
                    ambs = AmbulanceDriver.objects.filter(location = curloc)
                    if len(ambs) < 1:
                        curloc = curloc.parent
                        continue
                    for amb in ambs: amb.send_notification(message, report)
                    break

            # if the destination is the supervisor
            elif trigger.destination != TriggeredText.DESTINATION_CHW:
                reporter_ident = report.reporter.connection().identity
                sup_group = ReporterGroup.objects.get(title='Supervisor')
        
                # figure out what location we'll use to find supervisors
                location = report.reporter.location

                # if we are supposed to tell the district supervisor and our current location 
                # is a health clinic, then walk up the tree looking for a hospital
                if trigger.destination == TriggeredText.DESTINATION_DIS and location.type.pk == 5:  # health center
                    # find the parent
                    if location.parent:
                        location = location.parent
                    # couldn't find it?  oh well, we'll alert the normal supervisor
                    
                # now look up to see if we have any reporters in this group 
                # with the same location as  our reporter
                sups = Reporter.objects.filter(groups=sup_group, location=location).order_by("pk")

                # for each supervisor
                for sup in sups:
                    # load the connection for it
                    conn = sup.connection()
                    lang = sup.language

                    # get th appropriate message to send
                    text = trigger.message_kw
                    if lang == 'en':
                        text = trigger.message_en
                    elif lang == 'fr':
                        text = trigger.message_fr
                
                    # and send this message to them
                    forward = _("%(phone)s: %(text)s" % { 'phone': reporter_ident, 'text': text })

                    message.forward(conn.identity, forward)

            # otherwise, this is just a response to the reporter
            else:
                # calculate our message based on language, we'll return it in a bit
                lang = get_language()
                reporter_message = trigger.message_kw
                if lang == 'en':
                    reporter_message = trigger.message_en
                elif lang == 'fr':
                    reporter_message = trigger.message_fr

        # return our advice texts
        return reporter_message
    
    def cc_supervisor(self, message, report):
        """ CC's the supervisor of the clinic for this CHW   """
        
        # look up our supervisor group type
        sup_group = ReporterGroup.objects.get(title='Supervisor')
        
        # now look up to see if we have any reporters in this group with the same location as 
        # our reporter
        sups = Reporter.objects.filter(groups=sup_group, location=message.reporter.location).order_by("pk")
        
        # reporter identity
        reporter_ident = message.reporter.connection().identity
	
	#reporter village
	reporter_village = message.reporter.village
        
        # we have at least one supervisor
        if sups:
            for sup in sups:
                # load the connection for it
                conn = sup.connection()
                
                # and send this message to them
                forward = _("%(phone)s: %(report)s" % { 'phone': reporter_ident, 'report': report.as_verbose_string() })
                message.forward(conn.identity, forward)

    @keyword("\s*pre(.*)")
    def pregnancy(self, message, notice):
        """Incoming pregnancy reports.  This registers a new mother as having an upcoming child"""

        self.debug("PRE message: %s" % message.text)

        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True

        m = re.search("pre\s+(\d+)\s+([0-9.]+)\s?(.*)", message.text, re.IGNORECASE)
        if not m:
            message.respond(_("The correct format message is: PRE MOTHER_ID LAST_MENSES ACTION_CODE LOCATION_CODE MOTHER_WEIGHT"))
            return True
        
        received_patient_id = m.group(1)
        
        try:
            last_menses = self.parse_dob(m.group(2))
        except Exception, e:
            # date was invalid, respond
            message.respond("%s" % e)
            return True
            
        optional_part = m.group(3)

        # get or create the patient
        patient = self.get_or_create_patient(message.reporter, received_patient_id)
        
        # create our report
        report = self.create_report('Pregnancy', patient, message.reporter)

        report.set_date_string(last_menses)
        
        # read our fields
        try:
            (fields, dob) = self.read_fields(optional_part, False, True)
        except Exception, e:
            # there were invalid fields, respond and exit
            message.respond("%s" % e)
            return True
        
        # save the report
    	if not report.has_dups():
        	report.save()
        else:
    		message.respond(_("This report has been recorded, and we cannot duplicate it again. Thank you!"))
    		return True
        # then associate all our fields with it
        for field in fields:
            field.save()
            report.fields.add(field)            

        # either return an advice text, or our default text for this message type
        response = self.run_triggers(message,report)
        if response:
            message.respond(response)
        else:
            message.respond(_("Thank you! Pregnancy report submitted successfully."))
            
        # cc the supervisor if there is one
        self.cc_supervisor(message, report)
  
        
        return True
    
    @keyword("\s*risk(.*)")
    def risk(self, message, notice):
        """Risk report, represents a possible problem with a pregnancy, can trigger alerts."""
        
        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
            
        m = re.search("risk\s+(\d+)(.*)", message.text, re.IGNORECASE)
        if not m:
            message.respond(_("The correct format message is: RISK MOTHER_ID ACTION_CODE LOCATION_CODE MOTHER_WEIGHT"))
            return True
        received_patient_id = m.group(1)
        optional_part = m.group(2)
        
        # get or create the patient
        patient = self.get_or_create_patient(message.reporter, received_patient_id)

        report = self.create_report('Risk', patient, message.reporter)
        
        # Line below may be needed in case Risk reports are sent without previous Pregnancy reports
        location = message.reporter.location
        
        # read our fields
        try:
            (fields, dob) = self.read_fields(optional_part, False, True)
        except Exception, e:
            # there were invalid fields, respond and exit
            message.respond("%s" % e)
            return True

        # save the report
        report.save()
        
        # then associate all the action codes with it
        for field in fields:
            field.save()
            report.fields.add(field)
            
        # either send back our advice text or our default response
        response = self.run_triggers(message, report)
        if response:
            message.respond(response)
        else:
            message.respond(_("Thank you! Risk report submitted successfully."))
            
        # cc the supervisor if there is one
        self.cc_supervisor(message, report)
        

        return True
    
    #Birth keyword
    @keyword("\s*bir(.*)")
    def birth(self, message, notice):
        """Birth report.  Sent when a new mother has a birth.  Can trigger alerts with particular action codes"""
        
        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
            
        #	m = re.search("bir\s+(\d+)\s+(\d+)(.*(cl|ho|hp|or).*)", message.text, re.IGNORECASE)
        m = re.search(r'bir\s+(\d+)\s+(\d+)\s+(.*(\s+(cl|ho|hp|or)\s+).*)', message.text, re.IGNORECASE)
        if not m:
            message.respond(_("The correct format message is: BIR MOTHER_ID CHILD_NUM ACTION_CODE LOCATION_CODE CHILD_WEIGHT MUAC"))
            return True
        received_patient_id = m.group(1)
        received_child_num = m.group(2)
        optional_part = m.group(3)
        
        # get or create the patient
        patient = self.get_or_create_patient(message.reporter, received_patient_id)
        
        report = self.create_report('Birth', patient, message.reporter)
        
        # read our fields
        try:
            (fields, dob) = self.read_fields(optional_part, True)
        except Exception, e:
            # there were invalid fields, respond and exit
            message.respond("%s" % e)
            return True

        # set the dob for the child if we got one
        if dob:
            report.set_date_string(dob)
            
        # set the child number
        child_num_type = FieldType.objects.get(key='child_number')
        fields.append(Field(type=child_num_type, value=Decimal(received_child_num)))

        # save the report
        if not report.has_dups():
        	report.save()
        else:
    		message.respond(_("This report has been recorded, and we cannot duplicate it again. Thank you!"))
    		return True
        
        # then associate all the action codes with it
        for field in fields:
            field.save()
            report.fields.add(field)            
        
        # either send back the advice text or our default msg
        response = self.run_triggers(message, report)
        if response:
            message.respond(response)
        else:
            message.respond(_("Thank you! Birth report submitted successfully."))
            
        # cc the supervisor if there is one
        self.cc_supervisor(message, report)
    	        
        return True
    
        #Birth keyword
    @keyword("\s*chi(.*)")
    def child(self, message, notice):
        """Child health report.  Ideally should be on a child that was previously registered, but if not that's ok."""
        
        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
            
        m = re.search("chi\s+(\d+)\s+(\d+)(.*)", message.text, re.IGNORECASE)
        if not m:
            message.respond(_("The correct format message is: CHI MOTHER_ID CHILD_NUM CHILD_DOB MOVEMENT_CODE ACTION_CODE MUAC WEIGHT"))
            return True
        received_patient_id = m.group(1)
        received_child_num = m.group(2)
        optional_part = m.group(3)
        
        # get or create the patient
        patient = self.get_or_create_patient(message.reporter, received_patient_id)
        
        report = self.create_report('Child Health', patient, message.reporter)
        
        # read our fields
        try:
            (fields, dob) = self.read_fields(optional_part, True)
        except Exception, e:
            # there were invalid fields, respond and exit
            message.respond("%s" % e)
            return True

        # set the dob for the child if we got one
        if dob:
            report.set_date_string(dob)

        # set the child number
        child_num_type = FieldType.objects.get(key='child_number')
        fields.append(Field(type=child_num_type, value=Decimal(received_child_num)))

        # save the report
        report.save()
        
        # then associate all the action codes with it
        for field in fields:
            field.save()
            report.fields.add(field)            
    
        # respond either with our advice text or our default msg
        response = self.run_triggers(message, report)
        if response:
            message.respond(response)
        else:
            message.respond(_("Thank you! Child health report submitted successfully."))
            
        # cc the supervisor if there is one
        self.cc_supervisor(message, report)
            
        return True
    
    @keyword("\s*last")
    def last(self, message):
        """Echos the last report that was sent for this report.  This is primarily used for unit testing"""
        
        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
    
        reports = Report.objects.filter(reporter=message.reporter).order_by('-pk')
    
        if not reports:
            message.respond(_("You have not yet sent a report."))
            return True
    
        report = reports[0]
        
        fields = []
        for field in report.fields.all().order_by('type'):
            fields.append(unicode(field))
            
        dob = _(" Date: %(date)s") % { 'date': report.date_string } if report.date_string else ""
        
        message.respond(report.as_verbose_string())
    	      
        return True      

#Didier new keys implementation
    @keyword("\s*anc(.*)")
    def anc(self, message, notice):
    	"""New Anc report. This is for regestering a new anc visit ."""
    	if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
    	
	m = re.search("anc\s+(\d+)\s?(.*)", message.text, re.IGNORECASE)
        if not m:
            message.respond(_("The correct format message is: ANC MOTHER_ID ..."))
            return True
    	received_patient_id = m.group(1)
	optional_part=m.group(2)
	anc_report=re.match("([0-9.]+)\s+(.*(\s*(anc2|anc3|anc4)\s*).*)",optional_part,re.IGNORECASE)
    	anc_dep=re.match("(dp)\s?(.*)",optional_part,re.IGNORECASE)
    	last_visit=date.today()
	if anc_report:
		try:
		    last_visit = self.parse_dob(anc_report.group(1))
		except Exception, e:
		    # date was invalid, respond
		    message.respond("%s" % e)
		    return True
		optional_part=anc_report.group(2)
    			
    	if anc_dep:
		pass		
	if not anc_report and not anc_dep:
		message.respond(_("The correct format message is: ANC MOTHER_ID LAST_VISIT ANC_ROUND ACTION_CODE MOTHER_WEIGHT"))
    	
    	if anc_report or anc_dep:
	    	# get or create the patient
		patient = self.get_or_create_patient(message.reporter, received_patient_id)

		# create our report
		report = self.create_report('ANC', patient, message.reporter)
    	#date of last visit
    	if anc_report:
    		report.set_date_string(last_visit)
	    	# read our fields
	try:
	    (fields, dob) = self.read_fields(optional_part,False, True)
	except Exception, e:
	    # there were invalid fields, respond and exit
	    message.respond("%s" % e)
	    return True

	# save the report
	if not report.has_dups():
        	report.save()
        else:
    		message.respond(_("This report has been recorded, and we cannot duplicate it again. Thank you!"))
    		return True
	
	# then associate all the action codes with it
	for field in fields:
	    field.save()
	    report.fields.add(field)            
	
	# either send back the advice text or our default msg
	if not Report.objects.filter(patient=patient,type__name='Pregnancy',created__gte=(date.today()-timedelta(270))):
		message.respond(_("Thank you! ANC report submitted. Please send also the pregnancy report of this patient %(patient)s") % { 'patient': patient.national_id })
		return True
	response = self.run_triggers(message, report)
	if response:
	    message.respond(response)
	else:
	    message.respond(_("Thank you! ANC report submitted successfully."))
	    
	# cc the supervisor if there is one
	self.cc_supervisor(message, report)
        return True 

    #   TODO:
    #   Muck with the translations.
    @keyword("\s*ref(.*)")
    def je_m_en_fou(self, message, notice):
        if not getattr(message, 'reporter', None):
            message.respond(_("You need to be registered first, use the REG keyword"))
            return True
    	rez = re.match(r'ref\s+(\d+)', message.text, re.IGNORECASE)
    	if not rez:
    	    message.respond(_('You never reported a refusal. Refusals are \
reported with the keyword REF'))
    	    return True
    	ref = Refusal(reporter = message.reporter, refid = rez.group(1))
    	ref.save()
        message.respond(_('It has been recorded.'))
        return True
#Didier end new keys 
