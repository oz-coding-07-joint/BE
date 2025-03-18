import base64
import hashlib
import hmac
import os
import sys
from datetime import datetime, timezone

import django
import requests

# Django 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Django 환경 설정 수동 로드
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

# settings.base에서 직접 불러오기
from config.settings import base

# NCP Object Storage 설정
AWS_ACCESS_KEY_ID = base.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = base.AWS_SECRET_ACCESS_KEY
AWS_STORAGE_BUCKET_NAME = base.AWS_STORAGE_BUCKET_NAME
AWS_S3_ENDPOINT_URL = base.AWS_S3_ENDPOINT_URL.rstrip("/")
AWS_S3_REGION_NAME = base.AWS_S3_REGION_NAME


# 현재 날짜 (ISO 8601) - UTC 시간 적용
def get_amz_date():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def get_amz_date_short():
    return datetime.now(timezone.utc).strftime("%Y%m%d")


# AWS Signature v4 Key 생성
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key():
    date_stamp = get_amz_date_short()
    k_date = sign(("AWS4" + AWS_SECRET_ACCESS_KEY).encode("utf-8"), date_stamp)
    k_region = sign(k_date, AWS_S3_REGION_NAME)
    k_service = sign(k_region, "s3")
    k_signing = sign(k_service, "aws4_request")
    return k_signing


# XML 형태의 CORS 정책 생성
CORS_POLICY_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<CORSConfiguration>
    <CORSRule>
        <AllowedOrigin>https://umdoong.shop</AllowedOrigin>
        <AllowedOrigin>https://api.umdoong.shop</AllowedOrigin>
        <AllowedOrigin>http://localhost:8000</AllowedOrigin>
        <AllowedOrigin>http://localhost:3000</AllowedOrigin>
        <AllowedMethod>GET</AllowedMethod>
        <AllowedMethod>HEAD</AllowedMethod>
        <AllowedMethod>PUT</AllowedMethod>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedMethod>DELETE</AllowedMethod>
        <AllowedHeader>*</AllowedHeader>
        <ExposeHeader>ETag</ExposeHeader>
        <ExposeHeader>Access-Control-Allow-Origin</ExposeHeader>
        <MaxAgeSeconds>3000</MaxAgeSeconds>
    </CORSRule>
</CORSConfiguration>
"""


# Content-MD5 해시값 계산
def calculate_md5(data):
    md5_hash = hashlib.md5(data.encode("utf-8")).digest()
    return base64.b64encode(md5_hash).decode("utf-8")


content_md5 = calculate_md5(CORS_POLICY_XML)


# AWS Signature v4 서명 계산
def calculate_signature():
    amz_date = get_amz_date()
    amz_date_short = get_amz_date_short()
    canonical_uri = "/"  # 버킷 이름을 포함하지 않음
    canonical_querystring = "cors="  # CORS 정책 변경

    # Payload Hash (빈 본문에 대한 SHA-256 해시)
    payload_hash = hashlib.sha256(CORS_POLICY_XML.encode("utf-8")).hexdigest()

    # Canonical Headers & Signed Headers
    canonical_headers = (
        f"content-md5:{content_md5}\n"
        f"host:{AWS_STORAGE_BUCKET_NAME}.kr.object.ncloudstorage.com\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "content-md5;host;x-amz-content-sha256;x-amz-date"

    # Canonical Request 생성
    canonical_request = (
        f"PUT\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    )

    # String to Sign 생성
    string_to_sign = (
        f"AWS4-HMAC-SHA256\n"
        f"{amz_date}\n"
        f"{amz_date_short}/{AWS_S3_REGION_NAME}/s3/aws4_request\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    # 최종 서명 생성
    signature = hmac.new(get_signature_key(), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return signature


# 헤더 생성
amz_date = get_amz_date()
signature = calculate_signature()

headers = {
    "x-amz-date": amz_date,
    "x-amz-content-sha256": hashlib.sha256(CORS_POLICY_XML.encode("utf-8")).hexdigest(),
    "Authorization": f"AWS4-HMAC-SHA256 Credential={AWS_ACCESS_KEY_ID}/{get_amz_date_short()}/{AWS_S3_REGION_NAME}/s3/aws4_request, SignedHeaders=content-md5;host;x-amz-content-sha256;x-amz-date, Signature={signature}",
    "Content-Type": "application/xml",
    "Content-MD5": content_md5,
}

# API 요청 URL (CORS 설정)
url = f"https://{AWS_STORAGE_BUCKET_NAME}.kr.object.ncloudstorage.com/?cors"

# PUT 요청 보내기
response = requests.put(url, headers=headers, data=CORS_POLICY_XML)

# 결과 출력
if response.status_code == 200:
    print("Referrer 기반 CORS 설정 성공!")
else:
    print(f"설정 실패: {response.status_code} - {response.text}")
