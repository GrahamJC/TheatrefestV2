import os
import dateutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.views import PasswordResetView as AuthPasswordResetView
from django.contrib import messages
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic.edit import FormView

from django_registration import signals
from django_registration.exceptions import ActivationError
import django_registration.backends.one_step.views as OneStepViews
import django_registration.backends.activation.views as TwoStepViews

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab

from core.models import Festival
from content.models import Image, PageImage, Document
from program.models import Company, Venue, VenueSponsor, Show, ShowImage
from .forms import RegistrationForm, PasswordResetForm, DebugForm

User = get_user_model()

class OneStepRegistrationView(OneStepViews.RegistrationView):

    form_class = RegistrationForm
    success_url = '/home'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
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
        kwargs['festival'] = self.request.festival
        return kwargs


class TwoStepActivationView(TwoStepViews.ActivationView):

    # Protect against activation being called twice by Outlook safelinks which call the URL
    # usinh HEAD first before the normal GET
    def head(self, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])

    def get_user(self, email):

        User = get_user_model()
        try:
            user = User.objects.get_by_natural_key(self.request.festival, email)
            if user.is_active:
                raise ActivationError(self.ALREADY_ACTIVATED_MESSAGE, code='already_activated')
            return user
        except User.DoesNotExist:
            raise ActivationError(self.BAD_USERNAME_MESSAGE, code='bad_username')


class PasswordResetView(AuthPasswordResetView):

    form_class = PasswordResetForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs


class ResendActivationView(TwoStepViews.RegistrationView):

    def get(self, request, *args, **kwargs):
        user_uuid = self.kwargs['user_uuid']
        user = get_object_or_404(User, uuid = user_uuid)
        self.send_activation_email(user)
        return redirect(reverse('django_registration_complete'))



def get_orphan_images():
    uuids = []
    uuids.extend([Path(festival.venue_map.name).stem for festival in Festival.objects.exclude(venue_map='')])
    uuids.extend([Path(image.image.name).stem for image in Image.objects.exclude(image='')])
    uuids.extend([Path(page_image.image.name).stem for page_image in PageImage.objects.exclude(image='')])
    uuids.extend([Path(company.image.name).stem for company in Company.objects.exclude(image='')])
    uuids.extend([Path(venue.image.name).stem for venue in Venue.objects.exclude(image='')])
    uuids.extend([Path(venue_sponsor.image.name).stem for venue_sponsor in VenueSponsor.objects.exclude(image='')])
    uuids.extend([Path(show.image.name).stem for show in Show.objects.exclude(image='')])
    uuids.extend([Path(show_image.image.name).stem for show_image in ShowImage.objects.exclude(image='')])
    uuids = list(dict.fromkeys(uuids))
    count = 0
    size = 0
    files = []
    for file in Path(os.path.join(settings.MEDIA_ROOT, 'uploads/images')).iterdir():
        if file.is_file():
            uuid = file.stem
            if not uuid in uuids:
                count += 1
                size += file.stat().st_size
                files.append(file)
    return {
        'count': count,
        'total_size': size,
        'files': files,
    }


def get_orphan_documents():
    uuids = []
    uuids.extend([Path(document.file.name).stem for document in Document.objects.exclude(file='')])
    uuids = list(dict.fromkeys(uuids))
    count = 0
    size = 0
    files = []
    for file in Path(os.path.join(settings.MEDIA_ROOT, 'uploads/documents')).iterdir():
        if file.is_file():
            uuid = file.stem
            if not uuid in uuids:
                count += 1
                size += file.stat().st_size
                files.append(file)
    return {
        'count': count,
        'total_size': size,
        'files': files,
    }

class DebugFormView(FormView):

    template_name = 'core/debug.html'
    form_class= DebugForm
    success_url = '/core/debug'

    def get_initial(self):
        initial = {}
        festival_id = self.request.session.get('festival_id', None)
        if festival_id:
            initial['festival'] = festival_id
        if 'date' in self.request.session:
            initial['date'] = dateutil.parser.parse(self.request.session['date']).date()
        if 'time' in self.request.session:
            initial['time'] = dateutil.parser.parse(self.request.session['time']).time()
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['orphan_images'] = get_orphan_images()
        context['orphan_documents'] = get_orphan_documents()
        return context

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('festival'),
            Row(
                Column('date', css_class='form-group col-md-6 mb-0'),
                Column('time', css_class='form-group col-md-6 mb-0'),
                css_class = 'form-row',
            ),
            FormActions(
                Submit('update', 'Update'),
            ),
        )
        return form

    def form_valid(self, form):
        if form.cleaned_data['festival']:
            self.request.session['festival_id'] = form.cleaned_data['festival'].id
        elif 'festival_id' in self.request.session:
            del self.request.session['festival_id']
        if form.cleaned_data['date']:
            self.request.session['date'] = str(form.cleaned_data['date'])
        elif 'date' in self.request.session:
            del self.request.session['date']
        if form.cleaned_data['time']:
            self.request.session['time'] = str(form.cleaned_data['time'])
        elif 'time' in self.request.session:
            del self.request.session['time']
        return super().form_valid(form)


#@login_required
def debug_clean_images(request):
    orphan_dir = Path(os.path.join(settings.MEDIA_ROOT, 'uploads/images/orphan'))
    orphan_dir.mkdir(exist_ok=True)
    for file in get_orphan_images()['files']:
        file.replace(orphan_dir / file.name)
    messages.info(request, 'Orphans moved to sub-directory')
    return redirect('core:debug')


#@login_required
def debug_clean_documents(request):
    orphan_dir = Path(os.path.join(settings.MEDIA_ROOT, 'uploads/documents/orphan'))
    orphan_dir.mkdir(exist_ok=True)
    for file in get_orphan_documents()['files']:
        file.replace(orphan_dir / file.name)
    messages.info(request, 'Orphans moved to sub-directory')
    return redirect('core:debug')


