import os
import csv
import requests
import random
import datetime
from slack_sdk import WebClient

# --- Slack 설정 ---
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
# 메시지를 전송할 채널 ID (예: "#lunch-recommendations" 또는 해당 채널의 ID)
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL")
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# --- Google 스프레드시트 설정 ---
# SPREADSHEET_CSV_URL: 스프레드시트를 '웹에 게시'하여 얻은 CSV URL
SPREADSHEET_CSV_URL = os.environ.get("SPREADSHEET_CSV_URL")

def get_restaurant_recommendations():
    """
    CSV 링크에서 데이터를 가져와 파싱한 후,
    평점이 2 초과인 항목만 필터링하고,
    무작위로 5~6곳을 추천합니다.
    
    CSV 파일은 아래 열을 포함해야 합니다:
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
        # 키와 값의 불필요한 공백 제거
        rec = {k.strip(): v.strip() for k, v in row.items()}
        try:
            rating = float(rec.get("평점", "0"))
        except ValueError:
            rating = 0
        if rating > 2:
            records.append(rec)
    if not records:
        print("추천할 데이터가 없습니다. (평점 2 초과 항목이 없습니다.)")
        return []
    count = random.choice([5, 6])
    return random.sample(records, min(len(records), count))

def create_slack_message(recommendations):
    """
    추천 맛집 목록과 유쾌한 멘트를 포함한 Slack 메시지를 생성합니다.
    헤더에는 오늘의 날짜(예: 2025년 1월 1일(월))가 포함됩니다.
    각 맛집 정보에는:
      - 가게 이름, 종류, 대표 메뉴, 평점, 가격대, 소요시간(거리)
      - 메모 (출력)
      - 지도 URL (메모 밑에 출력)
    """
    today = datetime.datetime.now()
    weekday_map = {0:"월", 1:"화", 2:"수", 3:"목", 4:"금", 5:"토", 6:"일"}
    formatted_date = f"{today.year}년 {today.month}월 {today.day}일({weekday_map[today.weekday()]})"
    
    message = f"*오늘의 점심 추천 목록 ({formatted_date}):*\n"
    for rec in get_restaurant_recommendations():
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
    # 아래 메시지는 최강욱 셰프 스타일의 톤으로 작성된 예시 (여러 개 중 랜덤 선택도 가능)
    chef_messages = [
        "자, 여러분! 이제 점심시간입니다. 오늘의 메뉴는 단순한 식사가 아니라, 감동을 선사할 요리의 예술입니다. 한 입 베어 물면 그 풍미에 감탄할 것입니다. 최고의 점심을 즐기세요! :fire:",
        "이제 점심입니다, 여러분! 오늘의 메뉴는 정성과 열정이 빚어낸 걸작입니다. 한 입 맛보면 요리의 진수를 느끼실 겁니다. 준비되셨나요? :chef:",
        "여러분, 점심 시간이 다가왔습니다. 오늘의 요리는 감탄을 자아내는 예술작품입니다. 한 입 베어 물면 여러분의 미각이 황홀경에 빠질 것입니다. 지금 바로 즐겨보세요! :sunglasses:"
    ]
    message += random.choice(chef_messages)
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
