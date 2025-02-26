import os
import csv
import requests
import random
import datetime
from slack_sdk import WebClient

# --- Slack 설정 ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#lunch-recommendations")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# --- Google 스프레드시트 설정 ---
# "웹에 게시"한 CSV 링크 (예: https://docs.google.com/spreadsheets/d/e/XXXXXXXXXXXX/pub?output=csv)
SPREADSHEET_CSV_URL = os.environ.get("SPREADSHEET_CSV_URL")

def get_restaurant_recommendations():
    """
    공개된 CSV 링크에서 데이터를 가져와 파싱한 후,
    맛집 리스트 중 무작위로 5~6곳을 추천합니다.
    CSV 파일은 다음 열을 포함해야 합니다:
      - 가게 이름
      - 종류
      - 대표 메뉴
      - 평점
      - 가격대
      - 메모
    """
    response = requests.get(SPREADSHEET_CSV_URL)
    if response.status_code != 200:
        print("스프레드시트 CSV 데이터를 가져오지 못했습니다.")
        return []
    content = response.content.decode('utf-8')
    reader = csv.DictReader(content.splitlines())
    records = []
    for row in reader:
        # 각 키를 strip() 처리하여 BOM이나 불필요한 공백 제거
        rec = {k.strip(): v for k, v in row.items()}
        records.append(rec)
    if not records:
        print("CSV 파일에 데이터가 없습니다.")
        return []
    count = random.choice([5, 6])
    recommendations = random.sample(records, min(len(records), count))
    return recommendations

def create_slack_message(recommendations):
    """
    추천 맛집 목록과 유쾌한 멘트를 포함한 Slack 메시지 생성
    """
    message = "*오늘의 점심 추천 목록:*\n"
    for rec in recommendations:
        try:
            store_name = rec["가게 이름"]
            store_type = rec["종류"]
            menu = rec["대표 메뉴"]
            rating = rec["평점"]
            price = rec["가격대"]
            memo = rec["메모"]
        except KeyError as e:
            print(f"CSV 행에 필요한 키가 없습니다: {e}")
            continue

        message += f":fork_and_knife: *{store_name}* ({store_type})\n"
        message += f"대표 메뉴: {menu} | 평점: {rating} | 가격대: {price}\n"
        if memo:
            message += f"메모: {memo}\n"
        message += "\n"
    message += "점심시간이다! 오늘도 맛있는 한 끼로 기분 UP! :smile:"
    return message

def send_slack_message():
    recommendations = get_restaurant_recommendations()
    if not recommendations:
        print("추천할 맛집이 없습니다. 스프레드시트 내용을 확인하세요!")
        return
    message = create_slack_message(recommendations)
    response = slack_client.chat_postMessage(channel=SLACK_CHANNEL, text=message)
    print(f"{datetime.datetime.now()} - 메시지 전송 완료: {response['ok']}")

if __name__ == "__main__":
    print("Slack 메시지 전송 시작!")
    send_slack_message()
