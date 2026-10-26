# Live Weather Tool for a Strands Agent (AWS Lambda + Amazon Bedrock)

An AWS Weekend Challenge entry: take an agent and give it **one new tool** it did not have before.

## Before and after

| | Before | After |
|---|---|---|
| Agent | Strands Agents + Amazon Bedrock assistant, no tools | Same agent + `get_weather` tool |
| "Should I carry an umbrella in Lucknow right now?" | Guesses, or says it has no live data | Calls the tool and answers with real temperature, humidity and conditions |
| "Is Delhi hotter than Mumbai today?" | Cannot know | Fetches both cities and compares them |

## The new tool

A Python AWS Lambda function (`lambda_function.py`) that:

- accepts a city name (direct invoke, Function URL query string, or JSON body)
- calls the OpenWeatherMap current-weather API
- returns clean JSON: city, country, coordinates, condition, temperature, feels-like, humidity, pressure, wind, cloud cover
- handles errors and always returns JSON with a status code:

| Code | Meaning |
|---|---|
| 200 | Success |
| 400 | Missing `city` |
| 404 | City not found |
| 429 | Provider rate limit |
| 502 | API key rejected or invalid provider response |
| 504 | Network error or timeout |
| 500 | Unexpected error |

It uses only the Python standard library, so there is no layer or dependency packaging.

## How it plugs into the agent

```python
@tool
def get_weather(city: str) -> dict:
    """Get the current real-time weather for a city."""
    resp = lambda_client.invoke(
        FunctionName="weather-fetcher",
        Payload=json.dumps({"city": city}).encode("utf-8"),
    )
    result = json.loads(resp["Payload"].read())
    return {"status": result["statusCode"], **json.loads(result["body"])}

agent = Agent(model=model, tools=[get_weather])
```

The Strands `@tool` decorator exposes the function to the model, and the function invokes the Lambda with boto3. The same wrapper works for any custom Lambda logic: swap the function name and the docstring.

## Architecture

```
User question
     |
Strands Agent (Amazon Bedrock model)
     |  decides to call get_weather
     v
boto3 lambda.invoke
     v
AWS Lambda (weather-fetcher)
     v
OpenWeatherMap API
```

## Setup

1. Get a free API key from openweathermap.org.
2. Create a Lambda function (Python 3.12), paste in `lambda_function.py`, set the timeout to 10 seconds.
3. Add the environment variable `OPENWEATHER_API_KEY`. (For production, use AWS Secrets Manager.)
4. Test the function with `{"city": "Lucknow"}`.
5. Locally:

```bash
pip install strands-agents boto3
aws configure          # use the region where the Lambda lives
```

6. Edit `FUNCTION_NAME` and `MODEL_ID` in `weather_agent_local.py`. The IAM user needs `lambda:InvokeFunction` and Bedrock invoke permissions.

## Run the demo

```bash
python weather_agent_local.py before   # agent without the tool
python weather_agent_local.py after    # agent with the Lambda tool
```

## AWS services used

- AWS Lambda (the new tool)
- Amazon Bedrock (the agent's model)

## Notes

- City names can be ambiguous (for example, two cities named Gorakhpur in India). Use `City,CountryCode` or add lat/lon support for exact lookups.
- Never commit API keys or AWS credentials.

## Files

- `lambda_function.py`: the Lambda tool
- `weather_agent_local.py`: the agent, with `before` and `after` modes