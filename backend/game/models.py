from django.db import models

class Widget(models.Model):
    name = models.CharField(max_length=255)
    qty = models.IntegerField(default=0)