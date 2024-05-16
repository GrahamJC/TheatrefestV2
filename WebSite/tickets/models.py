from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.db import models
from decimal import Decimal, ROUND_05UP

from core.models import TimeStampedModel, Festival
from core.utils import AutoOneToOneField

from program.models import Company, Show, ShowPerformance, Venue

class BoxOffice(TimeStampedModel):
    
    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='boxoffices')
    name = models.CharField(max_length = 32)

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

class Sale(TimeStampedModel):

    TRANSACTION_TYPE_CASH = 1
    TRANSACTION_TYPE_STRIPE = 2
    TRANSACTION_TYPE_SQUAREUP = 3
    TRANSACTION_TYPE_CHOICES = (
        (TRANSACTION_TYPE_CASH, 'Cash'),
        (TRANSACTION_TYPE_STRIPE, 'Stripe'),
        (TRANSACTION_TYPE_SQUAREUP, 'SquareUp'),
    )

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='sales')
    boxoffice = models.ForeignKey(BoxOffice, null = True, blank = True, on_delete = models.PROTECT, related_name = 'sales')
    venue = models.ForeignKey(Venue, null = True, blank = True, on_delete = models.PROTECT, related_name = 'sales')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.PROTECT, related_name = 'sales')
    customer = models.CharField(max_length = 64, blank = True, default = '')
    buttons = models.IntegerField(blank = True, default = 0)
    donation = models.IntegerField(blank = True, default = 0)
    amount = models.DecimalField(blank = True, default = 0, max_digits = 5, decimal_places = 2)
    completed = models.DateTimeField(null = True, blank = True)
    cancelled = models.DateTimeField(null = True, blank = True)
    transaction_ID = models.CharField(max_length = 128, null = True, blank = True)
    transaction_type = models.PositiveIntegerField(null = True, blank = True, choices = TRANSACTION_TYPE_CHOICES)
    transaction_fee = models.DecimalField(blank = True, default = 0, max_digits = 4, decimal_places = 2)
    notes = models.TextField(blank = True, default = '')

    @property
    def customer_user(self):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(festival = self.festival, email = self.customer)
        except user_model.DoesNotExist:
            user = None
        return user

    @property
    def is_customer_email(self):
        try:
            validate_email(self.customer)
        except ValidationError:
            return False
        return True

    @property
    def is_empty(self):
        return (self.buttons == 0) and (self.fringers.count() == 0) and (self.tickets.count() == 0)

    @property
    def button_cost(self):
        return self.buttons * self.festival.button_price

    @property
    def fringer_cost(self):
        return sum([f.price for f in self.fringers.all()])

    @property
    def ticket_cost(self):
        return sum([t.price for t in self.tickets.all()])

    @property
    def payw_cost(self):
        return sum([p.amount for p in self.PAYW_donations.all()])

    @property
    def total_cost(self):
        return self.button_cost + self.fringer_cost + self.ticket_cost + self.payw_cost + self.donation

    @property
    def total_cost_pence(self):
        return int(self.total_cost * 100)

    @property
    def is_complete(self):
        return self.completed != None

    @property
    def is_cancelled(self):
        return self.cancelled != None
    
    @property
    def is_in_progress(self):
        return not self.is_complete and not self.is_cancelled and self.transaction_type == None
    
    @property
    def is_payment_pending(self):
        return not self.is_complete and not self.is_cancelled and self.transaction_type != None

    @property
    def is_cash(self):
        return self.transaction_type == Sale.TRANSACTION_TYPE_CASH

    @property
    def is_stripe(self):
        return self.transaction_type == Sale.TRANSACTION_TYPE_STRIPE

    @property
    def is_square(self):
        return self.transaction_type == Sale.TRANSACTION_TYPE_SQUAREUP
    
    @property
    def ticket_performances(self):
        performances = []
        for ticket in self.tickets.values('performance_id').distinct():
            p = ShowPerformance.objects.get(pk = ticket['performance_id'])
            tickets = self.tickets.filter(performance_id = ticket['performance_id'])
            performance = {
                'id': p.id,
                'uuid': p.uuid,
                'show': p.show.name,
                'date' : p.date,
                'time': p.time,
                'ticket_cost': sum(t.price for t in tickets.all()), 
                'tickets': [{'id': t.id, 'uuid': t.uuid, 'description': f"{t.description}: {t.fringer.name}" if t.fringer else t.description, 'cost': t.price} for t in tickets],
            }
            performances.append(performance)
        return performances

    def transaction_type_description(self):
        if self.transaction_type == self.TRANSACTION_TYPE_CASH:
            return 'Cash'
        elif self.transaction_type == self.TRANSACTION_TYPE_STRIPE:
            return 'Stripe'
        elif self.transaction_type == self.TRANSACTION_TYPE_SQUAREUP:
            return 'Square'
        else:
            return 'Unknown'
        
    def __str__(self):
        return f'{self.id} ({self.customer})'


