import discord
import requests
import asyncio
import os
from datetime import datetime, timedelta

# discordbotのトークン
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
#メッセージを送信するチャンネルID
CHANNEL_ID = os.environ["CHANNEL_ID"]

# APIのエンドポイント
API_URL = os.environ["API_URL"]

# 送信する時間 下記の場合　毎日0時0分0秒に送信
SEND_HOUR = 0
# 時間をグリニッジ標準時に合わせる
SEND_HOUR -= 9
if SEND_HOUR < 0:
    SEND_HOUR += 24
SEND_MINUTE = 0
SEND_SECOND = 0


intents = discord.Intents.default()
client = discord.Client(intents=intents)

async def fetch_api_data():
    response = requests.get(API_URL)
    data = response.json()
    return data

async def Arrange_Data(data):
    # 複数の地点のデータが欲しい場合、first_locateをコピーして、second_locateを作ってください。
    # この際,data[0]をdata[1]に変更してください。
    first_locate = {
        "地点": os.environ["FIRST_LOCATE"],
        "最高気温": data[0]["daily"]["temperature_2m_max"][0],
        "最低気温": data[0]["daily"]["temperature_2m_min"][0],
        "降水時間帯": [],
    }

    for i in range(len(data[0]["hourly"]["precipitation_probability"])):
        
        if data[0]["hourly"]["precipitation_probability"][i] > 0.0:
            first_locate["降水時間帯"].append(f"{i}:00")            
            
            
    data = [first_locate]
    return data

async def send_message(channel, data):
    message = "今日の天気:\n"
    for d in data:
        message += f"{d['地点']}\n"
        message += f"最高気温 : {d['最高気温']}度\n"
        message += f"最低気温 : {d['最低気温']}度\n"
        message += f"降水時間帯 : {', '.join(d['降水時間帯'])}\n\n"
    # discordのメッセージは2000文字までなので、それを超える場合は...で省略する
    if len(message) > 2000:
        message = message[:1990] + "..."
    await channel.send(message)

async def scheduled_task():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    
    while not client.is_closed():
        now = datetime.now()
        target_time = now.replace(hour=SEND_HOUR, minute=SEND_MINUTE, second=SEND_SECOND, microsecond=0)
        
        # 現在時刻が指定時刻より大きい場合
        if now > target_time:
            target_time += timedelta(days=1)
            
        # タスクの実行にかかる時間を考慮して，少し早めに起動する
        buffer_time = timedelta(seconds=10)
        start_time = target_time - buffer_time
            
        # 送信時刻まで待機
        wait_time = (start_time - now).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
        
        #実行
        
        if now == target_time:
            data = await fetch_api_data()
            data = await Arrange_Data(data)
            await send_message(channel, data)
        
        # 翌日の送信時刻まで待機
        next_send_time = datetime.now() + timedelta(days=1)
        next_send_time = next_send_time.replace(hour=SEND_HOUR, minute=0, second=0, microsecond=0)
        sleep_duration = (next_send_time - datetime.now() - buffer_time).total_seconds()
        await asyncio.sleep(sleep_duration)

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")
    client.loop.create_task(scheduled_task())
    
client.run(DISCORD_TOKEN)
