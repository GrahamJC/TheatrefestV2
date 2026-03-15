from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from core.models import TimeStampedModel, Festival, User
from core.utils import get_image_filename

from program.models import Venue
from tickets.models import TicketType

class Role(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='roles')
    description = models.CharField(blank = True, max_length=32, default = '')
    comps_per_shift = models.FloatField(blank = False, default = 0)
    information = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('festival', 'description')
        ordering = ('festival', 'description')

    def __str__(self):
        return f'{self.description}'

    def can_delete(self):
        return (self.users.count() + self.shifts.count()) == 0


class Location(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='locations')
    description = models.CharField(blank = True, max_length=32, default = '')
    information = models.TextField(blank=True, default='')

    class Meta:
        unique_together = ('festival', 'description')
        ordering = ('festival', 'description')

    def __str__(self):
        return f'{self.description}'

    def can_delete(self):
        return self.shifts.count() == 0


class Commitment(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name='commitments')
    description = models.CharField(blank = True, max_length=32, default = '')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='commitments')
    needs_dbs = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='volunteer_commitments')
    volunteer_can_accept = models.BooleanField(blank = True, default = True)
    notes = models.TextField(blank = True, default = '')

    class Meta:
        unique_together = ('festival', 'description')
        ordering = ('festival', 'description')

    def __str__(self):
        return self.description

    def can_delete(self):
        return not self.user

    def update_shifts(self):
        for shift in self.shifts.all():
            shift.role = self.role
            shift.needs_dbs = self.needs_dbs
            shift.volunteer_can_accept = self.volunteer_can_accept
            shift.user = self.user
            shift.save()


class Shift(TimeStampedModel):

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='shifts')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    commitment = models.ForeignKey(Commitment, null=True, blank=True, on_delete=models.CASCADE, related_name='shifts')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='shifts')
    needs_dbs = models.BooleanField(default=False)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name='volunteer_shifts')
    volunteer_can_accept = models.BooleanField(blank = True, default = True)
    notes = models.TextField(blank = True, default = '')

    class Meta:
        unique_together = ('location', 'date', 'start_time', 'role')
        ordering = ('location', 'date', 'start_time', 'role')

    def __str__(self):
        return f'{self.location} {self.date}  {self.start_time} to {self.end_time} ({self.role})'

    def can_delete(self):
        return not self.user
