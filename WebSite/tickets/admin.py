from django.contrib import admin

from .models import BoxOffice, Basket, FringerType, Fringer, TicketType, Ticket, Sale, Refund, Donation

admin.site.register(BoxOffice)
admin.site.register(Basket)
admin.site.register(FringerType)
#admin.site.register(Fringer)
admin.site.register(TicketType)
admin.site.register(Ticket)
admin.site.register(Sale)
admin.site.register(Refund)
admin.site.register(Donation)


@admin.register(Fringer)
class FringerAdmin(admin.ModelAdmin):

    model = Fringer
    
    list_display = ('id', '__str__')
#    list_filter = ('email',)
