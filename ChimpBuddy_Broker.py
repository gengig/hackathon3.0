import json
import boto3
import uuid
import os
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_TABLE_NAME = "ChimpBuddy_AgentRegistry"
NEGOTIATION_TABLE_NAME = "ChimpBuddy_Negotiations"

dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
agent_table = dynamodb.Table(AGENT_TABLE_NAME)
negotiation_table = dynamodb.Table(NEGOTIATION_TABLE_NAME)

def get_agent_profile(client_id):
    try:
        response = agent_table.get_item(Key={"ClientID": client_id})
        if 'Item' in response:
            return response['Item']
        return None
    except ClientError as e:
        logger.error(f"Error fetching agent profile: {str(e)}")
        return None

def get_negotiation_history(negotiation_id):
    try:
        response = negotiation_table.get_item(Key={"NegotiationID": negotiation_id})
        if 'Item' in response:
            return response['Item']
        return None
    except ClientError as e:
        logger.error(f"Error fetching negotiation: {str(e)}")
        return None

def save_negotiation_state(negotiation_data):
    try:
        negotiation_table.put_item(Item=negotiation_data)
    except ClientError as e:
        logger.error(f"Error saving negotiation: {str(e)}")

def generate_smart_opening(buyer_profile, seller_profile, agent_role):
    try:
        if agent_role == "seller":
            prompt = f"""You are an AI buyer agent analyzing a seller's profile to craft the perfect opening negotiation message.

BUYER PROFILE (You):
- Description: {buyer_profile.get('description', '')}
- Budget: {buyer_profile.get('budget', {})}
- Preferences: {buyer_profile.get('preferences', '')}

SELLER PROFILE (Target):
- Description: {seller_profile.get('description', '')}
- Pricing: {seller_profile.get('pricing', {})}
- Services: {seller_profile.get('services', [])}

Craft an intelligent opening message that:
- Shows you understand their offering
- Mentions specific details from their description
- Presents your budget/needs strategically
- Sets up for productive negotiation

Return ONLY the opening message text (no JSON, no quotes):"""
        else:
            prompt = f"""Generate a seller opening message based on buyer interest.
Buyer: {buyer_profile.get('description', '')}
Your offering: {seller_profile.get('description', '')}

Return ONLY the opening message text:"""

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.8
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response["body"].read())
        opening_message = result["content"][0]["text"].strip()
        logger.info(f"AI generated opening: {opening_message}")
        return opening_message
        
    except Exception as e:
        logger.error(f"Error generating smart opening: {str(e)}")
        return "I'm interested in your tickets and would like to discuss pricing."

def negotiate_with_claude(agent_profile, negotiation_history, incoming_message, agent_role):
    try:
        agent_name = agent_profile['Profile'].get('Name', agent_profile['ClientID'])
        agent_description = agent_profile['Profile'].get('Description', '')
        pricing = agent_profile['Profile'].get('Pricing', {})
        
        history_context = ""
        if negotiation_history and 'Messages' in negotiation_history:
            history_context = "\n".join([
                f"{msg['Role']}: {msg['Content']}" 
                for msg in negotiation_history['Messages'][-5:]
            ])

        if agent_role == "seller":
            prompt = f"""You are {agent_name}, an AI agent selling tickets. Here's your profile:

Description: {agent_description}
Your Pricing: {pricing}

NEGOTIATION HISTORY:
{history_context}

INCOMING MESSAGE FROM BUYER:
{incoming_message}

As a seller, you should:
- Try to get a fair price for your tickets
- Highlight the value (Section 108, center ice, unobstructed view)
- Be willing to negotiate but don't go too low
- Accept reasonable offers
- Be professional and friendly

Respond with ONLY a JSON object:
{{
  "response": "Your negotiation response",
  "action": "counter|accept|reject",
  "price_per_ticket": 275,
  "reasoning": "Why you made this decision"
}}"""
        else:
            prompt = f"""You are {agent_name}, an AI agent buying tickets. Here's your profile:

Description: {agent_description}
Your Budget: {pricing}

NEGOTIATION HISTORY:
{history_context}

INCOMING MESSAGE FROM SELLER:
{incoming_message}

As a buyer, you should:
- Try to get a good deal within your budget
- Be interested but price-conscious
- Make reasonable counter-offers
- Accept good deals
- Be professional and friendly

Respond with ONLY a JSON object:
{{
  "response": "Your negotiation response",
  "action": "counter|accept|reject",
  "price_per_ticket": 250,
  "reasoning": "Why you made this decision"
}}"""

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "temperature": 0.7
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        result = json.loads(response["body"].read())
        ai_response = result["content"][0]["text"].strip()
        
        import re
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            negotiation_response = json.loads(json_match.group())
            logger.info(f"Claude negotiation response: {negotiation_response}")
            return negotiation_response
        else:
            logger.warning(f"Could not extract JSON from Claude response: {ai_response}")
            return {
                "response": "I'm interested in discussing this further.",
                "action": "counter",
                "price_per_ticket": 250,
                "reasoning": "Fallback response"
            }
            
    except Exception as e:
        logger.error(f"Error in Claude negotiation: {str(e)}")
        return {
            "response": "I'm having trouble processing your request right now.",
            "action": "counter", 
            "price_per_ticket": 250,
            "reasoning": f"Error: {str(e)}"
        }

