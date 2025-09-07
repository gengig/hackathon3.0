import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLES = ["ChimpBuddy_AgentRegistry", "ChimpBridge_AgentRegistry", "ChimpBuddy_Negotiations"]
FAISS_BUCKET = "chimpbridge-faiss-indexes"
FAISS_KEY = "agent_vectors.index"

def clear_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response.get('Items', [])
        
        if not items:
            return {"table": table_name, "status": "empty", "count": 0}
            
        with table.batch_writer() as batch:
            for item in items:
                if 'NegotiationID' in item:
                    key = {'NegotiationID': item['NegotiationID']}
                elif 'ClientID' in item:
                    key = {'ClientID': item['ClientID']}
                elif 'AgentID' in item:
                    key = {'AgentID': item['AgentID']}
                else:
                    continue
                batch.delete_item(Key=key)
        
        return {"table": table_name, "status": "cleared", "count": len(items)}
    except Exception as e:
        return {"table": table_name, "status": "error", "error": str(e)}

def clear_faiss():
    try:
        s3.delete_object(Bucket=FAISS_BUCKET, Key=FAISS_KEY)
        return {"faiss": "deleted"}
    except s3.exceptions.NoSuchKey:
        return {"faiss": "empty"}
    except s3.exceptions.NoSuchBucket:
        return {"faiss": "bucket_not_exists"}
    except Exception as e:
        return {"faiss": "error", "error": str(e)}

def lambda_handler(event, context):
    logger.info("🔄 ChimpBridge Demo Reset Started")
    
    results = {
        "status": "success", 
        "message": "ChimpBridge AI Agent Marketplace Reset Complete", 
        "tables": [], 
        "faiss": {}
    }
    
    # Clear DynamoDB tables
    for table in TABLES:
        results["tables"].append(clear_table(table))
    
    # Clear FAISS index
    results["faiss"] = clear_faiss()
    
    logger.info(f"Reset results: {results}")
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json", 
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(results, indent=2)
    }