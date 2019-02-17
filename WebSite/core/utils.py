import os
import uuid

from django.db.models.fields.related import OneToOneField, ReverseOneToOneDescriptor


def get_image_filename(instance, filename):
    if hasattr(instance, 'filename') and not instance.filename:
        instance.filename = filename
    ext = filename.split('.')[-1]
    return os.path.join('uploads', 'images', f'{uuid.uuid4()}.{ext}')


def get_document_filename(instance, filename):
    if hasattr(instance, 'filename') and not instance.filename:
        instance.filename = filename
    ext = filename.split('.')[-1]
    return os.path.join('uploads', 'documents', f'{uuid.uuid4()}.{ext}')


class AutoSingleRelatedObjectDescriptor(ReverseOneToOneDescriptor):
    """
    The descriptor that handles the object creation for an AutoOneToOneField.
    """

    def __get__(self, instance, instance_type=None):
        model = getattr(self.related, 'related_model', self.related.model)

        try:
            return (
                super(AutoSingleRelatedObjectDescriptor, self)
                    .__get__(instance, instance_type)
            )
        except model.DoesNotExist:
            # Using get_or_create instead() of save() or create() as it better handles race conditions
            model.objects.get_or_create(**{self.related.field.name: instance})

            # Don't return obj directly, otherwise it won't be added
            # to Django's cache, and the first 2 calls to obj.relobj
            # will return 2 different in-memory objects
            return (
                super(AutoSingleRelatedObjectDescriptor, self)
                    .__get__(instance, instance_type)
            )


class AutoOneToOneField(OneToOneField):
    """
    OneToOneField creates related object on first call if it doesnt exist yet.
    Use it instead of original OneToOne field.
    example:
        class MyProfile(models.Model):
            user = AutoOneToOneField(User, primary_key=True)
            home_page = models.URLField(max_length=255, blank=True)
            icq = models.IntegerField(max_length=255, null=True)
    """

    def contribute_to_related_class(self, cls, related):
        setattr(
            cls,
            related.get_accessor_name(),
            AutoSingleRelatedObjectDescriptor(related)
        )

#class AutoSingleRelatedObjectDescriptor(ReverseOneToOneDescriptor):

#    def __get__(self, instance, type=None):
#        rel_obj = None
#        try:
#            rel_obj = super().__get__(instance, type)
#            return related_object
#        except self.RelatedObjectDoesNotExist:
#            kwargs = {
#                self.related.field.name: instance,
#            }
#            rel_obj = self.related.related_model._default_manager.create(**kwargs)
#            setattr(instance, self.related.get_cache_name(), rel_obj)
#            return rel_obj


#class AutoOneToOneField(OneToOneField):

#    related_accessor_class = AutoSingleRelatedObjectDescriptor

