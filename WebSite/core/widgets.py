from django import forms
from dal.autocomplete import ModelSelect2 as ModelSelect2Base


class ModelSelect2(ModelSelect2Base):

    @property
    def media(self):
        parent = super().media;
        js_list = list(parent._js)
        if 'admin/js/vendor/jquery/jquery.js' in js_list:
            js_list.remove('admin/js/vendor/jquery/jquery.js')
        parent = forms.Media(js = js_list, css = parent._css)
        return parent + forms.Media(css = { 'screen': ('select2-bootstrap4.css',) })
