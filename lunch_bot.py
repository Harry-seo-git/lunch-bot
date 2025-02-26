import os
import csv
import requests
import random
import datetime
from slack_sdk import WebClient

# --- Slack 설정 ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# --- Google 스프레드시트 설정 ---
# SPREADSHEET_CSV_URL: 스프레드시트를 '웹에 게시'하여 얻은 CSV 링크
SPREADSHEET_CSV_URL = os.environ.get("SPREADSHEET_CSV_URL")

def get_restaurant_recommendations():
    """
    공개된 CSV 링크에서 데이터를 가져와 파싱한 후,
    맛집 리스트 중 평점이 2 초과인 항목만 필터링하고,
    무작위로 5~6곳을 추천합니다.
    
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
        # 평점이 2 초과인 항목만 포함
        if rating > 2:
            records.append(rec)
    if not records:
        print("추천할 데이터가 없습니다. (평점 2 초과인 항목이 없습니다.)")
        return []
    count = random.choice([5, 6])
    recommendations = random.sample(records, min(len(records), count))
    return recommendations

def create_slack_message(recommendations):
    """
    추천 맛집 목록과 유쾌한 멘트를 포함한 Slack 메시지 생성.
    헤더에는 오늘의 날짜(예: 2025년 1월 1일(월))도 포함됩니다.
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
            # "소요시간(거리)" 열을 읽어옴
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

def send_slack_message():
    # 평일(월~금)인 경우에만 실행 (토요일, 일요일 제외)
    if datetime.datetime.today().weekday() >= 5:
        print("오늘은 주말입니다. 메시지를 전송하지 않습니다.")
        return

    recommendations = get_restaurant_recommendations()
    if not recommendations:
        print("추천할 맛집이 없습니다. 스프레드시트 내용을 확인하세요!")
        return
    message = create_slack_message(recommendations)
    
    # 봇이 가입된 모든 채널에 메시지 전송
    conv_response = slack_client.conversations_list(types="public_channel,private_channel")
    channels = conv_response.get("channels", [])
    if not channels:
        print("봇이 가입된 채널이 없습니다.")
        return

    for channel in channels:
        if channel.get("is_member", False):  # 봇이 해당 채널의 멤버인지 확인
            channel_id = channel["id"]
            try:
                post_response = slack_client.chat_postMessage(channel=channel_id, text=message)
                print(f"메시지 전송 완료 in {channel.get('name', channel_id)}: {post_response['ok']}")
            except Exception as e:
                print(f"{channel.get('name', channel_id)} 채널에 메시지 전송 실패: {e}")

if __name__ == "__main__":
    print("Slack 메시지 전송 시작!")
    send_slack_message()
