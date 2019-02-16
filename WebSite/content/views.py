import os

from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.template import Template, Context

from .models import Page, PageImage


def home(request):

    # Go to first naviator option
    option = request.site.info.festival.navigators.first()
    if option:
        return redirect(option.href)

    # If there are no navigator options display no home page
    return render(request, 'content/no_home.html')


def page(request, page_uuid):

    # Get the page
    page = get_object_or_404(Page, uuid=page_uuid)

    # Render the page body as a Django template
    media_url = getattr(settings, 'MEDIA_URL', '/media')
    body_context = {
        'page': page,
        'image_urls': { image.name:os.path.join(media_url, image.image.url) for image in page.images.all() if image.image },
        'page_urls': { page.name:reverse('content:page', args=[page.uuid]) for page in request.festival.pages.all() },
    }
    #for image in page.images.all():
    #    context[f'image_{image.name}_url'] = os.path.join(media_url, image.image.url)
    template = Template(page.body)
    body_html = template.render(Context(body_context))

    # Render the page
    page_context = {
        'page': page,
        'body_html': body_html,
    }
    return render(request, 'content/page.html', page_context)
