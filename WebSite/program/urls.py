from django.urls import path

from . import views

app_name = "program"

urlpatterns = [
    path('shows', views.shows, name = 'shows'),
    path('shows/<uuid:festival_uuid>', views.shows, name = 'shows'),
    path('show/<uuid:show_uuid>', views.show, name = 'show'),
    path('schedule', views.schedule, name = 'schedule'),
    path('schedule/<uuid:festival_id>', views.schedule, name = 'schedule'),
    path('schedule/pdf', views.schedule_pdf, name = 'schedule_pdf'),
    path('schedule/<uuid:festival_uuid>/pdf', views.schedule_pdf, name = 'schedule_pdf'),
    path('venues', views.venues, name = 'venues'),
    path('venues/<uuid:festival_uuid>', views.venues, name = 'venues'),
    path('venue/<uuid:venue_uuid>', views.venue, name = 'venue'),
]

