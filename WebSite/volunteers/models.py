from django.conf import settings
from django.db import models
from django.utils.functional import cached_property

from core.models import TimeStampedModel, Festival, User
from core.utils import get_image_filename
from program.models import Venue


class Role(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.DELETE, related_name='roles')
    description = models.TextField(blank = True, default = '')

    class Meta:
        unique_together = ('festival', 'description')
        ordering = ('festival', 'description')

    def __str__(self):
        return f'{self.description}'

    
class Volunteer(TimeStampedModel):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='volunteer')
    roles = models.ManyToManyField(Skill, related_name = 'volunteers', blank = True)


class Shift(TimeStampedModel):

    venue = models.ForeignKey(Venue, on_delete=models.DELETE, related_name='shifts')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='shifts')
    volunteer = models.ForeignKey(Volunteer, null=True, blank=True, on_delete=models.PROTECT, related_name='shifts')

    class Meta:
        unique_together = ('venue', 'date', 'start_time', 'role')
        ordering = ('venue', 'date', 'start_time', 'role')

    def __str__(self):
        return f'{self.venue} {self.start_time} to {self.end_time} ({self.role})'
