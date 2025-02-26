import os
import csv
import requests
import random
import datetime
from slack_sdk import WebClient

# --- Slack 설정 ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
# Slack 채널 ID (예: "#lunch-recommendations" 또는 채널 ID)
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# --- Google 스프레드시트 설정 ---
# SPREADSHEET_CSV_URL: 스프레드시트를 '웹에 게시'하여 얻은 CSV URL
SPREADSHEET_CSV_URL = os.environ.get("SPREADSHEET_CSV_URL")

def get_restaurant_recommendations():
    """
    공개된 CSV 링크에서 데이터를 가져와 파싱한 후,
    평점이 2 초과인 항목만 필터링하고,
    무작위로 5~6곳을 추천합니다.
    
    CSV 파일은 다음 열을 포함해야 합니다:
      - 가게 이름
      - 종류
      - 대표 메뉴
      - 평점
      - 가격대
      - 소요시간(거리)
      - 메모
      - 지도 URL
    """
    response = requests.get(SPREADSHEET_CSV_URL)
    if response.status_code != 200:
        print("스프레드시트 CSV 데이터를 가져오지 못했습니다.")
        return []
    content = response.content.decode('utf-8')
    reader = csv.DictReader(content.splitlines())
    records = []
    for row in reader:
        # 각 키와 값의 양쪽 공백 제거
        rec = {k.strip(): v.strip() for k, v in row.items()}
        try:
            rating = float(rec.get("평점", "0"))
        except ValueError:
            rating = 0
        if rating > 2:
            records.append(rec)
    if not records:
        print("추천할 데이터가 없습니다. (평점 2 초과인 항목이 없습니다.)")
        return []
    count = random.choice([5, 6])
    return random.sample(records, min(len(records), count))

def create_slack_message(recommendations):
    """
    추천 맛집 목록과 유쾌한 멘트를 포함한 Slack 메시지를 생성합니다.
    헤더에는 오늘의 날짜(예: 2025년 1월 1일(월))가 포함됩니다.
    각 맛집 정보는 아래 항목들을 출력합니다:
      - 가게 이름, 종류, 대표 메뉴, 평점, 가격대, 소요시간(거리)
      - 메모
      - 지도 URL (메모 밑에 표시)
    """
    today = datetime.datetime.now()
    weekday_map = {0:"월", 1:"화", 2:"수", 3:"목", 4:"금", 5:"토", 6:"일"}
    formatted_date = f"{today.year}년 {today.month}월 {today.day}일({weekday_map[today.weekday()]})"
    
    message = f"*오늘의 점심 식당 추천 목록 ({formatted_date}):*\n"
    for rec in recommendations:
        try:
            store_name = rec["가게 이름"]
            store_type = rec["종류"]
            menu = rec["대표 메뉴"]
            rating = rec["평점"]
            price = rec["가격대"]
            duration = rec["소요시간(거리)"]
            memo = rec["메모"]
            map_url = rec["지도 URL"]
        except KeyError as e:
            print(f"CSV 행에 필요한 키가 없습니다: {e}")
            continue

        message += f":fork_and_knife: *{store_name}* ({store_type})\n"
        message += f"대표 메뉴: {menu} | 평점: {rating} | 가격대: {price} | 소요시간(거리): {duration}분\n"
        if memo:
            message += f"메모: {memo}\n"
        if map_url:
            message += f"지도: {map_url}\n"
        message += "\n"
    message += "점심시간이다! 오늘도 맛있는 한 끼로 기분 UP! :smile:"
    return message

def send_slack_message():
    recommendations = get_restaurant_recommendations()
    if not recommendations:
        print("추천할 맛집 데이터가 없습니다.")
        return
    message = create_slack_message(recommendations)
    try:
        response = slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
        print(f"{datetime.datetime.now()} - 메시지 전송 완료: {response['ok']}")
    except Exception as e:
        print(f"메시지 전송 실패: {e}")

if __name__ == "__main__":
    print("Slack 메시지 전송 시작!")
    send_slack_message()
