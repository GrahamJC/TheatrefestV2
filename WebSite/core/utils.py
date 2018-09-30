import os
import uuid

def get_image_filename(instance, filename):
    ext = filename.split('.')[-1]
    return os.path.join('uploads', 'images', f'{uuid.uuid4()}.{ext}')

