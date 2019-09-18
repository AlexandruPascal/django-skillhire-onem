from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from .validators import UsernameValidator


class Industry(models.Model):
    industry_name = models.CharField(max_length=35, blank=True, null=True)


class User(AbstractUser):
    username_validator = UsernameValidator
    username = models.CharField(
        'username',
        max_length=50,
        unique=True,
        help_text='Required. 50 characters or fewer, start with a letter. '
                  'Letters, digits and ./-/_ only.',
        validators=[username_validator],
        error_messages={'unique': 'A user with that username already exists.'},
        blank=True,
        null=True
    )
    country = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    REQUIRED_FIELDS = []

    class Meta(AbstractUser.Meta):
        swappable = 'AUTH_USER_MODEL'


class Offer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    industry = models.ForeignKey(
        Industry, on_delete=models.CASCADE, blank=True, null=True
    )
    skill_description = models.CharField(max_length=100, blank=True)


class History(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    accessed_offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    date_created = models.DateTimeField('date_created', auto_now_add=True)
    date_accessed = models.DateTimeField('date_accessed', default=timezone.now)
