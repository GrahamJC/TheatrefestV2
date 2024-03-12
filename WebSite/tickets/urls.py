from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path('myaccount', views.myaccount, name = 'myaccount'),
    path('myaccount/ticket/<uuid:ticket_uuid>/cancel', views.myaccount_ticket_cancel, name = 'myaccount_ticket_cancel'),
    path('myaccount/fringers/rename', views.myaccount_fringers_rename, name = 'myaccount_fringers_rename'),
    path('myaccount/fringers/buy', views.myaccount_fringers_buy, name = 'myaccount_fringers_buy'),
    path('myaccount/fringers/confirm', views.myaccount_fringers_confirm, name = 'myaccount_fringers_confirm'),
    path('buy/<uuid:performance_uuid>', views.buy, name = 'buy'),
    path('buy/<uuid:performance_uuid>/closed', views.buy_closed, name = 'buy_closed'),
    path('buy/<uuid:performance_uuid>/tickets/add', views.buy_tickets_add, name = 'buy_tickets_add'),
    path('buy/<uuid:performance_uuid>/tickets/add/confirm', views.buy_tickets_add_confirm, name = 'buy_tickets_add_confirm'),
    path('buy/<uuid:performance_uuid>/fringers/use', views.buy_fringers_use, name = 'buy_fringers_use'),
    path('buy/<uuid:performance_uuid>/fringers/use/confirm', views.buy_fringers_use_confirm, name = 'buy_fringers_use_confirm'),
    path('buy/<uuid:performance_uuid>/fringers/add', views.buy_fringers_add, name = 'buy_fringers_add'),
    path('buy/<uuid:performance_uuid>/fringers/add/confirm', views.buy_fringers_add_confirm, name = 'buy_fringers_add_confirm'),
    path('buy/<uuid:performance_uuid>/volunteer/use', views.buy_volunteer_use, name = 'buy_volunteer_use'),
    path('buy/<uuid:performance_uuid>/volunteer/use/confirm', views.buy_volunteer_use_confirm, name = 'buy_volunteer_use_confirm'),
    path('payw/<uuid:show_uuid>', views.payw, name = 'payw'),
    path('payw/<uuid:show_uuid>/donate', views.payw_donate, name = 'payw_donate'),
    path('checkout', views.checkout, name = 'checkout'),
    path('checkout/buttons/add', views.checkout_buttons_add, name = 'checkout_buttons_add'),
    path('checkout/buttons/none', views.checkout_buttons_none, name = 'checkout_buttons_none'),
    path('checkout/buttons/update', views.checkout_buttons_update, name = 'checkout_buttons_update'),
    path('checkout/performance/<uuid:performance_uuid>/remove', views.checkout_performance_remove, name = 'checkout_performance_remove'),
    path('checkout/ticket/<uuid:ticket_uuid>/remove', views.checkout_ticket_remove, name = 'checkout_ticket_remove'),
    path('checkout/fringer/<uuid:fringer_uuid>/remove', views.checkout_fringer_remove, name = 'checkout_fringer_remove'),
    path('checkout/stripe', views.checkout_stripe, name = 'checkout_stripe'),
    path('checkout/success/<uuid:sale_uuid>', views.checkout_success, name = 'checkout_success'),
    path('checkout/cancel/<uuid:sale_uuid>', views.checkout_cancel, name = 'checkout_cancel'),
    path('donations', views.donations, name = 'donations'),
    path('donation/stripe', views.donation_stripe, name = 'donation_stripe'),
    path('donation/success', views.donation_success, name = 'donation_success'),
    path('donation/cancel', views.donation_cancel, name = 'donation_cancel'),
    path('print/sale/<uuid:sale_uuid>', views.print_sale, name = 'print_sale'),
    path('print/performance/<uuid:performance_uuid>', views.print_performance, name = 'print_performance'),
]
