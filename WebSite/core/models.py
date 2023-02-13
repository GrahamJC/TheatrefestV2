from uuid import uuid4
from datetime import date

from django.core.mail import send_mail
from django.utils.functional import cached_property
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.sites.models import Site
from django.db import models

from .utils import get_image_filename

class TimeStampedModel(models.Model):

    """
    Abstract base class that provides a UUID and self-updating 'created' and 'updated' fields.
    """

    class Meta:
        abstract = True

    uuid = models.UUIDField(unique=True, default=uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Festival(TimeStampedModel):

    name = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=64)
    banner = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    venue_map = models.ImageField(upload_to = get_image_filename, blank = True, default = '')
    online_sales_open = models.DateField(null=True, blank=True)
    online_sales_close = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    button_price = models.DecimalField(max_digits = 4, decimal_places = 2, blank = True, default = 0)
    fringer_price = models.DecimalField(max_digits = 4, decimal_places = 2, blank = True, default = 0)
    fringer_shows = models.PositiveIntegerField(blank = True, default = 0)
    volunteer_comps = models.PositiveIntegerField(blank = True, default = 0)
    boxoffice_open = models.DateField(null=True, blank=True)
    boxoffice_close = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def volunteers(self):
        return self.users.filter(is_volunteer = True).order_by('last_name')

    @property
    def is_online_sales_open(self):
        return (self.online_sales_open != None) and (self.online_sales_open <= date.today())

    @property
    def is_online_sales_closed(self):
        return (self.online_sales_close != None) and (self.online_sales_close < date.today())

    @cached_property
    def stylesheet(self):
        from content.models import Resource
        return Resource.objects.filter(festival=self, name='Stylesheet').first()

    @cached_property
    def banner(self):
        from content.models import Image
        return Image.objects.filter(festival=self, name='Banner').first()

    @cached_property
    def banner_mobile(self):
        from content.models import Image
        return Image.objects.filter(festival=self, name='BannerMobile').first()

    @cached_property
    def privacy_policy(self):
        from content.models import Document
        return Document.objects.filter(festival=self, name='PrivacyPolicy').first()


class SiteInfo(TimeStampedModel):

    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name='info')
    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='festival')
    stylesheet = models.CharField(max_length=64, blank = True, default = '')
    banner = models.CharField(max_length=64, blank = True, default = '')
    navigator = models.CharField(max_length=64, blank = True, default = '')
    header = models.CharField(max_length=64, blank = True, default = '')
    footer = models.CharField(max_length=64, blank = True, default = '')


class UserManager(BaseUserManager):

    def _create_user(self, site, festival, email, password, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(site=site, festival=festival, email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_user(self, site, festival, email, password, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_admin', False)
        return self._create_user(site, festival, email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        return self._create_user(None, None, email, password, **extra_fields)

    def get_by_natural_key(self, site, festival, email):
        return self.get(site=site, festival=festival, email=email)


class User(TimeStampedModel, AbstractBaseUser, PermissionsMixin):

    site = models.ForeignKey(Site, null=True, blank=True, on_delete=models.PROTECT, related_name='users')
    festival = models.ForeignKey(Festival, null=True, blank=True, on_delete=models.PROTECT, related_name='users')
    email = models.EmailField(max_length=64)
    first_name = models.CharField(blank=True, default='', max_length=30)
    last_name = models.CharField(blank=True, default='', max_length=30)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_boxoffice = models.BooleanField(default=False)
    is_venue = models.BooleanField(default=False)
    is_volunteer = models.BooleanField(default=False)

    class Meta:
        #ordering = ('site', 'festival', 'email')
        unique_together = ('site', 'festival', 'email')

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FILEDS = []

    objects = UserManager()

    def __str__(self):
        return f'{self.festival.name}/{self.email}' if self.festival else self.email

    @property
    def username(self):
        return self.email

    @property
    def is_festival_admin(self):
        return self.is_admin

    @property
    def is_site_admin(self):
        return self.is_admin and not self.festival

    @property
    def is_system_admin(self):
        return self.is_admin and not self.site and not self.festival

    @property
    def is_staff(self):
        return self.is_system_admin

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'

    def get_short_name(self):
        return self.first_name

    def get_natural_key(self):
        return [self.site, self.festival, self.email]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email):
        send_mail(subject, message, from_email, [self.email])
