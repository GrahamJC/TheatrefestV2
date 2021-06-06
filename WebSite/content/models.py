import os

from django.conf import settings
from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel, Festival
from core.utils import get_image_filename, get_document_filename


class Page(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=32)
    title = models.CharField(max_length=64, blank=True, default='')
    body = models.TextField(blank=True, default='')
    body_test = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('festival', 'name')
        unique_together = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return self.navigators.count() == 0

    def get_absolute_url(self):
        return reverse('content:page_name', args=[self.name.lower()])

    def get_test_url(self):
        return reverse('content:page_test', args=[self.uuid])

class PageImage(TimeStampedModel):

    page = models.ForeignKey(Page, on_delete = models.CASCADE, related_name = 'images')
    name = models.CharField(max_length = 32)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')

    class Meta:
        unique_together = ('page', 'name')
        ordering = ('page', 'name')

    def __str__(self):
        return f'{self.page}/{self.name}'

    def can_delete(self):
        return True

    def get_absolute_url(self):
        return os.path.join(getattr(settings, 'MEDIA_URL', '/media'), self.image.url)


class Navigator(TimeStampedModel):

    URL = 1
    PAGE = 2
    SHOWS = 3
    SCHEDULE = 4
    VENUES = 5
    ARCHIVE_INDEX = 6
    ARCHIVE_HOME = 7
    DONATIONS = 8
    TYPE_CHOICES = (
        (URL, 'URL'),
        (PAGE, 'Content page'),
        (SHOWS, 'List/Search shows'),
        (SCHEDULE, 'Schedule'),
        (VENUES, 'List venues'),
        (DONATIONS, 'Donations'),
        (ARCHIVE_INDEX, 'Archive index'),
        (ARCHIVE_HOME, 'Archive home'),
    )

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='navigators')
    seqno = models.PositiveIntegerField(blank=True, default=0)
    label = models.CharField(max_length=32)
    type = models.IntegerField(choices=TYPE_CHOICES)
    url = models.URLField(max_length=256, blank=True, default='')
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.PROTECT, related_name='navigators')

    class Meta:
        ordering = ('festival', 'seqno', 'label')
        unique_together = ('festival', 'label')

    @property
    def href(self):
        if self.type == Navigator.URL and self.url:
            return self.url
        elif self.type == Navigator.PAGE and self.page:
            return self.page.get_absolute_url()
        elif self.type == Navigator.SHOWS:
            return reverse('program:shows')
        elif self.type == Navigator.SCHEDULE:
            return reverse('program:schedule')
        elif self.type == Navigator.VENUES:
            return reverse('program:venues')
        elif self.type == Navigator.DONATIONS:
            return reverse('tickets:donations')
        elif self.type == Navigator.ARCHIVE_INDEX:
            return reverse('festival:archive_index')
        elif self.type == Navigator.ARCHIVE_HOME:
            return reverse('festival:archive_home')
        else:
            return '#'

    def __str__(self):
        return f'{self.festival.name}/{self.label}'

    def can_delete(self):
        return True


class Image(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='images')
    name = models.CharField(max_length=32)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')

    class Meta:
        ordering = ('festival', 'name')
        unique_together = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return True

    def get_absolute_path(self):
        return self.image.path

    def get_absolute_url(self):
        return os.path.join(getattr(settings, 'MEDIA_URL', '/media'), self.image.url)


class Document(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(max_length=32)
    file = models.FileField(upload_to = get_document_filename, blank = True, default = '')
    filename = models.CharField(max_length=64, blank = True, default = '')

    class Meta:
        ordering = ('festival', 'name')
        unique_together = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return True

    def get_absolute_url(self):
        return reverse('content:document', args=[self.uuid])


class Resource(TimeStampedModel):

    CSS = 'text/css'
    JAVASCRIPT = 'application/javascript'
    TYPE_CHOICES = (
        (CSS, 'CSS stylesheet'),
        (JAVASCRIPT, 'Javascript'),
    )
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='resources')
    name = models.CharField(max_length=32)
    type = models.CharField(max_length=64, choices=TYPE_CHOICES)
    body = models.TextField(blank=True, default='')
    body_test = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('festival', 'name')
        unique_together = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return True

    def get_absolute_url(self):
        return reverse('content:resource', args=[self.uuid])

    def get_test_url(self):
        return reverse('content:resource_test', args=[self.uuid])
