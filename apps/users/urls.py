from django.urls import path

from .views import (
    ChangePasswordView,
    KakaoLoginView,
    LoginView,
    LogoutView,
    MyinfoView,
    SendEmailVerificationCodeView,
    SignUpView,
    SocialProfileCreate,
    TokenRefreshView,
    VerifyEmailCodeView,
    WithdrawalView,
)

urlpatterns = [
    path("send-email-verification/", SendEmailVerificationCodeView.as_view(), name="send-email-verification"),
    path("verify-email-code/", VerifyEmailCodeView.as_view(), name="verify-email-code"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("kakao-login/", KakaoLoginView.as_view(), name="kakao-login"),
    path("social-profile-create/", SocialProfileCreate.as_view(), name="social-profile-create"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdrawal/", WithdrawalView.as_view(), name="withdrawal"),
    path("myinfo/", MyinfoView.as_view(), name="myinfo"),
    path("password-change/", ChangePasswordView.as_view(), name="change-password"),
    path("token-refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
