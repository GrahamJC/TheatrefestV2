from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from core.models import TimeStampedModel, Festival
from core.utils import get_image_filename

class Company(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='companies')
    name = models.CharField(max_length = 64)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    listing = models.TextField(blank = True, default = '')
    listing_short = models.TextField(blank = True, default = '')
    detail = models.TextField(blank = True, default = '')
    address1 = models.CharField(max_length = 64, blank = True, default = '')
    address2 = models.CharField(max_length = 64, blank = True, default = '')
    city = models.CharField(max_length = 32, blank = True, default = '')
    post_code = models.CharField(max_length = 10, blank = True, default = '')
    telno = models.CharField(max_length = 32, blank = True, default = '')
    email = models.EmailField(max_length = 128, blank = True, default = '')
    website = models.URLField(max_length = 128, blank = True, default = '')
    facebook = models.CharField(max_length = 64, blank = True, default = '')
    twitter = models.CharField(max_length = 64, blank = True, default = '')
    instagram = models.CharField(max_length = 64, blank = True, default = '')

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}' if self.festival else self.name

    @property
    def can_delete(self):
        return self.shows.count() == 0

class CompanyContact(TimeStampedModel):

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length = 64)
    role = models.CharField(max_length = 64, blank = True, default = '')
    address1 = models.CharField(max_length = 64, blank = True, default = '')
    address2 = models.CharField(max_length = 64, blank = True, default = '')
    city = models.CharField(max_length = 32, blank = True, default = '')
    post_code = models.CharField(max_length = 10, blank = True, default = '')
    telno = models.CharField(max_length = 32, blank = True, default = '')
    mobile = models.CharField(max_length = 32, blank = True, default = '')
    email = models.EmailField(max_length = 64, blank = True, default = '')

    class Meta:
        unique_together = ('company', 'name')
        ordering = ('company', 'name')

    def __str__(self):
        return f"{self.company}/{self.name}"

    @property
    def can_delete(self):
        return True


class Venue(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='venues')
    name = models.CharField(max_length = 64)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    listing = models.TextField(blank = True, default = '')
    listing_short = models.TextField(blank = True, default = '')
    detail = models.TextField(blank = True, default = '')
    address1 = models.CharField(max_length = 64, blank = True, default = '')
    address2 = models.CharField(max_length = 64, blank = True, default = '')
    city = models.CharField(max_length = 32, blank = True, default = '')
    post_code = models.CharField(max_length = 10, blank = True, default = '')
    telno = models.CharField(max_length = 32, blank = True, default = '')
    email = models.EmailField(max_length = 128, blank = True, default = '')
    website = models.URLField(max_length = 128, blank = True, default = '')
    facebook = models.CharField(max_length = 64, blank = True, default = '')
    twitter = models.CharField(max_length = 64, blank = True, default = '')
    instagram = models.CharField(max_length = 64, blank = True, default = '')
    is_ticketed = models.BooleanField(default = False)
    is_scheduled = models.BooleanField(default = False)
    is_searchable = models.BooleanField(default = False)
    capacity = models.IntegerField(null = True, blank = True)
    map_index = models.IntegerField(blank = True, default = 0)
    color = models.CharField(max_length = 16, blank = True, default = '')

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}' if self.festival else self.name

    @property
    def can_delete(self):
        return self.shows.count() == 0

    @property
    def sponsor(self):
        return self.sponsors.first()

    def get_first_performance(self, date = None):
        if date:
            return ShowPerformance.objects.filter(date = date, show__venue = self).order_by('time').first()
        else:
            return ShowPerformance.objects.filter(show__venue = self).order_by('date', 'time').first()

    def get_next_performance(self, date = None):
        if date:
            return ShowPerformance.objects.filter(date = date, show__venue = self, close_checkpoint = None).order_by('time').first()
        else:
            return ShowPerformance.objects.filter(show__venue = self, close_checkpoint = None).order_by('date', 'time').first()

    def get_last_performance(self, date = None):
        if date:
            return ShowPerformance.objects.filter(date = date, show__venue = self).order_by('time').first()
        else:
            return ShowPerformance.objects.filter(show__venue = self).order_by('date', 'time').first()


class VenueContact(TimeStampedModel):

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='contacts')
    name = models.CharField(max_length = 64)
    role = models.CharField(max_length = 64, blank = True, default = '')
    address1 = models.CharField(max_length = 64, blank = True, default = '')
    address2 = models.CharField(max_length = 64, blank = True, default = '')
    city = models.CharField(max_length = 32, blank = True, default = '')
    post_code = models.CharField(max_length = 10, blank = True, default = '')
    telno = models.CharField(max_length = 32, blank = True, default = '')
    mobile = models.CharField(max_length = 32, blank = True, default = '')
    email = models.EmailField(max_length = 64, blank = True, default = '')

    class Meta:
        unique_together = ('venue', 'name')
        ordering = ('venue', 'name')

    def __str__(self):
        return f'{self.venue}/{self.name}'

    @property
    def can_delete(self):
        return True

