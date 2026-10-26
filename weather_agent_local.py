"""
Strands agent + Lambda weather tool, configured for ap-southeast-2 and run from a laptop.

pip install strands-agents boto3
aws configure   (region: ap-southeast-2)

Usage:
  python weather_agent_local.py before   # agent WITHOUT the tool
  python weather_agent_local.py after    # agent WITH the Lambda tool
"""
import json
import sys

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

REGION = "ap-southeast-2"
FUNCTION_NAME = "weather-fetcher"  # change to your Lambda's exact name
MODEL_ID = "apac.anthropic.claude-sonnet-4-20250514-v1:0"  # replace with an inference profile ID from your Bedrock console

lambda_client = boto3.client("lambda", region_name=REGION)
model = BedrockModel(model_id=MODEL_ID, region_name=REGION)

QUESTION = "Should I carry an umbrella in Lucknow right now? Also, is Delhi hotter than Mumbai today?"


@tool
def get_weather(city: str) -> dict:
    """Get the current real-time weather for a city (e.g. 'Lucknow' or 'London,GB')."""
    resp = lambda_client.invoke(
        FunctionName=FUNCTION_NAME,
        Payload=json.dumps({"city": city}).encode("utf-8"),
    )
    result = json.loads(resp["Payload"].read())
    return {"status": result["statusCode"], **json.loads(result["body"])}


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "after"

    if mode == "before":
        agent = Agent(model=model)  # no tools: it can only guess
    else:
        agent = Agent(
            model=model,
            tools=[get_weather],
            system_prompt="You are a helpful assistant. Use get_weather for any question about current weather.",
        )

    agent(QUESTION)