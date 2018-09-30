from django.db import models
from django.urls import reverse

from core.models import TimeStampedModel, Festival
from core.utils import get_image_filename


class ContentPage(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='content_pages')
    name = models.CharField(max_length=32)
    title = models.CharField(max_length=64, blank=True, default='')
    body = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('festival', 'name')
        unique_together = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return self.navigator_options.count() == 0


class ContentPageImage(TimeStampedModel):

    page = models.ForeignKey(ContentPage, on_delete = models.CASCADE, related_name = 'images')
    name = models.CharField(max_length = 32)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')

    class Meta:
        unique_together = ('page', 'name')
        ordering = ('page', 'name')

    def __str__(self):
        return f'{self.page}/{self.name}'


class NavigatorOption(TimeStampedModel):

    URL = 1
    PAGE = 2
    SHOWS = 3
    SCHEDULE = 4
    VENUES = 5
    TYPE_CHOICES = (
        (URL, 'URL'),
        (PAGE, 'Content page'),
        (SHOWS, 'List/search shows'),
        (SCHEDULE, 'Schedule'),
        (VENUES, 'List venues'),
    )

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='navigator_options')
    seqno = models.PositiveIntegerField(blank=True, default=0)
    label = models.CharField(max_length=32)
    type = models.IntegerField(choices=TYPE_CHOICES)
    url = models.URLField(max_length=32, blank=True, default='')
    page = models.ForeignKey(ContentPage, null=True, blank=True, on_delete=models.PROTECT, related_name='navigator_options')

    class Meta:
        ordering = ('festival', 'seqno', 'label')
        unique_together = ('festival', 'label')

    @property
    def href(self):
        if self.type == NavigatorOption.URL and self.url:
            return self.utl
        elif self.type == NavigatorOption.PAGE and self.page:
            return reverse('festival:page', kwargs={'page_uuid': self.page.uuid})
        elif self.type == NavigatorOption.SHOWS:
            return reverse('program:shows')
        elif self.type == NavigatorOption.SCHEDULE:
            return reverse('program:schedule')
        elif self.type == NavigatorOption.VENUES:
            return reverse('program:venues')
        else:
            return '#'

    def __str__(self):
        return f'{self.festival.name}/{self.label}'

    def can_delete(self):
        return true
