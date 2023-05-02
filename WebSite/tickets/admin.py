from django.contrib import admin

from .models import BoxOffice, Basket, FringerType, Fringer, TicketType, Ticket, Sale, Refund, Donation, Checkpoint
from core.models import Festival
from program.models import Venue

admin.site.register(BoxOffice)
admin.site.register(Basket)
admin.site.register(FringerType)
#admin.site.register(Fringer)
admin.site.register(TicketType)
admin.site.register(Ticket)
#admin.site.register(Sale)
admin.site.register(Refund)
admin.site.register(Donation)
admin.site.register(Checkpoint)


@admin.register(Fringer)
class FringerAdmin(admin.ModelAdmin):

    model = Fringer
    
    list_display = ('id', '__str__')
#    list_filter = ('email',)

class SaleTypeListFilter(admin.SimpleListFilter):

    title = 'Type'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        result = [('OL', 'Online')]
        if request.festival:
            result.extend([(f'BO:boxoffice.id', f'BoxOffice: {boxoffice.name}') for boxoffice in BoxOffice.objects.filter(festival = request.festival).order_by('name')])
            result.extend([(f'V:{venue.id}', f'Venue: {venue.name}') for venue in Venue.objects.filter(festival = request.festival, is_ticketed = True).order_by('name')])
        else:
            result.extend([('BO', 'BoxOffice')])
            result.extend([('V', 'Venue')])
        return result

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == 'OL':
                return queryset.filter(boxoffice__isnull = True, venue__isnull = True)
            elif self.value() == 'BO':
                return queryset.filter(boxoffice__isnull = False)
            elif self.value() == 'V':
                return queryset.filter(venue__isnull = False)
            elif self.value().startswith('BO:'):
                return queryset.filter(boxoffice_id = self.value()[3:])
            elif self.value().startswith('V:'):
                return queryset.filter(venue_id = self.value()[2:])
        return queryset


class SaleTicketsInline(admin.TabularInline):

    model = Ticket
    fields = ['ticket_performance', 'description', 'cost']
    readonly_fields = ['ticket_performance']
    extra = 0
    show_change_link = True

    @admin.display(description = 'Performance')
    def ticket_performance(self, obj):
        return f'ID: {obj.id}'

    
class SaleFringersInline(admin.TabularInline):

    model = Fringer
    fields = ['name', 'description', 'shows', 'cost']
    extra = 0
    show_change_link = True


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):

    model = Sale
    date_hierarchy = 'created'
    search_fields = ['id', 'customer']
    fields = ['id', 'created', 'updated', 'user', 'boxoffice', 'venue', 'customer', 'buttons', 'amount', 'completed', 'cancelled', 'transaction_type', 'transaction_fee', 'stripe_pi']
    readonly_fields = ['id', 'created', 'updated']
    autocomplete_fields = ['user']
    list_display = ('id', 'customer', 'sale_type', 'amount', 'completed')
    list_filter = [SaleTypeListFilter]
    #inlines = [SaleTicketsInline, SaleFringersInline]
    inlines = [SaleTicketsInline]

    @admin.display(description = 'Type')
    def sale_type(self, obj):
        if obj.boxoffice:
            return f'BoxOffice: {obj.boxoffice.name}'
        elif obj.venue:
            return f'Venue: {obj.venue.name}'
        return 'Online'

    def get_queryset(self, request):
        # Limit to selected festival
        qs = super().get_queryset(request)
        return qs.filter(festival = request.festival)

    def get_changeform_initial_data(self, request):
        # Set selected festival
        return {
            'festival': request.festival,
        }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Restrict choices for box office and venue
        if db_field.name == 'boxoffice':
            kwargs['queryset'] = BoxOffice.objects.filter(festival = request.festival)
        if db_field.name == 'venue':
            kwargs['queryset'] = Venue.objects.filter(festival = request.festival, is_ticketed = True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
