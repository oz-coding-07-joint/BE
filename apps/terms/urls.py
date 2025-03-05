from django.urls import path

from apps.terms.views import TermsView

urlpatterns = [
    path("", TermsView.as_view(), name="terms"),
]