def lambda_handler(event, context):
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        client_id = query_params.get('ClientID')
        
        if not client_id:
            return respond(400, "Missing ClientID parameter")

        body = json.loads(event.get("body", "{}"))
        agent_profile = get_agent_profile(client_id)
        if not agent_profile:
            return respond(404, f"Agent {client_id} not found")

        agent_role = "buyer" if client_id.endswith("_buyer") else "seller"
        action = body.get("action", "negotiate")
        
        if action == "initiate" or action == "initiate_smart":
            negotiation_id = str(uuid.uuid4())
            
            if action == "initiate_smart":
                buyer_profile = body.get("buyer_profile", {})
                seller_profile = body.get("seller_profile", {})
                incoming_message = generate_smart_opening(buyer_profile, seller_profile, agent_role)
            else:
                incoming_message = body.get("message", "I'm interested in your offering.")
            
            negotiation_response = negotiate_with_claude(
                agent_profile, None, incoming_message, agent_role
            )
            
            negotiation_data = {
                "NegotiationID": negotiation_id,
                "Participants": [client_id, body.get("counterpart_id", "unknown")],
                "Status": "active",
                "Messages": [
                    {
                        "Role": "initiator",
                        "Content": incoming_message,
                        "Timestamp": datetime.utcnow().isoformat()
                    },
                    {
                        "Role": agent_role,
                        "Content": negotiation_response["response"],
                        "Timestamp": datetime.utcnow().isoformat()
                    }
                ],
                "CreatedAt": datetime.utcnow().isoformat(),
                "UpdatedAt": datetime.utcnow().isoformat()
            }
            
            save_negotiation_state(negotiation_data)
            
            return respond(200, {
                "negotiation_id": negotiation_id,
                "response": negotiation_response["response"],
                "action": negotiation_response["action"],
                "price_per_ticket": negotiation_response["price_per_ticket"],
                "reasoning": negotiation_response["reasoning"]
            })
            
        elif action == "negotiate":
            negotiation_id = body.get("negotiation_id")
            incoming_message = body.get("message", "")
            
            if not negotiation_id or not incoming_message:
                return respond(400, "Missing negotiation_id or message")
            
            negotiation_history = get_negotiation_history(negotiation_id)
            if not negotiation_history:
                return respond(404, "Negotiation not found")
            
            negotiation_response = negotiate_with_claude(
                agent_profile, negotiation_history, incoming_message, agent_role
            )
            
            new_messages = negotiation_history.get("Messages", []) + [
                {
                    "Role": "counterpart",
                    "Content": incoming_message,
                    "Timestamp": datetime.utcnow().isoformat()
                },
                {
                    "Role": agent_role,
                    "Content": negotiation_response["response"],
                    "Timestamp": datetime.utcnow().isoformat()
                }
            ]
            
            negotiation_history["Messages"] = new_messages
            negotiation_history["UpdatedAt"] = datetime.utcnow().isoformat()
            
            if negotiation_response["action"] in ["accept", "reject"]:
                negotiation_history["Status"] = "completed"
            
            save_negotiation_state(negotiation_history)
            
            return respond(200, {
                "negotiation_id": negotiation_id,
                "response": negotiation_response["response"],
                "action": negotiation_response["action"],
                "price_per_ticket": negotiation_response["price_per_ticket"],
                "reasoning": negotiation_response["reasoning"]
            })
            
        else:
            return respond(400, f"Unknown action: {action}")
            
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
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