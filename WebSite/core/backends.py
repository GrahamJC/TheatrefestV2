import logging

from django.contrib.auth.backends import UserModel, ModelBackend

logger = logging.getLogger(__name__)

class AuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        try:
            if username.startswith('#'):
                logger.info(f'Authenticating system user: {username[1:]}')
                user = UserModel._default_manager.get_by_natural_key(None, None, username[1:])
            elif username.startswith('!'):
                logger.info(f'Authenticating site user: {request.site.name}/{username[1:]}')
                user = UserModel._default_manager.get_by_natural_key(request.site, None, username[1:])
            else:
                logger.info(f'Authenticating festival user: {request.festival.name}/{username}')
                user = UserModel._default_manager.get_by_natural_key(request.site, request.festival, username)
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user (#20760).
            UserModel().set_password(password)
        else:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        logger.warn('Authenticatication failed')
        return None
