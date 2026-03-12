import os
import dateutil
from pathlib import Path

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import PasswordResetView as AuthPasswordResetView
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
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
from .forms import RegistrationForm, PasswordResetForm, AdminFestivalForm, DebugForm

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


# Administration
@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin(request):

    # Render the page
    context = {
    }
    return render(request, 'core/admin.html', context)


class AdminFestivalList(LoginRequiredMixin, ListView):

    model = Festival
    context_object_name = 'festivals'
    template_name = 'core/admin_festival_list.html'

    def get_queryset(self):
        return Festival.objects.order_by('name')

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'System Admin', 'url': reverse('core:admin') },
            { 'text': 'Festivals' },
        ]
        return context_data


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_festival_live(request, slug):

    # Make festival live
    festival = get_object_or_404(Festival, uuid=slug)
    for f in Festival.objects.filter(is_live=True).exclude(id=festival.id):
        f.is_live = False
        f.save()
    festival.is_live = True
    festival.save()
    return redirect('core:admin_festival_list')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_festival_enable(request, slug):

    # Enable festival for this session
    festival = get_object_or_404(Festival, uuid=slug)
    request.session['festival_id'] = festival.id
    return redirect('core:admin_festival_list')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_festival_disable(request):

    # Disable festival for this session
    if 'festival_id' in request.session:
        del request.session['festival_id']
    return redirect('core:admin_festival_list')


class AdminFestivalCreate(LoginRequiredMixin, UserPassesTestMixin, SuccessMessageMixin, CreateView):

    model = Festival
    form_class = AdminFestivalForm
    context_object_name = 'festival'
    template_name = 'core/admin_festival.html'
    success_message = 'Festival added'
    success_url = reverse_lazy('core:admin_festival_list')

    def test_func(self):
        return self.request.user.is_superuser
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = Festival()
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'title',
            'previous',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'System Admin', 'url': reverse('core:admin') },
            { 'text': 'Festivals', 'url': reverse('core:admin_festival_list') },
            { 'text': 'Add' },
        ]
        return context_data


class AdminFestivalUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Festival
    form_class = AdminFestivalForm
    slug_field = 'uuid'
    context_object_name = 'festival'
    template_name = 'core/admin_festival.html'
    success_message = 'Festival updated'
    success_url = reverse_lazy('core:admin_festival_list')

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'title',
            'previous',
            'is_archived',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['breadcrumbs'] = [
            { 'text': 'System Admin', 'url': reverse('core:admin') },
            { 'text': 'Festivals', 'url': reverse('core:admin_festival_list') },
            { 'text': 'Update' },
        ]
        return context_data


@login_required
def admin_festival_delete(request, slug):

    # Delete image
    image = get_object_or_404(Festival, uuid=slug)
    image.delete()
    messages.success(request, 'Festival deleted')
    return redirect('core:admin_festival_list')


# Debug
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
