from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import TermsSerializer


class TermsView(APIView):

    @extend_schema(
        summary="약관 조회", description="약관의 내용을 확인할 수 있습니다", request=TermsSerializer, tags=["Terms"]
    )
    def get(self, request):
        return
