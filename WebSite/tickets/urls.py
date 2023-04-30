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
    path('checkout', views.CheckoutView.as_view(), name = 'checkout'),
    path('checkout/remove/performance/<uuid:performance_uuid>', views.CheckoutRemovePerformanceView.as_view(), name = 'checkout_remove_performance'),
    path('checkout/remove/ticket/<uuid:ticket_uuid>', views.CheckoutRemoveTicketView.as_view(), name = 'checkout_remove_ticket'),
    path('checkout/remove/fringer/<uuid:fringer_uuid>', views.CheckoutRemoveFringerView.as_view(), name = 'checkout_remove_fringer'),
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
