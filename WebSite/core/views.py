from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login

from django_registration import signals
import django_registration.backends.one_step.views as OneStepViews
import django_registration.backends.activation.views as TwoStepViews

from .forms import RegistrationForm

User = get_user_model()

class OneStepRegistrationView(OneStepViews.RegistrationView):

    form_class = RegistrationForm
    success_url = '/home'

    def get_initial(self):
        initial = super().get_initial()
        #initial['site'] = self.request.site
        initial['festival'] = self.request.festival
        return initial

    def register(self, form):
        new_user = form.save()
        new_user = authenticate(self.request, **{
            User.USERNAME_FIELD: new_user.get_username(),
            'password': form.cleaned_data['password1']
        })
        login(self.request, new_user)
        signals.user_registered.send(
            sender=self.__class__,
            user=new_user,
            request=self.request
        )
        return new_user

class TwoStepRegistrationView(TwoStepViews.RegistrationView):

    form_class = RegistrationForm

    def get_initial(self):
        initial = super().get_initial()
        initial['site'] = self.request.site
        initial['festival'] = self.request.festival
        return initial

