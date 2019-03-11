from django.shortcuts import get_object_or_404

from content.models import Image, Resource

from .models import Festival

class FestivalMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.site:
            festival_id = request.session.get('festival_id', None)
            if festival_id:
                request.festival = get_object_or_404(Festival, pk=festival_id)
            else:
                request.festival = request.site.info.festival
            if request.festival:
                stylesheet = Resource.objects.filter(festival=request.festival, name='Stylesheet').first()
                if stylesheet:
                    request.festival.stylesheet = stylesheet.get_test_url() if request.path.endswith('test') else stylesheet.get_absolute_url()
                banner = Image.objects.filter(festival=request.festival, name='Banner').first()
                if banner:
                    request.festival.banner = banner.get_absolute_url()
                banner = Image.objects.filter(festival=request.festival, name='BannerMobile').first()
                if banner:
                    request.festival.banner_mobile = banner.get_absolute_url()
        response = self.get_response(request)
        return response
