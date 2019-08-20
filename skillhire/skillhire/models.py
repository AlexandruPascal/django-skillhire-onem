from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Offer(models.Model):
    description = models.CharField(max_length=40, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    accessed_offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    date_created = models.DateTimeField('date_created', auto_now_add=True)
    date_accessed = models.DateTimeField('date_accessed', default=timezone.now)
