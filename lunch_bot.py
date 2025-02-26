import os
import csv
import requests
import random
import datetime
import schedule
import time
import threading
from slack_sdk import WebClient
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# --- 환경 변수 및 Slack 클라이언트 설정 ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
AUTO_CHANNEL = os.environ.get("AUTO_CHANNEL")  # 자동 메시지 전송용 채널 ID (설정하지 않으면 봇이 가입된 모든 채널로 전송)
SPREADSHEET_CSV_URL = os.environ.get("SPREADSHEET_CSV_URL")

# Slack Bolt 앱 생성
bolt_app = App(token=SLACK_BOT_TOKEN)
slack_client = bolt_app.client

# --- CSV 파일에서 맛집 추천 데이터 읽기 ---
def get_restaurant_recommendations():
    """
    공개된 CSV 링크에서 데이터를 가져와 파싱한 후,
    평점이 2 초과인 항목만 필터링하고 무작위로 5~6곳 추천.
    
    CSV 파일은 다음 열을 포함해야 합니다:
      - 가게 이름
      - 종류
      - 대표 메뉴
      - 평점
      - 가격대
      - 소요시간(거리)
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
        # 각 키와 값을 strip() 처리하여 BOM이나 불필요한 공백 제거
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

# --- Slack 메시지 생성 ---
def create_slack_message(recommendations):
    """
    추천 맛집 목록과 유쾌한 멘트를 포함한 Slack 메시지를 생성합니다.
    헤더에 오늘의 날짜(예: 2025년 1월 1일(월))를 포함합니다.
    """
    today = datetime.datetime.now()
    weekday_map = {0:"월", 1:"화", 2:"수", 3:"목", 4:"금", 5:"토", 6:"일"}
    formatted_date = f"{today.year}년 {today.month}월 {today.day}일({weekday_map[today.weekday()]})"
    
    message = f"*오늘의 점심 추천 목록 ({formatted_date}):*\n"
    for rec in recommendations:
        try:
            store_name = rec["가게 이름"]
            store_type = rec["종류"]
            menu = rec["대표 메뉴"]
            rating = rec["평점"]
            price = rec["가격대"]
            duration = rec["소요시간(거리)"]
            memo = rec["메모"]
        except KeyError as e:
            print(f"CSV 행에 필요한 키가 없습니다: {e}")
            continue

        message += f":fork_and_knife: *{store_name}* ({store_type})\n"
        message += f"대표 메뉴: {menu} | 평점: {rating} | 가격대: {price} | 소요시간(거리): {duration}분\n"
        if memo:
            message += f"메모: {memo}\n"
        message += "\n"
    message += "점심시간이다! 오늘도 맛있는 한 끼로 기분 UP! :smile:"
    return message

# --- Slack 메시지 전송 함수 ---
def send_slack_message_to_channel(channel):
    recommendations = get_restaurant_recommendations()
    if not recommendations:
        print("추천할 맛집이 없습니다. 스프레드시트 내용을 확인하세요!")
        return
    message = create_slack_message(recommendations)
    try:
        slack_client.chat_postMessage(channel=channel, text=message)
        print(f"{datetime.datetime.now()} - 메시지 전송 완료 in {channel}")
    except Exception as e:
        print(f"채널 {channel}에 메시지 전송 실패: {e}")

# --- 자동 메시지 스케줄링 ---
def scheduled_job():
    # 평일인지 확인
    if datetime.datetime.today().weekday() >= 5:
        print("오늘은 주말입니다. 자동 메시지를 전송하지 않습니다.")
        return
    if AUTO_CHANNEL:
        send_slack_message_to_channel(AUTO_CHANNEL)
    else:
        # AUTO_CHANNEL이 설정되지 않은 경우, 봇이 가입한 모든 채널에 전송
        conv_response = slack_client.conversations_list(types="public_channel,private_channel")
        channels = conv_response.get("channels", [])
        for channel in channels:
            if channel.get("is_member", False):
                send_slack_message_to_channel(channel["id"])

def run_schedule():
    schedule.every().monday.at("10:15").do(scheduled_job)
    schedule.every().tuesday.at("10:15").do(scheduled_job)
    schedule.every().wednesday.at("10:15").do(scheduled_job)
    schedule.every().thursday.at("10:15").do(scheduled_job)
    schedule.every().friday.at("10:15").do(scheduled_job)
    while True:
        schedule.run_pending()
        time.sleep(60)

# 백그라운드 스레드로 스케줄 실행
schedule_thread = threading.Thread(target=run_schedule, daemon=True)
schedule_thread.start()

# --- Slack 메시지 이벤트 처리 (명령어 "!점심폭격기") ---
@bolt_app.message("!점심폭격기")
def handle_command(message, say):
    recommendations = get_restaurant_recommendations()
    if not recommendations:
        say("추천할 맛집 정보가 없습니다. 스프레드시트 설정을 확인해주세요.")
        return
    msg = create_slack_message(recommendations)
    say(msg)

# --- Flask를 이용한 Slack 이벤트 수신 ---
flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    # Flask 서버 실행 (예: 포트 3000)
    flask_app.run(port=3000)
