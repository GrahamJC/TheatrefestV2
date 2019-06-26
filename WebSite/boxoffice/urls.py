from django.urls import path

from . import views

app_name = "boxoffice"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:boxoffice_uuid>', views.main, name = 'main'),
    path('<uuid:boxoffice_uuid>/tab/<str:tab>', views.main, name = 'main_tab'),
    # Sales
    path('<uuid:boxoffice_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/select', views.sale_show_select, name = 'sale_show_select'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/select', views.sale_performance_select, name = 'sale_performance_select'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/tickets/add', views.sale_tickets_add, name = 'sale_tickets_add'),
    path('sale/<uuid:sale_uuid>/extras/update', views.sale_extras_update, name = 'sale_extras_update'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/remove', views.sale_remove_performance, name = 'sale_remove_performance'),
    path('sale/<uuid:sale_uuid>/ticket/<uuid:ticket_uuid>/remove', views.sale_remove_ticket, name = 'sale_remove_ticket'),
    path('sale/<uuid:sale_uuid>/complete', views.sale_complete, name = 'sale_complete'),
    path('sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    path('sale/<uuid:sale_uuid>/close', views.sale_close, name = 'sale_close'),
    path('sale/<uuid:sale_uuid>/select', views.sale_select, name = 'sale_select'),
    path('sale/<uuid:sale_uuid>/email', views.sale_email, name = 'sale_email'),
    # Checkpoints
    path('<uuid:boxoffice_uuid>/checkpoint/add', views.checkpoint_add, name = 'checkpoint_add'),
    path('checkpoint/<uuid:checkpoint_uuid>/select', views.checkpoint_select, name = 'checkpoint_select'),
    path('checkpoint/<uuid:checkpoint_uuid>/update', views.checkpoint_update, name = 'checkpoint_update'),
    path('checkpoint/<uuid:checkpoint_uuid>/cancel', views.checkpoint_cancel, name = 'checkpoint_cancel'),
    # Shows
    # Users
    path('user/autocomplete', views.UserAutoComplete.as_view(), name='user_autocomplete'),
    path('<uuid:boxoffice_uuid>/user/lookup', views.user_lookup, name = 'user_lookup'),
]
