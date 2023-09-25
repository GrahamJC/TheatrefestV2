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
        return (self.volunteers.count() + self.shifts.count()) == 0


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

    
class Volunteer(TimeStampedModel):

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='volunteer')
    roles = models.ManyToManyField(Role, related_name = 'volunteers', blank = True)
    is_dbs = models.BooleanField(default=False)

    @property
    def comps_earned(self):

        # Calculate comps earned (rounded down) and limit to a maximum of 4
        comps = 0
        for shift in self.shifts.all():
            comps += shift.role.comps_per_shift
        comps = int(comps)
        max_comps = self.user.festival.volunteer_comps
        return comps if max_comps == 0 else min(comps, max_comps)

    @property
    def comps_used(self):
        return self.user.tickets.filter(type=TicketType.get_volunteer(festival=self.user.festival), sale__completed__isnull = False).count()

    @property
    def comps_available(self):
        return self.comps_earned - self.comps_used

    def __str__(self):
        return f'{self.user.get_full_name()}'

    def can_remove(self):
        return self.shifts.count() == 0


class Shift(TimeStampedModel):

    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='shifts')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='shifts')
    needs_dbs = models.BooleanField(default=False)
    volunteer = models.ForeignKey(Volunteer, null=True, blank=True, on_delete=models.PROTECT, related_name='shifts')
    volunteer_can_accept = models.BooleanField(blank = True, default = True)
    notes = models.TextField(blank = True, default = '')

    class Meta:
        unique_together = ('location', 'date', 'start_time', 'role')
        ordering = ('location', 'date', 'start_time', 'role')

    def __str__(self):
        return f'{self.location} {self.date}  {self.start_time} to {self.end_time} ({self.role})'

    def can_delete(self):
        return True
