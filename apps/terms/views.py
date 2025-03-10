from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Terms
from .serializers import TermsSerializer


class TermsView(APIView):
    """
    활성화 된 약관을 가져오는 API
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="약관 조회", description="약관의 내용을 확인할 수 있습니다", request=TermsSerializer, tags=["Terms"]
    )
    def get(self, request):
        terms = Terms.objects.filter(is_active=True)
        serializer = TermsSerializer(terms, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
