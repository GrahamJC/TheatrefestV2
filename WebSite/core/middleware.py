from .models import Festival

class FestivalMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.site:
            request.festival = request.site.info.festival
        response = self.get_response(request)
        return response