class Refund(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='refunds')
    boxoffice = models.ForeignKey(BoxOffice, null = True, blank = True, on_delete = models.PROTECT, related_name = 'refunds')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.PROTECT, related_name = 'refunds')
    customer = models.CharField(max_length = 64, blank = True, default = '')
    amount = models.DecimalField(blank = True, default = 0, max_digits = 5, decimal_places = 2)
    reason = models.TextField()
    completed = models.DateTimeField(null = True, blank = True)

    @property
    def customer_user(self):
        user_model = get_user_model()
        try:
            user = user_model.objects.get(email = self.customer)
        except user_model.DoesNotExist:
            user = None
        return user

    @property
    def is_empty(self):
        return (self.tickets.count() == 0)

    @property
    def ticket_cost(self):
        return sum([t.price for t in self.tickets.all()])

    @property
    def total_cost(self):
        return self.ticket_cost

    @property
    def performances(self):
        performances = []
        for ticket in self.tickets.values('performance_id').distinct():
            p = ShowPerformance.objects.get(pk = ticket['performance_id'])
            tickets = self.tickets.filter(performance_id = ticket['performance_id'])
            performance = {
                'id': p.id,
                'uuid': p.uuid,
                'show': p.show.name,
                'date' : p.date,
                'time': p.time,
                'ticket_cost': sum(t.price for t in tickets.all()), 
                'tickets': [{'id': t.id, 'uuid': t.uuid, 'description': t.description, 'cost': t.price} for t in tickets],
            }
            performances.append(performance)
        return performances

    def __str__(self):
        return f'{self.id} ({self.customer})'


class Basket(TimeStampedModel):
    
    user = AutoOneToOneField(settings.AUTH_USER_MODEL, on_delete = models.CASCADE, primary_key = True, related_name = 'basket')
    buttons = models.IntegerField(blank = True, default = 0)

    @property
    def ticket_count(self):
        return self.tickets.count()

    @property
    def has_tickets(self):
        return self.ticket_count > 0

    @property
    def fringer_count(self):
        return self.fringers.count()

    @property
    def has_fringers(self):
        return self.fringer_count > 0

    @property
    def has_buttons(self):
        return self.buttons > 0

    @property
    def total_count(self):
        return self.ticket_count + self.fringer_count + self.buttons
    
    @property
    def is_empty(self):
        return self.total_count == 0

    @property
    def ticket_cost(self):
        return sum([t.price for t in self.tickets.all()])

    @property
    def fringer_cost(self):
        return sum([f.price for f in self.fringers.all()])

    @property
    def button_cost(self):
        return self.buttons * self.user.festival.button_price

    @property
    def total_cost(self):
        return self.ticket_cost + self.fringer_cost + self.button_cost

    @property
    def performances(self):
        performances = []
        for t in self.tickets.values('performance_id').distinct():
            p = ShowPerformance.objects.get(pk = t['performance_id'])
            tickets = self.tickets.filter(performance = p)
            performance = {
                'id': p.id,
                'uuid': p.uuid,
                'show': p.show.name,
                'date' : p.date,
                'time': p.time,
                'ticket_cost': sum(t.price for t in tickets), 
                'tickets': [{'id': t.id, 'uuid': t.uuid, 'description': t.description, 'cost': t.price} for t in tickets],
            }
            performances.append(performance)
        return performances

    def __str__(self):
        return f'{self.user}'


