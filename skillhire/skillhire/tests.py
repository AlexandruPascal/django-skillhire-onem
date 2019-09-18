from django.test import TestCase
from skillhire.models import Industry


class IndustryTestCase(TestCase):
    fixtures = ['industry.json']
