from django.contrib import admin

from .models import ContentPage, ContentPageImage, NavigatorOption

# Register standard admins
admin.site.register(ContentPage)
admin.site.register(ContentPageImage)
admin.site.register(NavigatorOption)
