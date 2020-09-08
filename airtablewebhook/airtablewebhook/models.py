from django.db import models
import uuid

class AirtableEntry(models.Model):
    base_name                = models.CharField(max_length = 40)
    stop_name                = models.CharField(max_length = 350)
    stop_airtable_id         = models.CharField(max_length = 30)
    stop_salesforce_id       = models.CharField(max_length = 30)
    stop_date                = models.DateField()
    stop_address             = models.CharField(max_length = 400)
    stop_delivered           = models.BooleanField()
    stop_bottles_dropped_off = models.PositiveSmallIntegerField()
    stop_bottles_picked_up   = models.PositiveSmallIntegerField()
    stop_number              = models.PositiveSmallIntegerField()
    django_id                = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stop_notes               = models.CharField(max_length = 500)
    stop_phone_number        = models.CharField(max_length = 30)
    stop_apt_number          = models.CharField(max_length = 200)
    stop_bottles_to_deliver  = models.PositiveSmallIntegerField()
    method                   = models.CharField(max_length = 20, default = "Not Inserted")
    stop_equipment           = models.CharField(max_length = 250)
    stop_attachment          = models.CharField(max_length = 300)
    stop_bpa_free            = models.CharField(max_length = 30)
    stop_water_type          = models.CharField(max_length = 30)


class BaseNamesInUsage(models.Model):
    base_name  = models.CharField(max_length = 30)
    base_id    = models.CharField(max_length = 30)
    date       = models.DateField()