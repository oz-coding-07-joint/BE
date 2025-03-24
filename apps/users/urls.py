from django.urls import path

from .views import (
    ChangePasswordView,
    KakaoAuthView,
    LoginView,
    LogoutView,
    MyinfoView,
    SendEmailVerificationCodeView,
    SignUpView,
    SocialSignupCompleteView,
    TokenRefreshView,
    VerifyEmailCodeView,
    WithdrawalView,
)

urlpatterns = [
    path("send-email-verification/", SendEmailVerificationCodeView.as_view(), name="send-email-verification"),
    path("verify-email-code/", VerifyEmailCodeView.as_view(), name="verify-email-code"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", LoginView.as_view(), name="login"),
    path("social-signup-complete/", SocialSignupCompleteView.as_view(), name="social-signup-complete"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("withdrawal/", WithdrawalView.as_view(), name="withdrawal"),
    path("myinfo/", MyinfoView.as_view(), name="myinfo"),
    path("password-change/", ChangePasswordView.as_view(), name="change-password"),
    path("token-refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("kakao-auth/", KakaoAuthView.as_view(), name="kakao-auth"),
]
