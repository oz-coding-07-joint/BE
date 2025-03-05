from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    ChangePasswordView,
    KakaoLoginView,
    LoginView,
    LogoutView,
    MyinfoView,
    SignUpView,
    Social_profile_create,
    WithdrawalView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("kakao-login/", KakaoLoginView.as_view(), name="kakao-login"),
    path("social-profile-create/", Social_profile_create.as_view(), name="social-profile-create"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdrawal/", WithdrawalView.as_view(), name="withdrawal"),
    path("myinfo/", MyinfoView.as_view(), name="myinfo"),
    path("password-change/", ChangePasswordView.as_view(), name="change-password"),
    path("token-refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
