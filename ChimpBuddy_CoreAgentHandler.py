import json
import boto3
import uuid
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_TABLE_NAME = "ChimpBuddy_AgentRegistry"
BRIDGE_ENDPOINT = "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/default/ChimpBridge_RegisterAgent"

dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
agent_table = dynamodb.Table(AGENT_TABLE_NAME)

def extract_profile_with_ai(description):
    try:
        prompt = f"""Extract structured information from this agent description:

"{description}"

Return ONLY a JSON object with these fields:
{{
  "Name": "extracted name or generate one",
  "Description": "clean description", 
  "Services": ["list", "of", "services"],
  "Pricing": {{"Min": 200, "Max": 400}},
  "Location": "extracted location",
  "ContactInfo": "extracted contact or generate"
}}"""

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.3
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response["body"].read())
        ai_response = result["content"][0]["text"].strip()
        
        import re
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        
        return None
    except Exception as e:
        logger.error(f"AI extraction error: {str(e)}")
        return None

def register_with_bridge(client_id, profile):
    try:
        import requests
        payload = {"ClientID": client_id, "Profile": profile}
        response = requests.post(BRIDGE_ENDPOINT, 
                               headers={"Content-Type": "application/json"},
                               data=json.dumps(payload, default=decimal_default))
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Bridge registration error: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        client_id = query_params.get('ClientID')
        
        if not client_id:
            return respond(400, "Missing ClientID parameter")

        body = json.loads(event.get("body", "{}"))
        action = body.get("action", "get")
        
        if action == "create":
            description = body.get("description", "")
            if not description:
                return respond(400, "Missing description")
            
            extracted_profile = extract_profile_with_ai(description)
            if not extracted_profile:
                return respond(500, "Failed to extract profile")
            
            agent_data = {
                "ClientID": client_id,
                "Profile": extracted_profile,
                "RawDescription": description,
                "CreatedAt": datetime.utcnow().isoformat(),
                "Status": "active"
            }
            
            agent_table.put_item(Item=agent_data)
            
            # Auto-register with ChimpBridge
            bridge_registered = register_with_bridge(client_id, extracted_profile)
            
            return respond(200, {
                "ClientID": client_id,
                "ExtractedProfile": extracted_profile,
                "BridgeRegistered": bridge_registered,
                "Status": "Profile created and registered"
            })
            
        elif action == "get":
            response = agent_table.get_item(Key={"ClientID": client_id})
            if 'Item' in response:
                return respond(200, response['Item'])
            else:
                return respond(404, "Agent not found")
                
        else:
            return respond(400, f"Unknown action: {action}")
            
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        return respond(500, f"Internal server error: {str(e)}")

def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=decimal_default)
    }

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError