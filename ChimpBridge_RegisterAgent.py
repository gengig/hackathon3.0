import json
import boto3
import numpy as np
import faiss
import logging
from datetime import datetime
from botocore.exceptions import ClientError
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BRIDGE_TABLE_NAME = "ChimpBridge_AgentRegistry"
FAISS_BUCKET = "chimpbridge-faiss-indexes"
FAISS_KEY = "agent_vectors.index"

dynamodb = boto3.resource("dynamodb")
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
s3 = boto3.client("s3")
bridge_table = dynamodb.Table(BRIDGE_TABLE_NAME)

def get_text_embedding(text):
    try:
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            body=json.dumps({"inputText": text}),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response["body"].read())
        return np.array(result["embedding"], dtype=np.float32)
    except Exception as e:
        logger.error(f"Embedding error: {str(e)}")
        return None

def load_faiss_index():
    try:
        response = s3.get_object(Bucket=FAISS_BUCKET, Key=FAISS_KEY)
        index_data = response['Body'].read()
        
        with open('/tmp/temp_index.faiss', 'wb') as f:
            f.write(index_data)
        
        return faiss.read_index('/tmp/temp_index.faiss')
    except Exception as e:
        logger.info(f"Creating new FAISS index: {str(e)}")
        return faiss.IndexFlatIP(1536)

def save_faiss_index(index):
    try:
        faiss.write_index(index, '/tmp/temp_index.faiss')
        
        with open('/tmp/temp_index.faiss', 'rb') as f:
            s3.put_object(Bucket=FAISS_BUCKET, Key=FAISS_KEY, Body=f.read())
        
        return True
    except Exception as e:
        logger.error(f"Save index error: {str(e)}")
        return False

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        action = body.get("action", "register")
        
        if action == "register":
            client_id = body.get("ClientID")
            profile = body.get("Profile", {})
            
            if not client_id or not profile:
                return respond(400, "Missing ClientID or Profile")
            
            description = profile.get("Description", "")
            embedding = get_text_embedding(description)
            
            if embedding is None:
                return respond(500, "Failed to generate embedding")
            
            agent_data = {
                "AgentID": client_id,
                "Profile": profile,
                "Description": description,
                "Services": profile.get("Services", []),
                "Pricing": profile.get("Pricing", {}),
                "RegisteredAt": datetime.utcnow().isoformat(),
                "Status": "active"
            }
            
            bridge_table.put_item(Item=agent_data)
            
            # Update FAISS index
            index = load_faiss_index()
            index.add(embedding.reshape(1, -1))
            save_faiss_index(index)
            
            return respond(200, {
                "AgentID": client_id,
                "Status": "Registered in marketplace",
                "IndexSize": index.ntotal
            })
            
        elif action == "find_matches":
            client_id = body.get("ClientID")
            description = body.get("description", "")
            max_results = body.get("max_results", 5)
            
            if not client_id or not description:
                return respond(400, "Missing ClientID or description")
            
            query_embedding = get_text_embedding(description)
            if query_embedding is None:
                return respond(500, "Failed to generate query embedding")
            
            index = load_faiss_index()
            if index.ntotal == 0:
                return respond(200, {"Matches": [], "Message": "No agents in marketplace"})
            
            # Search for similar agents
            distances, indices = index.search(query_embedding.reshape(1, -1), min(max_results + 5, index.ntotal))
            
            # Get all registered agents
            response = bridge_table.scan()
            all_agents = response.get('Items', [])
            
            matches = []
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < len(all_agents):
                    agent = all_agents[idx]
                    
                    # Skip self-matches
                    if agent.get('AgentID') == client_id:
                        continue
                    
                    similarity = float(distance)
                    if similarity > 0.3:  # Minimum similarity threshold
                        match_data = {
                            "AgentID": agent.get('AgentID'),
                            "Description": agent.get('Description'),
                            "Services": agent.get('Services', []),
                            "Pricing": agent.get('Pricing', {}),
                            "Similarity": similarity,
                            "Endpoint": f"https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/default/ChimpBuddy_Broker?ClientID={agent.get('AgentID')}"
                        }
                        matches.append(match_data)
                
                if len(matches) >= max_results:
                    break
            
            return respond(200, {
                "ClientID": client_id,
                "Matches": matches,
                "TotalAgents": index.ntotal
            })
            
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