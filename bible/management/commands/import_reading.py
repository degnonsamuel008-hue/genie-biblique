import csv
from django.core.management.base import BaseCommand
from bible.models import DailyReading
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
       with open('data/reading_plan_365.csv',encoding='utf-8') as f:
           for row in csv.DictReader(f):
               DailyReading.objects.get_or_create(
                   day_number=int(row['day_number']),
                   defaults={
                       'title':row['title'],
                       'reference':row['reference'],
                       'summary':row.get('summary','')
                   }
               )
       print("365 jours importés !")