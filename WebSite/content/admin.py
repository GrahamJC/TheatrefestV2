from django.contrib import admin

from .models import Page, PageImage, Navigator, Image, Resource, Document

# Register standard admins
admin.site.register(Page)
admin.site.register(PageImage)
admin.site.register(Navigator)
admin.site.register(Image)
admin.site.register(Resource)
admin.site.register(Document)
