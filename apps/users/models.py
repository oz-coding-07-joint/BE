from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django_softdelete.models import SoftDeleteManager, SoftDeleteModel

from apps.common.models import BaseModel


class UserManager(BaseUserManager, SoftDeleteManager):
    def active_user(self):
        return self.filter(is_active=True)

    def active_staff(self):
        return self.filter(is_staff=True, is_active=True)

    def withdraw_user(self):
        return self.filter(is_active=False, is_staff=False)

    def withdraw_staff(self):
        return self.filter(is_staff=True, is_active=False)

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("이메일 주소는 필수입니다.")
        if not password:
            raise ValueError("비밀번호는 필수입니다.")
        email = self.normalize_email(email)  # 이메일 정규화
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        # self._db는 UserManager에서 사용 중인 데이터베이스를 말함
        user.save(
            using=self._db
        )  # 다중 데이터 베이스를 사용하는 상황에서 정확히 지정해주기 위함이지만 단일에서도 관례적으로 사용
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(BaseModel, AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=30)
    nickname = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=130)
    provider = models.CharField(max_length=10, choices=[("LOCAL", "Local"), ("KAKAO", "Kakao")], default="LOCAL")
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
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "student"

    def __str__(self):
        return f"{self.user.name}"


class Instructor(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    experience = models.CharField(max_length=1000, null=True, blank=True)

    class Meta:
        db_table = "instructor"

    def __str__(self):
        return f"{self.user.name}"
