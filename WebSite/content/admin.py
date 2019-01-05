from django.contrib import admin

from .models import Page, PageImage, Navigator

# Register standard admins
admin.site.register(Page)
admin.site.register(PageImage)
admin.site.register(Navigator)