class VenueSponsor(TimeStampedModel):

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='sponsors')
    name = models.CharField(max_length = 64)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    contact = models.CharField(max_length = 64, blank = True, default = '')
    telno = models.CharField(max_length = 32, blank = True, default = '')
    email = models.EmailField(max_length = 64, blank = True, default = '')
    color = models.CharField(max_length = 16, blank = True, default = '')
    background = models.CharField(max_length = 16, blank = True, default = '')
    message = models.CharField(max_length = 32, blank = True, default = '')
    website = models.URLField(max_length = 128, blank = True, default = '')
    facebook = models.CharField(max_length = 64, blank = True, default = '')
    twitter = models.CharField(max_length = 64, blank = True, default = '')
    instagram = models.CharField(max_length = 64, blank = True, default = '')

    class Meta:
        unique_together = ('venue', 'name')
        ordering = ('venue', 'name')

    def __str__(self):
        return f'{self.venue}/{self.name}'

    @property
    def can_delete(self):
        return True


class Genre(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='genres')
    name = models.CharField(max_length = 32)

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}' if self.festival else self.name

    @property
    def can_delete(self):
        return self.shows.count() == 0


class Show(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='shows')
    name = models.CharField(max_length = 64)
    company = models.ForeignKey(Company, on_delete = models.PROTECT, related_name = 'shows')
    venue = models.ForeignKey(Venue, on_delete = models.PROTECT, related_name = 'shows')
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    listing = models.TextField(blank = True, default = '')
    listing_short = models.TextField(blank = True, default = '')
    detail = models.TextField(blank = True, default = '')
    website = models.URLField(max_length = 128, blank = True, default = '')
    facebook = models.CharField(max_length = 64, blank = True, default = '')
    twitter = models.CharField(max_length = 64, blank = True, default = '')
    instagram = models.CharField(max_length = 64, blank = True, default = '')
    genres = models.ManyToManyField(Genre, related_name = 'shows', blank = True)
    genre_text = models.CharField(max_length = 64, blank = True, default = '')
    has_warnings = models.BooleanField(blank = True, default = False)
    age_range = models.CharField(max_length = 16, blank = True, default = '')
    duration = models.PositiveIntegerField(null = True, blank = True)
    is_suspended = models.BooleanField(blank = True, default = False)
    is_cancelled = models.BooleanField(blank = True, default = False)
    replaced_by = models.OneToOneField('self', on_delete = models.SET_NULL, related_name = 'replacement_for', blank = True, null = True)

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}' if self.festival else self.name

    @property
    def can_delete(self):
        return True

    @property
    def is_ticketed(self):
        return self.venue.is_ticketed

    @property
    def is_online_tickets_open(self):
        return (
            self.venue.is_ticketed
            and not (self.is_suspended or self.is_cancelled)
            and self.festival.is_online_tickets_open
        )

    @cached_property
    def genre_list(self):
        return self.genre_text or ", ".join([genre.name for genre in self.genres.all()])

    @cached_property
    def performance_dates(self):
        dates = [p.date for p in self.performances.all()]
        dates = list(set(dates))
        dates.sort()
        return dates


class ShowImage(TimeStampedModel):

    show = models.ForeignKey(Show, on_delete = models.CASCADE, related_name = 'images')
    name = models.CharField(max_length = 32)
    image = models.ImageField(upload_to = get_image_filename, blank = True, default = '')

    class Meta:
        unique_together = ('show', 'name')
        ordering = ('show', 'name')

    def __str__(self):
        return f'{self.show}/{self.name}'

    @property
    def can_delete(self):
        return True


class ShowPerformance(TimeStampedModel):

    show = models.ForeignKey(Show, on_delete = models.CASCADE, related_name = 'performances')
    date = models.DateField()
    time = models.TimeField()
    audience = models.IntegerField(blank = True, default = 0)
    notes = models.TextField(blank = True, default = '')

    class Meta:
        unique_together = ('show', 'date', 'time')
        ordering = ('show', 'date', 'time')

    def __str__(self):
        return f'{self.show}/{self.date} at {self.time}'

    @property
    def can_delete(self):
        return True

    @property
    def is_ticketed(self):
        return self.show.is_ticketed

    @property
    def is_cancelled(self):
        return self.show.is_cancelled

    @property
    def is_suspended(self):
        return self.show.is_suspended

    @property
    def tickets_sold(self):
        return self.tickets.filter(basket__isnull = True).count()

    @property
    def tickets_refunded(self):
        return self.tickets.filter(refund__isnull = False).count()

    @property
    def tickets_available(self):
        available = self.show.venue.capacity - self.tickets_sold + self.tickets_refunded if self.show.venue.capacity else 0
        return available if available > 0 else 0

    @property
    def has_open_checkpoint(self):
        return hasattr(self, 'open_checkpoint')

    @property
    def has_close_checkpoint(self):
        return hasattr(self, 'close_checkpoint')


class ShowReview(TimeStampedModel):

    RATING_1STAR = 1
    RATING_2STAR = 2
    RATING_3STAR = 3
    RATING_4STAR = 4
    RATING_5STAR = 5
    RATING_CHOICES = (
        (RATING_1STAR, '*'),
        (RATING_2STAR, '**'),
        (RATING_3STAR, '***'),
        (RATING_4STAR, '****'),
        (RATING_5STAR, '*****'),
    )

    show = models.ForeignKey(Show, on_delete = models.CASCADE, related_name = 'reviews')
    source = models.CharField(max_length = 128)
    rating = models.PositiveIntegerField(null = True, blank = True, choices = RATING_CHOICES)
    body = models.TextField(blank = True, default = '')
    url = models.URLField(max_length = 128, blank = True, default = '')

    class Meta:
        ordering = ('show', 'source')

    def __str__(self):
        return f'{self.show}/{self.source}'

    @property
    def can_delete(self):
        return True
