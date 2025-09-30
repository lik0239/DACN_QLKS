from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Taikhoan

class TaikhoanPlainBackend(BaseBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or password is None:
            return None
        try:
            tk = Taikhoan.objects.get(tentaikhoan=username)
        except Taikhoan.DoesNotExist:
            return None

        if (tk.matkhau or "") != password:
            return None

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": tk.email or "", "first_name": ""}
        )

        if created or user.has_usable_password():
            user.set_unusable_password()
            user.last_login = timezone.now()
            user.save(update_fields=["password", "last_login"])
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
