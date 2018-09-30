import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib import messages
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse_lazy
from django.views.generic import View, FormView, CreateView, UpdateView, DeleteView

from extra_views import InlineFormSet, CreateWithInlinesView, UpdateWithInlinesView
from extra_views.contrib.mixins import SuccessMessageWithInlinesMixin

from .models import ContentPage, ContentPageImage
from .forms import ContentPageForm, ContentPageImageForm


def home(request):

    # Go to first naviator option
    option = request.site.info.festival.navigator_options.first()
    if option:
        return redirect(option.href)

    # If there are no navigator options display no home page
    return render(request, 'festival/no_home.html')


def content_page(request, page_uuid):

    # Get the page
    page = get_object_or_404(ContentPage, uuid=page_uuid)

    # Render the page body as a Django template
    context = {
        'page': page,
    }
    media_url = getattr(settings, 'MEDIA_URL', '/media')
    for image in page.images.all():
        context[f'image_{image.name}_url'] = os.path.join(media_url, image.image.url)
    template = Template(page.body)
    body_html = template.render(Context(context))

    # Render the page
    context = {
        'page': page,
        'body_html': body_html,
    }
    return render(request, 'festival/content_page.html', context)


@login_required
def admin_home(request):

    # Render the page
    context = {
        'festival': request.site.info.festival,
    }
    return render(request, 'festival/admin_main.html', context)


@login_required
def admin_pages(request):

    # Render the page
    return render(request, 'festival/admin_pages.html')


@login_required
def admin_page_create(request):

    # Create image formset type
    ImageFormset = inlineformset_factory(ContentPage, ContentPageImage, form=ContentPageImageForm, extra=1)

    # Check request type
    if request.method == 'GET':

        # Create page form and image formset
        form = ContentPageForm(initial={'festival': request.festival})
        images_formset = ImageFormset()

    else:

        # Create page form, bind it to POST data and valdate
        page = None
        form = ContentPageForm(data=request.POST, files=request.FILES)
        if form.is_valid():
            page = form.save(commit=False)

        # Create images formset, bind to POST data and validate
        images_formset = ImageFormset(instance=page, data=request.POST, files=request.FILES)
        if page and images_formset.is_valid():

            # Save the page and images
            page.save()
            images_formset.save()

            # Notify success and return to page list (if exiting) or page edit (if continuing)
            messages.success(request, 'Page added')
            if 'Exit' in request.POST:
                return redirect('festival:admin_pages')
            else:
                return redirect('festival:admin_page_update', page_uuid=page.uuid)

    # Create context and render page
    context = {
        'form': form,
        'images_formset': images_formset,
    }
    return render(request, 'festival/admin_page_create.html', context)


@login_required
def admin_page_update(request, page_uuid):

    # Get page
    page = get_object_or_404(ContentPage, uuid=page_uuid)

    # Create image formset type
    ImageFormset = inlineformset_factory(ContentPage, ContentPageImage, form=ContentPageImageForm, extra=1)

    # Check request type
    if request.method == 'GET':

        # Create page form and image formset
        form = ContentPageForm(instance=page)
        images_formset = ImageFormset(instance=page)

    else:

        # Create page form, bind it to POST data and valdate
        page_valid = False
        form = ContentPageForm(instance=page, data=request.POST, files=request.FILES)
        if form.is_valid():
            form.save(commit=False)
            page_valid = True

        # Create images formset, bind to POST data and validate
        images_formset = ImageFormset(instance=page, data=request.POST, files=request.FILES)
        if page_valid and images_formset.is_valid():

            # Save the page and images
            page.save()
            images_formset.save()

            # Notify success and return to page list (if exiting) or page edit (if continuing)
            messages.success(request, 'Page updated')
            if 'Exit' in request.POST:
                return redirect('festival:admin_pages')

    # Create context and render page
    context = {
        'page': page,
        'form': form,
        'images_formset': images_formset,
    }
    return render(request, 'festival/admin_page_update.html', context)


@login_required
def admin_page_delete(request, page_uuid):

    # Get page
    page = get_object_or_404(ContentPage, uuid=page_uuid)

    # Delete it
    page.delete()

    # Return to page list
    messages.success(request, 'Page deleted')
    return redirect('festival:admin_pages')


class ContentPageImagesInline(InlineFormSet):

    model = ContentPageImage
    form_class = ContentPageImageForm

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs['extra'] = 1
        return kwargs


class CreateContentPageView(LoginRequiredMixin, SuccessMessageWithInlinesMixin, CreateWithInlinesView):

    model = ContentPage
    form_class = ContentPageForm
    template_name = 'festival/admin_page_create.html'
    success_message = 'Page added'
    success_url = reverse_lazy('festival:admin_pages')
    inlines = [ContentPageImagesInline]

    def get_initial(self):
        initial = super().get_initial()
        initial['festival'] = self.request.festival
        return initial


class UpdateContentPageView(LoginRequiredMixin, SuccessMessageWithInlinesMixin, UpdateWithInlinesView):

    model = ContentPage
    form_class = ContentPageForm
    template_name = 'festival/admin_page_update.html'
    success_message = 'Page updated'
    success_url = reverse_lazy('festival:admin_pages')
    inlines = [ContentPageImagesInline]

    def get_object(self):
        page_uuid = self.kwargs.get('page_uuid')
        return get_object_or_404(ContentPage, uuid=page_uuid)
