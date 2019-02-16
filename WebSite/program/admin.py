from django.contrib import admin

from .models import Company, CompanyContact, Venue, VenueContact, VenueSponsor, Genre, Show, ShowImage, ShowPerformance, ShowReview
    
    
class CompanyContactInline(admin.StackedInline):
    
    model = CompanyContact
    extra = 0
    classes = ['collapse']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    
    model = Company
    fieldsets = [
        (None, {
            'fields': ('festival', 'name', 'image', 'listing', 'listing_short', 'detail'),
        }),
        ('Address', {
            'classes': ('collapse',),
            'fields': ('address1', 'address2', 'city', 'post_code'),
        }),
        ('Primary contact', {
            'classes': ('collapse',),
            'fields': ('telno', 'email'),
        }),
        ('Social media', {
            'classes': ('collapse',),
            'fields': ('website', 'facebook', 'twitter', 'instagram'),
        }),
    ]
    inlines = [
        CompanyContactInline,
    ]
    list_filter = ('festival',)
    list_max_show_all = 25
    
    
class VenueContactInline(admin.StackedInline):
    
    model = VenueContact
    extra = 0
    classes = ['collapse']
    
    
class VenueSponsorInline(admin.StackedInline):
    
    model = VenueSponsor
    extra = 0
    classes = ['collapse']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    
    model = Venue
    fieldsets = [
        (None, {
            'fields': ('festival', 'name', 'image', 'listing', 'listing_short', 'detail', 'is_ticketed', 'is_scheduled', 'is_searchable', 'capacity', 'map_index', 'color'),
        }),
        ('Address', {
            'classes': ('collapse',),
            'fields': ('address1', 'address2', 'city', 'post_code'),
        }),
        ('Primary contact', {
            'classes': ('collapse',),
            'fields': ('telno', 'email'),
        }),
        ('Social media', {
            'classes': ('collapse',),
            'fields': ('website', 'facebook', 'twitter', 'instagram'),
        }),
    ]
    inlines = [
        VenueContactInline,
        VenueSponsorInline,
    ]
    list_filter = ('festival',)
    list_max_show_all = 25
