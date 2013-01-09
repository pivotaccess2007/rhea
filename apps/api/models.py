from django.db import models
from ubuzima.models import *
import urllib2

# Create your Django models here, if you need them.

class NotificationType(models.Model):

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

class Concept(models.Model):
	name = models.CharField(max_length=30, blank=True)
	answer = models.CharField(max_length=30, blank=True)
	mapping = models.CharField(max_length=30, default = "RSMS", blank=True)
	mapping_code = models.CharField(max_length=30, blank=True)
	data_type = models.CharField(max_length=30, blank=True)
	value = models.CharField(max_length=30, default = "N/A", blank=True)
	
	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)
		

	
	def __unicode__(self):
		return "%s" % (self.name +"  "+ self.answer)

class Notification(models.Model):
	
	not_type = models.ForeignKey(NotificationType)
	message = models.TextField()
	report = models.ForeignKey(Report)
	created = models.DateTimeField(auto_now_add=True)
	class Meta:

		# define a permission for this app to use the @permission_required
		# in the admin's auth section, we have a group called 'manager' whose
		# users have this permission -- and are able to see this section
		permissions = (
		    ("can_view", "Can view"),
		)
		
		unique_together = ('report', 'not_type',)

	
	def __unicode__(self):
		return self.message

class LastNotification(models.Model):
	last_not=models.ForeignKey(Notification, unique=True,null=True)
	last_preg=models.ForeignKey(Report, unique=True,null=True, related_name="pre")
	last_risk=models.ForeignKey(Report, unique=True,null=True, related_name="risk")
	last_bir=models.ForeignKey(Report, unique=True,null=True, related_name="bir")
	last_mat=models.ForeignKey(Report, unique=True,null=True, related_name="mat")
	last_reg=models.ForeignKey(Reporter, unique=True,null=True, related_name="reg")
	last_field=models.ForeignKey(Field, unique=True,null=True, related_name="field")

class RheaRequest(models.Model):
	request = models.TextField()
	data = models.TextField()
	response = models.TextField()
	status_reason = models.CharField(max_length=30)
	
	
