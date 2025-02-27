from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django_softdelete.models import SoftDeleteModel

from apps.common.models import BaseModel


class UserManager(BaseUserManager):
    def active_user(self):
        return self.filter(is_active=True)

    def active_staff(self):
        return self.filter(is_staff=True, is_active=True)

    def withdraw_user(self):
        return self.filter(is_active=False, is_staff=False)

    def withdraw_staff(self):
        return self.filter(is_staff=True, is_active=False)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=30)
    nickname = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=130)
    profile_image = models.CharField(max_length=255, null=True, blank=True)
    provider = models.CharField(max_length=50, null=True, blank=True)
    provider_id = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # 로그인 시 username이 아니라 email로 로그인하게 됨(식별자가 email)
    USERNAME_FIELD = "email"

    objects = UserManager()

    def has_perm(self, perm, obj=None):
        # 사용자가 superuser인 경우 Django의 모든 권한 부여
        if self.is_active and self.is_superuser:
            return True
        return False

    def has_module_perms(self, app_label):
        # 사용자가 superuser인 경우 모든 앱의 권한을 부여
        if self.is_active and self.is_superuser:
            return True
        return False

    class Meta:
        db_table = "user"


class Student(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "student"

    def __str__(self):
        return f"{self.user.name}"


class Instructor(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    experience = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "instructor"

    def __str__(self):
        return f"{self.user.name}"
