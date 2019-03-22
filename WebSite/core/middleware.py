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
        response = self.get_response(request)
        return response
