"""
AWS Lambda: fetch real-time weather for a city via OpenWeatherMap.

Runtime: Python 3.12 (no external dependencies, uses only the standard library)
Env vars: OPENWEATHER_API_KEY (required), UNITS (optional: metric | imperial | standard, default metric)

Accepted inputs:
  - Direct invoke / Strands agent:  {"city": "Lucknow"}  or  {"city": "Lucknow,IN"}
  - Function URL / API Gateway:     ?city=Lucknow  or JSON body {"city": "Lucknow"}
"""
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request

API_URL = "https://api.openweathermap.org/data/2.5/weather"
TIMEOUT_SECONDS = 5


def _response(status: int, payload: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def _extract_city(event: dict):
    """Pull the city out of whichever event shape we were given."""
    if not isinstance(event, dict):
        return None
    if event.get("city"):
        return str(event["city"]).strip()

    params = event.get("queryStringParameters") or {}
    if params.get("city"):
        return str(params["city"]).strip()

    body = event.get("body")
    if body:
        try:
            parsed = json.loads(body) if isinstance(body, str) else body
            if isinstance(parsed, dict) and parsed.get("city"):
                return str(parsed["city"]).strip()
        except json.JSONDecodeError:
            return None
    return None


def lambda_handler(event, context):
    city = _extract_city(event)
    if not city:
        return _response(400, {"error": "Missing required parameter: 'city'"})

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return _response(500, {"error": "Server misconfiguration: API key not set"})

    units = os.environ.get("UNITS", "metric")
    query = urllib.parse.urlencode({"q": city, "appid": api_key, "units": units})
    request = urllib.request.Request(f"{API_URL}?{query}", headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _response(404, {"error": f"City not found: '{city}'"})
        if e.code == 401:
            return _response(502, {"error": "Weather provider rejected the API key"})
        if e.code == 429:
            return _response(429, {"error": "Weather provider rate limit reached, try again later"})
        return _response(502, {"error": f"Weather provider error (HTTP {e.code})"})

    except (urllib.error.URLError, socket.timeout):
        return _response(504, {"error": "Could not reach weather provider (network or timeout)"})

    except json.JSONDecodeError:
        return _response(502, {"error": "Weather provider returned invalid JSON"})

    except Exception as e:  # last-resort guard so the caller always gets JSON
        print(f"Unexpected error: {e!r}")
        return _response(500, {"error": "Internal error"})

    temp_unit = {"metric": "°C", "imperial": "°F"}.get(units, "K")
    weather = (data.get("weather") or [{}])[0]
    main = data.get("main", {})
    wind = data.get("wind", {})

    result = {
        "city": data.get("name"),
        "country": data.get("sys", {}).get("country"),
        "coordinates": data.get("coord"),
        "condition": weather.get("main"),
        "description": weather.get("description"),
        "temperature": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "temp_unit": temp_unit,
        "humidity_percent": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "cloud_cover_percent": data.get("clouds", {}).get("all"),
        "observed_at_unix": data.get("dt"),
    }
    return _response(200, result)