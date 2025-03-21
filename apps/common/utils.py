import os
import uuid

import boto3
import redis
from django.conf import settings


def generate_ncp_signed_url(object_key, expiration=60 * 30):
    """
    NCP Object Storage용 Signed URL 생성 함수

    :param object_key: 접근하려는 파일의 경로
    :param expiration: Signed URL 유효 시간 (초 단위)
    :return: Signed URL (유효 시간 동안만 접근 가능)
    """
    if not object_key:
        return None

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME

    # Signed URL 생성
    signed_url = s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": bucket_name,
            "Key": object_key,
            "ResponseContentType": "video/mp4",  # 파일 유형 설정 (필요시)
            "ResponseCacheControl": "no-cache",  # 캐시 방지
        },
        ExpiresIn=expiration,
        HttpMethod="GET",
    )

    return signed_url


def generate_material_signed_url(object_key, expiration=300, original_filename=None):
    """
    NCP Object Storage용 학습 자료 다운로드 Signed URL 생성
    :param object_key: 파일 경로
    :param expiration: URL 유효 시간 (초 단위, 기본 5분)
    :return: Signed URL (유효 시간 동안만 접근 가능)
    """
    if not object_key:
        return None

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        bucket_name = settings.AWS_STORAGE_BUCKET_NAME

        object_key = object_key.replace(settings.MEDIA_URL, "").lstrip("/")

        filename = original_filename or os.path.basename(object_key)

        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": object_key,
                "ResponseContentType": "application/octet-stream",  #  브라우저가 파일을 무조건 다운로드하도록 지시하는 binary type
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
                "ResponseCacheControl": "no-cache",
            },
            ExpiresIn=expiration,
            HttpMethod="GET",
        )

        return signed_url

    except Exception as e:
        return None  # 오류 발생 시 None 반환


def generate_unique_filename(filename):
    """UUID + 원본 파일명 + 확장자로 파일명 생성하는 함수"""
    name, ext = os.path.splitext(filename)  # 파일명과 확장자 분리
    return f"{name}_{uuid.uuid4()}{ext}"  # UUID + 원본 파일명 + 확장자


def class_lecture_file_path(instance, filename):
    """썸네일, 학습자료, 강의영상 파일을 동일한 경로에 저장"""

    from apps.courses.models import ChapterVideo, Lecture, LectureChapter

    unique_filename = generate_unique_filename(filename)

    # Lecture 모델 (썸네일 저장)
    if isinstance(instance, Lecture):
        file_type = "thumbnails"
        course_id = instance.course.id
        lecture_id = instance.id

    # LectureChapter 모델 (학습자료 저장)
    elif isinstance(instance, LectureChapter):
        file_type = "materials"
        course_id = instance.lecture.course.id
        lecture_id = instance.lecture.id

    # ChapterVideo 모델 (강의 영상 저장)
    elif isinstance(instance, ChapterVideo):
        file_type = "videos"
        course_id = instance.lecture_chapter.lecture.course.id
        lecture_id = instance.lecture_chapter.lecture.id

    else:
        raise ValueError(f"지원되지 않는 모델 유형입니다: {type(instance).__name__}")

    # 올바른 경로 반환
    return f"classes/{course_id}/lectures/{lecture_id}/{file_type}_{unique_filename}"


def assignment_material_path(instance, filename):
    """과제 자료 저장 경로 생성 함수"""
    unique_filename = generate_unique_filename(filename)

    # instance는 이미 Assignment 인스턴스이므로, pk가 있다면 사용, 없다면 'new'로 처리
    assignment_pk = instance.pk if instance.pk else "new"

    try:
        # Lecture 정보를 통해 강의(클래스) 식별자(course_id)를 가져옵니다.
        course_id = instance.chapter_video.lecture_chapter.lecture.course_id
    except AttributeError:
        course_id = "default"

    return f"classes/{course_id}/assignments/{assignment_pk}/assignment_materials/{unique_filename}"


def assignment_comment_file_path(instance, filename):
    """학생 제출 파일과 강사 피드백 파일을 구분하여 저장 경로 설정"""
    if not instance.assignment or not instance.assignment.pk:
        raise ValueError("Assignment 정보가 없어서 파일 경로를 생성할 수 없습니다.")

    unique_filename = generate_unique_filename(filename)

    is_instructor = hasattr(instance.user, "instructor")

    # 파일 저장 경로 설정
    base_path = f"classes/{instance.assignment.chapter_video.lecture_chapter.lecture.course_id}/assignments/{instance.assignment.pk}"
    folder = "feedbacks" if is_instructor else "submissions"

    return f"{base_path}/{folder}/{unique_filename}"


def delete_file_from_ncp(file_path):
    """NCP Object Storage에서 파일 삭제"""
    if not file_path:
        return

    s3_client = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    object_key = file_path.replace(settings.MEDIA_URL, "").lstrip("/")

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        print(f"Deleted from NCP Storage: {object_key}")
    except Exception as e:
        print(f"Error deleting file from NCP: {e}")


redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST"),
    port=6379,
    db=0,
    decode_responses=True,  # 문자열 반환을 위해 decode_responses=True 설정
)
