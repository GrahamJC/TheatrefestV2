from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import PasswordResetView as AuthPasswordResetView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from django_registration import signals
import django_registration.backends.one_step.views as OneStepViews
import django_registration.backends.activation.views as TwoStepViews

from .forms import RegistrationForm, PasswordResetForm

User = get_user_model()


class OneStepRegistrationView(OneStepViews.RegistrationView):

    form_class = RegistrationForm
    success_url = '/home'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['site'] = self.request.site
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update({
        })
        return context

    def register(self, form):
        new_user = form.save()
        new_user = authenticate(self.request, **{
            User.USERNAME_FIELD: new_user.get_username(),
            'password': form.cleaned_data['password1']
        })
        login(self.request, new_user)
        signals.user_registered.send(
            sender = self.__class__,
            user = new_user,
            request = self.request
        )
        return new_user


class TwoStepRegistrationView(TwoStepViews.RegistrationView):

    form_class = RegistrationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['site'] = self.request.site
        kwargs['festival'] = self.request.festival
        return kwargs


class TwoStepActivationView(TwoStepViews.ActivationView):

    def get_user(self, email):

        User = get_user_model()
        try:
            user = User.objects.get_by_natural_key(self.request.site, self.request.festival, email)
            if user.is_active:
                raise ActivationError(self.ALREADY_ACTIVATED_MESSAGE, code='already_activated')
            return user
        except User.DoesNotExist:
            raise ActivationError(self.BAD_USERNAME_MESSAGE, code='bad_username')


class PasswordResetView(AuthPasswordResetView):

    form_class = PasswordResetForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['site'] = self.request.site
        kwargs['festival'] = self.request.festival
        return kwargs


class ResendActivationView(TwoStepViews.RegistrationView):

    def get(self, request, *args, **kwargs):
        user_uuid = self.kwargs['user_uuid']
        user = get_object_or_404(User, uuid = user_uuid)
        self.send_activation_email(user)
        return redirect(reverse('django_registration_complete'))

