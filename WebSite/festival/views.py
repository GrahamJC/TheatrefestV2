import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404, render, redirect
from django.template import Template, Context
from django.urls import reverse_lazy
from django.views.generic import View, FormView, CreateView, UpdateView, DeleteView

from extra_views import InlineFormSet, CreateWithInlinesView, UpdateWithInlinesView
from extra_views.contrib.mixins import SuccessMessageWithInlinesMixin

from content.models import Page, PageImage, Navigator
from .forms import PageForm, PageImageForm, NavigatorForm


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
    ImageFormset = inlineformset_factory(Page, PageImage, form=PageImageForm, extra=1)

    # Check request type
    if request.method == 'GET':

        # Create page form and image formset
        form = PageForm(initial={'festival': request.festival})
        images_formset = ImageFormset()

    else:

        # Create page form, bind it to POST data and valdate
        page = None
        form = PageForm(data=request.POST, files=request.FILES)
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
    page = get_object_or_404(Page, uuid=page_uuid)

    # Create image formset type
    ImageFormset = inlineformset_factory(Page, PageImage, form=PageImageForm, extra=1)

    # Check request type
    if request.method == 'GET':

        # Create page form and image formset
        form = PageForm(instance=page)
        images_formset = ImageFormset(instance=page)

    else:

        # Create page form, bind it to POST data and valdate
        page_valid = False
        form = PageForm(instance=page, data=request.POST, files=request.FILES)
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
    page = get_object_or_404(Page, uuid=page_uuid)

    # Delete it
    page.delete()

    # Return to page list
    messages.success(request, 'Page deleted')
    return redirect('festival:admin_pages')


class PageImagesInline(InlineFormSet):

    model = PageImage
    form_class = PageImageForm

    def get_factory_kwargs(self):
        kwargs = super().get_factory_kwargs()
        kwargs['extra'] = 1
        return kwargs


class CreatePageView(LoginRequiredMixin, SuccessMessageWithInlinesMixin, CreateWithInlinesView):

    model = Page
    form_class = PageForm
    template_name = 'festival/admin_page_create.html'
    success_message = 'Page added'
    success_url = reverse_lazy('festival:admin_pages')
    inlines = [PageImagesInline]

    def get_initial(self):
        initial = super().get_initial()
        initial['festival'] = self.request.festival
        return initial


class UpdatePageView(LoginRequiredMixin, SuccessMessageWithInlinesMixin, UpdateWithInlinesView):

    model = Page
    form_class = PageForm
    template_name = 'festival/admin_page_update.html'
    success_message = 'Page updated'
    success_url = reverse_lazy('festival:admin_pages')
    inlines = [PageImagesInline]

    def get_object(self):
        page_uuid = self.kwargs.get('page_uuid')
        return get_object_or_404(Page, uuid=page_uuid)


@login_required
def admin_navigators(request):

    # Render the page
    return render(request, 'festival/admin_navigators.html')


@login_required
def admin_navigator_create(request):

    # Check request type
    if request.method == 'GET':

        # Create navigator form
        form = NavigatorForm(request.festival, initial={'festival': request.festival})

    else:

        # Create navigator form, bind it to POST data and valdate
        navigator = None
        form = NavigatorForm(request.festival, data=request.POST)
        if form.is_valid():
            navigator = form.save()

            # Notify success and return to navigator list (if exiting) or navigator edit (if continuing)
            messages.success(request, 'Navigator added')
            if 'Exit' in request.POST:
                return redirect('festival:admin_navigators')
            else:
                return redirect('festival:admin_navigator_update', navigator_uuid=navigator.uuid)

    # Create context and render page
    context = {
        'form': form,
    }
    return render(request, 'festival/admin_navigator_create.html', context)


@login_required
def admin_navigator_update(request, navigator_uuid):

    # Get navigator
    navigator = get_object_or_404(Navigator, uuid=navigator_uuid)

    # Check request type
    if request.method == 'GET':

        # Create navigator form
        form = NavigatorForm(request.festival, instance=navigator)

    else:

        # Create navigator form, bind it to POST data and valdate
        form = NavigatorForm(request.festival, instance=navigator, data=request.POST)
        if form.is_valid():
            form.save()

            # Notify success and return to navigator list (if exiting) or navigator edit (if continuing)
            messages.success(request, 'Navigator updated')
            if 'Exit' in request.POST:
                return redirect('festival:admin_navigators')

    # Create context and render page
    context = {
        'navigator': navigator,
        'form': form,
    }
    return render(request, 'festival/admin_navigator_update.html', context)


@login_required
def admin_navigator_delete(request, navigator_uuid):

    # Get navigator
    navigator = get_object_or_404(Navigator, uuid=navigator_uuid)

    # Delete it
    navigator.delete()

    # Return to navigator  list
    messages.success(request, 'Navigator deleted')
    return redirect('festival:admin_navigators')
