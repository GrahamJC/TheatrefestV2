from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView, RedirectView

from django_registration.backends.activation.views import ActivationView

import debug_toolbar

from core.views import OneStepRegistrationView, TwoStepRegistrationView, TwoStepActivationView, PasswordResetView, ResendActivationView
from content.views import home

urlpatterns = [
    path('', home),
    path('home', home, name='home'),
    path('content/', include('content.urls')),
    path('festival/', include('festival.urls')),
    path('program/', include('program.urls')),
    path('tickets/', include('tickets.urls')),
    path('venue/', include('venue.urls')),
    path('volunteers/', include('volunteers.urls')),
    path('boxoffice/', include('boxoffice.urls')),
    path('reports/', include('reports.urls')),
    path('admin/', admin.site.urls),
    # django.contrib.auth
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<str:uidb64>/<str:token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    # Django registration
    path('activate/complete', TemplateView.as_view(template_name='django_registration/activation_complete.html'), name='django_registration_activation_complete'),
    path('activate/<str:activation_key>', TwoStepActivationView.as_view(), name='django_registration_activate'),
    path('register', (TwoStepRegistrationView if settings.REGISTRATION_TWOSTEP else OneStepRegistrationView).as_view(), name='django_registration_register'),
    path('register/complete', TemplateView.as_view(template_name='django_registration/registration_complete.html'), name='django_registration_complete'),
    path('register/closed', TemplateView.as_view(template_name='django_registration/registration_closed.html'), name='django_registration_disallowed'),
    # Extension to resend activation e-mail
    path('register/resend/<uuid:user_uuid>', ResendActivationView.as_view(), name='resend_activation_email'),
    # Debug toolbar
    path('__debug__/', include(debug_toolbar.urls)),
    # Select2
    path('select2/', include('django_select2.urls')),
]

# Serve static and media files
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root = settings.MEDIA_ROOT)
