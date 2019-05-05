import django
import datetime
from django.test import TestCase

django.setup()

from core.models import Festival

class FestivalTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        festival = Festival.objects.create(
            name = 'TestFestival',
            title = 'Test festival',
            online_sales_open = datetime.datetime(2019, 5, 1),
            online_sales_close = datetime.datetime(2019, 7, 4),
        )

    def test_festival_sales_open(self):
        festival = Festival.objects.get(name = 'TestFestival')
        self.assertTrue(festival.is_online_sales_open)
        self.assertFalse(festival.is_online_sales_closed)


class SiteInfoTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        festival = Festival.objects.create(
            name = 'TestFestival',
            title = 'Test festival',
            online_sales_open = datetime.datetime(2019, 5, 1),
            online_sales_close = datetime.datetime(2019, 7, 4),
        )

    def test_festival_sales_open(self):
        festival = Festival.objects.get(name = 'TestFestival')
        self.assertTrue(festival.is_online_sales_open)
        self.assertFalse(festival.is_online_sales_closed)
