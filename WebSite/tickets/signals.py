from datetime import timezone

from django.contrib.auth import user_logged_in, user_logged_out
from django.dispatch import receiver

# Logging
import logging
logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def user_logged_in_signal(sender, user, request, **kwargs):
    logger.info(f"User {user.email} logged on")

    # Delete any incomplete sales and return items to basket
    for sale in user.sales.filter(boxoffice__isnull = True, venue__isnull = True, completed__isnull = True):
        for ticket in sale.tickets.all():
            ticket.basket = user.basket
            ticket.sale = None
            ticket.save()
            logger.info(f"{ticket.description} ticket for {ticket.performance.show.name} on {ticket.performance.date} at {ticket.performance.time} returned to basket {user.id}")
        for fringer in sale.fringers.all():
            fringer.basket = user.basket
            fringer.sale = None
            fringer.save()
            logger.info(f"eFringer {fringer.name} returned to basket {user.id}")
        logger.info(f"Incomplete sale {sale.id} auto-cancelled")
        sale.cancelled = timezone.now()
        sale.save


@receiver(user_logged_out)
def user_logged_out_signal(sender, user, request, **kwargs):
    logger.info(f"User {user.email} logged out")
