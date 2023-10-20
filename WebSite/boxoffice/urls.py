from django.urls import path

from . import views

app_name = "boxoffice"

urlpatterns = [
    # Select
    path('select', views.select, name = 'select'),
    # Main page
    path('<uuid:boxoffice_uuid>', views.main, name = 'main'),
    path('<uuid:boxoffice_uuid>/tab/<str:tab>', views.main, name = 'main_tab'),
    path('<uuid:boxoffice_uuid>/sale/<uuid:sale_uuid>', views.main_sale, name = 'main_sale'),
    # Sales
    path('<uuid:boxoffice_uuid>/sale/start', views.sale_start, name = 'sale_start'),
    path('sale/<uuid:sale_uuid>/show/select', views.sale_show_select, name = 'sale_show_select'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/performance/select', views.sale_performance_select, name = 'sale_performance_select'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/tickets/add', views.sale_tickets_add, name = 'sale_tickets_add'),
    path('sale/<uuid:sale_uuid>/performance/<uuid:performance_uuid>/remove', views.sale_remove_performance, name = 'sale_remove_performance'),
    path('sale/<uuid:sale_uuid>/ticket/<uuid:ticket_uuid>/remove', views.sale_remove_ticket, name = 'sale_remove_ticket'),
    path('sale/<uuid:sale_uuid>/show/select_payw', views.sale_show_select_payw, name = 'sale_show_select_payw'),
    path('sale/<uuid:sale_uuid>/show/<uuid:show_uuid>/payw/add', views.sale_payw_add, name = 'sale_payw_add'),
    path('sale/<uuid:sale_uuid>/payw/<uuid:payw_uuid>/remove', views.sale_payw_remove, name = 'sale_payw_remove'),
    path('sale/<uuid:sale_uuid>/extras/update', views.sale_extras_update, name = 'sale_extras_update'),
    path('sale/<uuid:sale_uuid>/payment/cash', views.sale_payment_cash, name = 'sale_payment_cash'),
    path('sale/<uuid:sale_uuid>/payment/card', views.sale_payment_card, name = 'sale_payment_card'),
    path('sale/<uuid:sale_uuid>/payment/cancel', views.sale_payment_cancel, name = 'sale_payment_cancel'),
    path('sale/<uuid:sale_uuid>/complete/cash', views.sale_complete_cash, name = 'sale_complete_cash'),
    path('sale/<uuid:sale_uuid>/complete/zero', views.sale_complete_zero, name = 'sale_complete_zero'),
    path('sale/<uuid:sale_uuid>/cancel', views.sale_cancel, name = 'sale_cancel'),
    path('sale/<uuid:sale_uuid>/select', views.sale_select, name = 'sale_select'),
    path('sale/<uuid:sale_uuid>/update', views.sale_update, name = 'sale_update'),
    path('sale/<uuid:sale_uuid>/close', views.sale_close, name = 'sale_close'),
    path('sale/<uuid:sale_uuid>/email', views.sale_email, name = 'sale_email'),
    # Refunds
    path('<uuid:boxoffice_uuid>/refund/start', views.refund_start, name = 'refund_start'),
    path('refund/<uuid:refund_uuid>/show/select', views.refund_show_select, name = 'refund_show_select'),
    path('refund/<uuid:refund_uuid>/show/<uuid:show_uuid>/performance/select', views.refund_performance_select, name = 'refund_performance_select'),
    path('refund/<uuid:refund_uuid>/ticket/<uuid:ticket_uuid>/add', views.refund_add_ticket, name = 'refund_add_ticket'),
    path('refund/<uuid:refund_uuid>/ticket/<uuid:ticket_uuid>/remove', views.refund_remove_ticket, name = 'refund_remove_ticket'),
    path('refund/<uuid:refund_uuid>/complete', views.refund_complete, name = 'refund_complete'),
    path('refund/<uuid:refund_uuid>/cancel', views.refund_cancel, name = 'refund_cancel'),
    path('refund/<uuid:refund_uuid>/close', views.refund_close, name = 'refund_close'),
    path('refund/<uuid:refund_uuid>/select', views.refund_select, name = 'refund_select'),
    # Checkpoints
    path('<uuid:boxoffice_uuid>/checkpoint/add', views.checkpoint_add, name = 'checkpoint_add'),
    path('checkpoint/<uuid:checkpoint_uuid>/select', views.checkpoint_select, name = 'checkpoint_select'),
    path('checkpoint/<uuid:checkpoint_uuid>/update', views.checkpoint_update, name = 'checkpoint_update'),
    path('checkpoint/<uuid:checkpoint_uuid>/cancel', views.checkpoint_cancel, name = 'checkpoint_cancel'),
    # Tickets
    path('<uuid:boxoffice_uuid>/tickets/search', views.tickets_search, name = 'tickets_search'),
    # SquareUp callback
    path('square/callback', views.square_callback, name='square_callback'),
]
