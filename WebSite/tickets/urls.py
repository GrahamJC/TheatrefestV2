from django.urls import path

from . import views

app_name = "tickets"

urlpatterns = [
    path('myaccount', views.MyAccountView.as_view(), name = 'myaccount'),
    path('myaccount/confirm/fringers', views.MyAccountConfirmFringersView.as_view(), name = 'myaccount_confirm_fringers'),
    path('buy/<uuid:performance_uuid>', views.BuyView.as_view(), name = 'buy'),
    path('buy/<uuid:performance_uuid>/closed', views.BuyClosedView.as_view(), name = 'buy_closed'),
    path('buy/confirm/tickets/<uuid:performance_uuid>', views.BuyConfirmTicketsView.as_view(), name = 'buy_confirm_tickets'),
    path('buy/confirm/fringer_tickets/<uuid:performance_uuid>', views.BuyConfirmFringerTicketsView.as_view(), name = 'buy_confirm_fringer_tickets'),
    path('buy/confirm/fringers/<uuid:performance_uuid>', views.BuyConfirmFringersView.as_view(), name = 'buy_confirm_fringers'),
    path('buy/confirm/volunteer_ticket/<uuid:performance_uuid>', views.BuyConfirmVolunteerTicketView.as_view(), name = 'buy_confirm_volunteer_ticket'),
    path('payw/<uuid:show_uuid>', views.PAYWView.as_view(), name = 'payw'),
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
    path('ticket/<uuid:ticket_uuid>/cancel', views.ticket_cancel, name = 'ticket_cancel'),
    path('donations', views.donations, name = 'donations'),
    path('donation/stripe', views.donation_stripe, name = 'donation_stripe'),
    path('donation/success', views.donation_success, name = 'donation_success'),
    path('donation/cancel', views.donation_cancel, name = 'donation_cancel'),
    path('print/sale/<uuid:sale_uuid>', views.PrintSaleView.as_view(), name = 'print_sale'),
    path('print/performance/<uuid:performance_uuid>', views.PrintPerformanceView.as_view(), name = 'print_performance'),
]
