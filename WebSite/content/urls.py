from django.urls import path

from . import views

app_name = 'content'

urlpatterns = [
    # Pages
    path('page/<uuid:page_uuid>', views.page, name='page'),
]
