from django.core.management.base import BaseCommand
from django.conf import settings
import urllib2
import time
import datetime
from optparse import make_option
from ubuzima.dbmodule import *

class Command(BaseCommand):
    help = "Build statistics and populate statistics tables.  This command should be run every five minutes via cron"
    
    def handle(self, **options):
        print "Running Build statistics and populate statistics tables..."

        if stats_tables_exists():
		if syncdb_ubuzima_db():	print "Build statistics and populate statistics tables Complete."
		else: print "Build statistics and populate statistics tables Incomplete."
	else:
		if generate_ubuzima_stats(): print "Build statistics and populate statistics tables Complete."
		else: print "Build statistics and populate statistics tables Incomplete."

