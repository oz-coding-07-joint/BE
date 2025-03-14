import base64
import hashlib
import hmac
import os
import time
import urllib.parse
import uuid

import redis


def generate_ncp_signed_url(object_name, chapter_video_id, expiration=120):
    """
    NCP Object Storage에서 Signed URL을 생성하는 함수.
    expiration: URL 만료 시간 (초) (기본값 2분)
    """
    access_key = os.getenv("NCP_ACCESS_KEY_ID")
    secret_key = os.getenv("NCP_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("NCP_BUCKET_NAME")
    endpoint = "https://kr.object.ncloudstorage.com"

    if not all([access_key, secret_key, bucket_name]):
        raise ValueError("NCP Object Storage 설정값이 없습니다.")

    # 만료 시간 설정 (Unix Timestamp)
    expires = int(time.time()) + expiration

    # 서명 생성
    string_to_sign = f"GET\n\n\n{expires}\n/{bucket_name}/{object_name}"
    signature = base64.b64encode(
        hmac.new(secret_key.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    ).decode("utf-8")

    # Signed URL 생성
    signed_url = f"{endpoint}/{bucket_name}/{object_name}?" + urllib.parse.urlencode(
        {"AWSAccessKeyId": access_key, "Expires": expires, "Signature": signature}
    )

    # Redis 키 설정
    redis_key = f"signed_url:{chapter_video_id}"  # ✅ chapter_video_id 기반으로 저장

    # ✅ 기존 Signed URL 즉시 삭제
    redis_client.delete(redis_key)

    # ✅ 새로운 Signed URL 저장 (2분 후 자동 만료)
    redis_client.setex(redis_key, expiration, signed_url)

    return signed_url


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

    # ✅ 올바른 경로 반환
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


redis_client = redis.StrictRedis(
    host=os.getenv("REDIS_HOST", "localhost"),  # 도커에서는 redis의 컨테이너 이름, 로컬에서는 localhost
    port=6379,
    db=0,
    decode_responses=True,  # 문자열 반환을 위해 decode_responses=True 설정
)
