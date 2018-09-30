from django_registration.backends.activation.views import RegistrationView as BaseRegistrationView

from .forms import RegistrationForm

class RegistrationView(BaseRegistrationView):

    form_class = RegistrationForm

    def get_initial(self):
        initial = super().get_initial()
        initial['site'] = self.request.site
        initial['festival'] = self.request.festival
        return initial