class TicketType(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='ticket_types')
    name = models.CharField(max_length = 32)
    seqno = models.IntegerField(default = 1)
    price = models.DecimalField(max_digits = 4, decimal_places = 2, blank = True, default = 0)
    is_online = models.BooleanField(default = False)
    is_boxoffice = models.BooleanField(default = False)
    is_venue = models.BooleanField(default = False)
    rules = models.TextField(blank = True, default = '')
    payment = models.DecimalField(max_digits = 4, decimal_places = 2, blank = True, default = 0)

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    @property
    def can_delete(self):
        return (self.tickets.count() == 0) and (self.fringer_types.count() == 0)

    def get_volunteer(festival):
        return TicketType.objects.get(festival_id=festival.id, name='Volunteer')

class FringerType(TimeStampedModel):

    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='fringer_types')
    name = models.CharField(max_length = 32)
    shows = models.PositiveIntegerField(blank = True, default = 0)
    price = models.DecimalField(max_digits = 4, decimal_places = 2, blank = True, default = 0)
    is_online = models.BooleanField(default = False)
    rules = models.TextField(blank = True, default = '')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='fringer_types')

    class Meta:
        unique_together = ('festival', 'name')
        ordering = ('festival', 'name')

    def __str__(self):
        return f'{self.festival.name}/{self.name}'

    def can_delete(self):
        return self.fringers.count() == 0
    
class Fringer(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.PROTECT, null = True, blank = True, related_name = 'fringers')
    type = models.ForeignKey(FringerType, on_delete = models.PROTECT, related_name = 'fringers')
    name = models.CharField(max_length = 32)
    basket = models.ForeignKey(Basket, on_delete = models.CASCADE, null = True, blank = True, related_name = 'fringers')
    sale = models.ForeignKey(Sale, on_delete = models.CASCADE, null = True, blank = True, related_name = 'fringers')

    class Meta:
        #ordering = ['user', 'name']
        unique_together = ('user', 'name')

    def __str__(self):
        if self.user:
            return f"eFringer ({self.id}, {self.user.email}/{self.name})"
        elif self.sale:
            return f"Paper ({self.id}, {self.sale.customer})"
        else:
            return f"Fringer({self.id})"

    @property
    def description(self):
        return self.type.name

    @property
    def price(self):
        return self.type.price

    @property
    def used(self):
        return self.tickets.filter(refund = None).count() + self.PAYW_donations.count()

    @property
    def available(self):
        return self.type.shows - self.used

    @property
    def valid_tickets(self):
        return self.tickets.exclude(refund__isnull = False)

    def is_available(self, performance = None):
        return (self.available > 0) and ((performance == None) or (performance not in [t.performance for t in self.tickets.filter(refund__isnull = True)]))

    @staticmethod
    def get_available(user, performance = None):
        return [f for f in user.fringers.exclude(sale__completed__isnull = True) if f.is_available(performance)]
    
