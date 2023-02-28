import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, HTML, Submit, Button, Row, Column
from crispy_forms.bootstrap import FormActions, TabHolder, Tab, Div

from .models import Page, PageImage, Navigator, Image, Document, Resource
from .forms import AdminPageForm, AdminPageImageForm, AdminNavigatorForm, AdminImageForm, AdminDocumentForm, AdminResourceForm

def home(request):

    # Go to first naviator option
    option = request.festival.navigators.first()
    if option:
        return redirect(option.href)

    # If there are no navigator options display no home page
    return render(request, 'content/no_home.html')


def page(request, page_uuid):

    # Get the page
    page = get_object_or_404(Page, uuid=page_uuid)

    # Render the page body as a Django template
    image_urls = { image.name:image.get_absolute_url() for image in request.festival.images.all() if image.image }
    image_urls.update({ image.name:image.get_absolute_url() for image in page.images.all() if image.image })
    document_urls = { document.name:document.get_absolute_url() for document in request.festival.documents.all() if document.file }
    page_urls = { page.name:page.get_absolute_url() for page in request.festival.pages.all() }
    resource_urls = { resource.name:resource.get_absolute_url() for resource in request.festival.resources.all() }
    body_context = {
        'user': request.user,
        'page': page,
        'image_urls': image_urls,
        'document_urls': document_urls,
        'page_urls': page_urls,
        'resource_urls': resource_urls,
    }
    template = Template(page.body)
    body_html = template.render(Context(body_context))

    # Render the page
    page_context = {
        'page': page,
        'body_html': body_html,
    }
    return render(request, 'content/page.html', page_context)


def page_test(request, page_uuid):

    # Get the page
    page = get_object_or_404(Page, uuid=page_uuid)

    # Render the page body as a Django template
    image_urls = { image.name:image.get_absolute_url() for image in request.festival.images.all() if image.image }
    image_urls.update({ image.name:image.get_absolute_url() for image in page.images.all() if image.image })
    document_urls = { document.name:document.get_absolute_url() for document in request.festival.documents.all() if document.file }
    page_urls = { page.name:page.get_test_url() for page in request.festival.pages.all() }
    resource_urls = { resource.name:resource.get_test_url() for resource in request.festival.resources.all() }
    body_context = {
        'user': request.user,
        'page': page,
        'image_urls': image_urls,
        'document_urls': document_urls,
        'page_urls': page_urls,
        'resource_urls': resource_urls,
    }
    template = Template(page.body_test or page.body)
    body_html = template.render(Context(body_context))

    # Render the page
    page_context = {
        'page': page,
        'body_html': body_html,
    }
    return render(request, 'content/page.html', page_context)


def page_name(request, page_name):

    # Get page and render it
    find_page = get_object_or_404(Page, festival=request.festival, name__iexact=page_name)
    return page(request, find_page.uuid)


def document(request, document_uuid):

    # Get the document
    document = get_object_or_404(Document, uuid=document_uuid)

    # Return it
    response = FileResponse(document.file, as_attachment=True, filename=document.filename)
    return response


def resource(request, resource_uuid):

    # Get the document and return it
    resource = get_object_or_404(Resource, uuid=resource_uuid)
    image_urls = { image.name:image.get_absolute_url() for image in request.festival.images.all() if image.image }
    document_urls = { document.name:document.get_absolute_url() for document in request.festival.documents.all() if document.file }
    page_urls = { page.name:page.get_absolute_url() for page in request.festival.pages.all() }
    resource_urls = { resource.name:resource.get_absolute_url() for resource in request.festival.resources.all() }
    context = {
        'page': page,
        'image_urls': image_urls,
        'document_urls': document_urls,
        'page_urls': page_urls,
        'resource_urls': resource_urls,
    }
    template = Template(resource.body)
    return HttpResponse(template.render(Context(context)), content_type=resource.type)


def resource_test(request, resource_uuid):

    # Get the document and return it
    resource = get_object_or_404(Resource, uuid=resource_uuid)
    image_urls = { image.name:image.get_absolute_url() for image in request.festival.images.all() if image.image }
    document_urls = { document.name:document.get_absolute_url() for document in request.festival.documents.all() if document.file }
    page_urls = { page.name:page.get_test_url() for page in request.festival.pages.all() }
    resource_urls = { resource.name:resource.get_test_url() for resource in request.festival.resources.all() }
    context = {
        'page': page,
        'image_urls': image_urls,
        'document_urls': document_urls,
        'page_urls': page_urls,
        'resource_urls': resource_urls,
    }
    template = Template(resource.body_test or resource.body)
    return HttpResponse(template.render(Context(context)), content_type=resource.type)


class AdminPageList(LoginRequiredMixin, ListView):

    model = Page
    context_object_name = 'pages'
    template_name = 'content/admin_page_list.html'

    def get_queryset(self):
        return Page.objects.filter(festival=self.request.festival)


class AdminPageCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Page
    form_class = AdminPageForm
    context_object_name = 'page'
    template_name = 'content/admin_page.html'
    success_message = 'Page added'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Field('name'),
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form

    def get_success_url(self):
        return reverse('content:admin_page_update', args=[self.object.uuid])


class AdminPageUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Page
    form_class = AdminPageForm
    slug_field = 'uuid'
    context_object_name = 'page'
    template_name = 'content/admin_page.html'
    success_message = 'Page updated'
    
    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.fields['body'].widget.attrs['rows'] = 16
        form.fields['body_test'].widget.attrs['rows'] = 16
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('name', css_class='col-sm-4'),
                Column('title', css_class='col-sm-8'),
                css_class='form-row',
            ),
            TabHolder(
                Tab ('Body',
                    Field('body', css_class='mt-2 tf-nowrap'),
                ),
                Tab ('Test',
                    Field('body_test', css_class='mt-2 tf-nowrap'),
                    Div(
                        Submit('copy-from-body', 'Copy from Body'),
                        Submit('copy-to-body', 'Copy to Body'),
                        Submit('save-test', 'Save'),
                        Button('show-test', 'Show'),
                        css_class='text-right',
                    )
                ),
                Tab('Images',
                    HTML('{% include \'content/_admin_page_images.html\' %}')
                ),
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def form_valid(self, form):
        if 'copy-from-body' in self.request.POST:
            form.instance.body_test = form.instance.body
        elif 'copy-to-body' in self.request.POST:
            form.instance.body = form.instance.body_test
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        if 'save' in self.request.POST:
            return reverse('content:admin_page_list')
        else:
            return reverse('content:admin_page_update_tab', args=[self.object.uuid, 'test'])
    

@login_required
def admin_page_delete(request, slug):

    # Delete page
    page = get_object_or_404(Page, uuid=slug)
    page.delete()
    messages.success(request, 'Page deleted')
    return redirect('content:admin_page_list')


class AdminPageImageCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = PageImage
    form_class = AdminPageImageForm
    context_object_name = 'image'
    template_name = 'content/admin_page_image.html'
    success_message = 'Page image added'

    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(Page, uuid=kwargs['page_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['page'] = self.page
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['page'] = self.page
        return context_data

    def get_success_url(self):
        return reverse('content:admin_page_update_tab', args=[self.page.uuid, 'images'])


class AdminPageImageUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = PageImage
    form_class = AdminPageImageForm
    slug_field = 'uuid'
    context_object_name = 'image'
    template_name = 'content/admin_page_image.html'
    success_message = 'Page image updated'

    def dispatch(self, request, *args, **kwargs):
        self.page = get_object_or_404(Page, uuid=kwargs['page_uuid'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['page'] = self.page
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['page'] = self.page
        return context_data

    def get_success_url(self):
        return reverse('content:admin_page_update_tab', args=[self.page.uuid, 'images'])
    

@login_required
def admin_page_image_delete(request, page_uuid, slug):

    # Delete page image
    image = get_object_or_404(PageImage, uuid=slug)
    image.delete()
    messages.success(request, 'Page image deleted')
    return redirect('content:admin_page_update_tab', page_uuid, 'images')


class AdminNavigatorList(LoginRequiredMixin, ListView):

    model = Navigator
    context_object_name = 'navigators'
    template_name = 'content/admin_navigator_list.html'

    def get_queryset(self):
        return Navigator.objects.filter(festival=self.request.festival)


class AdminNavigatorCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Navigator
    form_class = AdminNavigatorForm
    context_object_name = 'navigator'
    template_name = 'content/admin_navigator.html'
    success_message = 'Navigator added'
    success_url = reverse_lazy('content:admin_navigator_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('seqno', css_class = 'col-sm-2'),
                Column('label', css_class = 'col-sm-10'),
                class_class='form-row',
            ),
            'type',
            'url',
            'page',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


class AdminNavigatorUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Navigator
    form_class = AdminNavigatorForm
    slug_field = 'uuid'
    context_object_name = 'navigator'
    template_name = 'content/admin_navigator.html'
    success_message = 'Navigator updated'
    success_url = reverse_lazy('content:admin_navigator_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('seqno', css_class = 'col-sm-2'),
                Column('label', css_class = 'col-sm-10'),
                class_class='form-row',
            ),
            'type',
            'url',
            'page',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form
    

@login_required
def admin_navigator_delete(request, slug):

    # Delete navigator
    navigator = get_object_or_404(Navigator, uuid=slug)
    navigator.delete()
    messages.success(request, 'Navigator deleted')
    return redirect('content:admin_navigator_list')


class AdminImageList(LoginRequiredMixin, ListView):

    model = Image
    context_object_name = 'images'
    template_name = 'content/admin_image_list.html'

    def get_queryset(self):
        return Image.objects.filter(festival=self.request.festival)


class AdminImageCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Image
    form_class = AdminImageForm
    context_object_name = 'image'
    template_name = 'content/admin_image.html'
    success_message = 'Image added'
    success_url = reverse_lazy('content:admin_image_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            'map',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


class AdminImageUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Image
    form_class = AdminImageForm
    slug_field = 'uuid'
    context_object_name = 'image'
    template_name = 'content/admin_image.html'
    success_message = 'Image updated'
    success_url = reverse_lazy('content:admin_image_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'image',
            'map',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form
    

@login_required
def admin_image_delete(request, slug):

    # Delete image
    image = get_object_or_404(Image, uuid=slug)
    image.delete()
    messages.success(request, 'Image deleted')
    return redirect('content:admin_image_list')


class AdminDocumentList(LoginRequiredMixin, ListView):

    model = Document
    context_object_name = 'documents'
    template_name = 'content/admin_document_list.html'

    def get_queryset(self):
        return Document.objects.filter(festival=self.request.festival)


class AdminDocumentCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Document
    form_class = AdminDocumentForm
    context_object_name = 'document'
    template_name = 'content/admin_document.html'
    success_message = 'Document added'
    success_url = reverse_lazy('content:admin_document_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'file',
            'filename',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


class AdminDocumentUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Document
    form_class = AdminDocumentForm
    slug_field = 'uuid'
    context_object_name = 'document'
    template_name = 'content/admin_document.html'
    success_message = 'Document updated'
    success_url = reverse_lazy('content:admin_document_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            'name',
            'file',
            'filename',
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form
    

@login_required
def admin_document_delete(request, slug):

    # Delete document
    document = get_object_or_404(Document, uuid=slug)
    document.delete()
    messages.success(request, 'Document deleted')
    return redirect('content:admin_document_list')


class AdminResourceList(LoginRequiredMixin, ListView):

    model = Resource
    context_object_name = 'resources'
    template_name = 'content/admin_resource_list.html'

    def get_queryset(self):
        return Resource.objects.filter(festival=self.request.festival)


class AdminResourceCreate(LoginRequiredMixin, SuccessMessageMixin, CreateView):

    model = Resource
    form_class = AdminResourceForm
    context_object_name = 'resource'
    template_name = 'content/admin_resource.html'
    success_message = 'Resource added'
    success_url = reverse_lazy('content:admin_resource_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('name', css_class='col-sm-8'),
                Column('type', css_class='col-sm-4'),
                css_class='form-row',
            ),
            'body',
            FormActions(
                Submit('save', 'Save'),
                Button('cancel', 'Cancel'),
            ),
        )
        return form


class AdminResourceUpdate(LoginRequiredMixin, SuccessMessageMixin, UpdateView):

    model = Resource
    form_class = AdminResourceForm
    slug_field = 'uuid'
    context_object_name = 'resource'
    template_name = 'content/admin_resource.html'
    success_message = 'Resource updated'
    success_url = reverse_lazy('content:admin_resource_list')
    
    def dispatch(self, request, *args, **kwargs):
        self.initial_tab = kwargs.pop('tab', None)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['festival'] = self.request.festival
        return kwargs

    def get_form(self):
        form = super().get_form()
        form['body'].label = ''
        form['body_test'].label = ''
        form.helper = FormHelper()
        form.helper.layout = Layout(
            Row(
                Column('name', css_class='col-sm-8'),
                Column('type', css_class='col-sm-4'),
                css_class='form-row',
            ),
            TabHolder(
                Tab ('Body',
                    Field('body', css_class='mt-2 tf-nowrap'),
                ),
                Tab ('Test',
                    Field('body_test', css_class='mt-2 tf-nowrap'),
                    Div(
                        Submit('copy-from-body', 'Copy from Body'),
                        Submit('copy-to-body', 'Copy to Body'),
                        Submit('save-test', 'Save'),
                        Button('show-test', 'Show'),
                        css_class='text-right',
                    )
                ),
            ),
            FormActions(
                Submit('save', 'Save'),
                Button('delete', 'Delete'),
                Button('cancel', 'Cancel'),
            )
        )
        return form

    def form_valid(self, form):
        if 'copy-from-body' in self.request.POST:
            form.instance.body_test = form.instance.body
        elif 'copy-to-body' in self.request.POST:
            form.instance.body = form.instance.body_test
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data['initial_tab'] = self.initial_tab
        return context_data

    def get_success_url(self):
        if 'save' in self.request.POST:
            return reverse('content:admin_resource_list')
        else:
            return reverse('content:admin_resource_update_tab', args=[self.object.uuid, 'test'])
    

@login_required
def admin_resource_delete(request, slug):

    # Delete resource
    resource = get_object_or_404(Resource, uuid=slug)
    resource.delete()
    messages.success(request, 'Resource deleted')
    return redirect('content:admin_resource_list')
