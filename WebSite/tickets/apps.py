from django.apps import AppConfig

class TicketsConfig(AppConfig):
    name = 'tickets'

    def ready(self):
        # Connect signals using @receiver
        from . import signals