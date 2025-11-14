from fastapi import FastAPI, HTTPException
import requests
from datetime import datetime,timezone,timedelta
import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

app = FastAPI()
load_dotenv()

weather_key=os.getenv("WEATHER_API")
ai_key=os.getenv("HF_API")

def local_time(offset:int):
    tz=timezone(timedelta(seconds=offset))
    now=datetime.now(tz)
    return{
        "time_24h":now.strftime("%H:%M, %a, %d %b %y"),
        "time_12h":now.strftime("%I:%M %p %a, %d %b %y"),
    }


def format_time(time:int,offset:int):
    tz=timezone(timedelta(seconds=offset))
    local=datetime.fromtimestamp(time,tz)
    return{
        "time_24h":local.strftime("%H:%M"),
        "time_12h":local.strftime("%I:%M %p"),
    }

def ai_comment(weather):
    client = InferenceClient(
        api_key=ai_key,
    )

    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct:scaleway",
        messages=[
            {
                "role": "user",
                "content": f"Give a short one line tip for user based on weather {weather} remember to as colon : at the beginning of tip to differentiate it"
            }
        ],
    )

    comment = completion.choices[0].message.content

    if ":" in comment:
        comment = comment.split(":", 1)[-1]
    return comment.strip().strip('"')


@app.get("/weather/{city}")
def get_weather(city:str):
    url=f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_key}&units=metric"

    try:
        response = requests.get(url,timeout=5)
        response.raise_for_status()
        data=response.json()

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Weather service timed out")

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
    
    except requests.exceptions.JSONDecodeError:
        raise HTTPException(status_code=502, detail="Bad gateway: Invalid response form weather service.")




    if data.get("cod") != 200:
        raise HTTPException(status_code=data.get("cod",400),detail=data.get("message","Unknown error"))

    # return data

    main = data.get("main",{})
    sys = data.get("sys",{})
    weather = (data.get("weather") or [{}])[0]
    wind = data.get("wind",{})
    clouds = data.get("clouds",{})
    rain = data.get("rain",{})
    snow = data.get("snow",{})
    time_offset = data.get("timezone",0)

    return {
        "city" : data.get("name","Unknown"),
        "country" : sys.get("country",""),
        "main" : weather.get("main",""),
        "description" : weather.get("description",""),
        "icon" : weather.get("icon",""),
        "temp" : main.get("temp",0),
        "feels_like" : main.get("feels_like",0),
        "pressure" : main.get("pressure",0),
        "humidity" : main.get("humidity",0),
        "visibility" : data.get("visibility",0),
        "wind_speed" : wind.get("speed",0),
        "wind_dir" : wind.get("deg",0),
        "wind_gust" : wind.get("gust",0),
        "clouds" : clouds.get("all",0),
        "dt" : format_time(data.get("dt",0),time_offset),
        "sunrise" : format_time(sys.get("sunrise",0),time_offset),
        "sunset" : format_time(sys.get("sunset",0),time_offset),
        "current_time" : local_time(time_offset),
        "rain_1h" : rain.get("1h",0),
        "rain_3h" : rain.get("3h",0),
        "snow_1h" : snow.get("1h",0),
        "snow_3h" :snow.get("3h",0),
        "ai_comment":ai_comment(weather)
    }
