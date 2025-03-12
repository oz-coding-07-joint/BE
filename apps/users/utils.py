import requests


def get_kakao_user_data(access_token):
    url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()  # 사용자의 카카오 정보 반환
    return None  # 오류 처리