class Ticket(TimeStampedModel):

    performance = models.ForeignKey(ShowPerformance, on_delete = models.PROTECT, related_name = 'tickets')
    type = models.ForeignKey(TicketType, on_delete = models.PROTECT, related_name = 'tickets', null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, on_delete = models.PROTECT, related_name = 'tickets')
    basket = models.ForeignKey(Basket, on_delete = models.CASCADE, null = True, blank = True, related_name = 'tickets')
    fringer = models.ForeignKey(Fringer, on_delete = models.PROTECT, null = True, blank = True, related_name = 'tickets')
    sale = models.ForeignKey(Sale, on_delete = models.CASCADE, null = True, blank = True, related_name = 'tickets')
    refund = models.ForeignKey(Refund, on_delete = models.SET_NULL, null = True, blank = True, related_name = 'tickets')
    token_issued = models.BooleanField(default = False)

    #class Meta:
    #    ordering = ['performance']

    #def __str__(self):
    #    return f'{self.id} ({self.description}): {self.performance}'

    @property
    def is_confirmed(self):
        return (self.basket == None) and (self.refund == None)

    @property
    def is_cancelled(self):
        return (self.refund != None)

    @property
    def description(self):
        return self.type.name

    @property
    def price(self):
        return self.type.price

class Checkpoint(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, null = True, on_delete = models.PROTECT, related_name = 'checkpoints')
    boxoffice = models.ForeignKey(BoxOffice, null = True, blank = True, on_delete = models.PROTECT, related_name = 'checkpoints')
    venue = models.ForeignKey(Venue, null = True, blank = True, on_delete = models.PROTECT, related_name = 'checkpoints')
    open_performance = models.OneToOneField(ShowPerformance, null = True, blank = True, on_delete = models.PROTECT, related_name = 'open_checkpoint')
    close_performance = models.OneToOneField(ShowPerformance, null = True, blank = True, on_delete = models.PROTECT, related_name = 'close_checkpoint')
    cash = models.DecimalField(max_digits = 5, decimal_places = 2)
    buttons = models.IntegerField()
    fringers = models.IntegerField()
    notes = models.TextField(blank = True, default = '')

    def __str__(self):
        if self.boxoffice:
            return f'{self.boxoffice}/{self.id}/{self.created}'
        else:
            return f'{self.venue}/{self.id}/{self.created}'

class Donation(TimeStampedModel):
    
    festival = models.ForeignKey(Festival, on_delete=models.PROTECT, related_name='donations')
    email = models.CharField(max_length = 64)
    amount = models.DecimalField(max_digits = 5, decimal_places = 2)

    class Meta:
        ordering = ('festival', 'created')

    def __str__(self):
        return f'{self.festival}/{self.email}/£{self.amount}'


class PayAsYouWill(TimeStampedModel):

    sale = models.ForeignKey(Sale, on_delete = models.CASCADE, null = True, blank = True, related_name = 'PAYW_donations')
    show = models.ForeignKey(Show, on_delete = models.PROTECT, related_name = 'PAYW_donations')
    fringer = models.ForeignKey(Fringer, on_delete = models.PROTECT, null = True, blank = True, related_name = 'PAYW_donations')
    amount = models.IntegerField()


class Bucket(TimeStampedModel):

    date = models.DateField()
    company = models.ForeignKey(Company, on_delete = models.PROTECT, related_name = 'buckets')
    show = models.ForeignKey(Show, on_delete = models.PROTECT, null = True, blank = True, related_name = 'buckets')
    performance = models.ForeignKey(ShowPerformance, on_delete = models.PROTECT, null = True, blank = True, related_name = 'buckets')
    description = models.CharField(blank=True, default='', max_length = 32)
    cash = models.DecimalField(max_digits = 5, decimal_places = 2)
    fringers = models.IntegerField()

    @property
    def can_delete(self):
        return True


class BadgesIssued(TimeStampedModel):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete = models.PROTECT, related_name = 'badges_issued')
    boxoffice = models.ForeignKey(BoxOffice, null = True, blank = True, on_delete = models.PROTECT, related_name = 'badges_issued')
    venue = models.ForeignKey(Venue, null = True, blank = True, on_delete = models.PROTECT, related_name = 'badges_issued')
    badges = models.IntegerField()
