"""
AWS Lambda Handler for Interview Assistant
Location: backend/lambda_handler.py

Uses Mangum to adapt FastAPI for Lambda + API Gateway
"""

import os
import json
import boto3
from mangum import Mangum

# Load secrets from Secrets Manager on cold start
def load_secrets():
    """Load API keys from Secrets Manager."""
    secrets_arn = os.environ.get('SECRETS_ARN')
    if not secrets_arn:
        return
    
    try:
        client = boto3.client('secretsmanager')
        response = client.get_secret_value(SecretId=secrets_arn)
        secrets = json.loads(response['SecretString'])
        
        # Set environment variables from secrets
        for key, value in secrets.items():
            if key != 'placeholder' and value:
                os.environ[key] = value
                
    except Exception as e:
        print(f"Warning: Could not load secrets: {e}")

# Load secrets on cold start
load_secrets()

# Import FastAPI app after setting environment variables
from app import app

# Create Mangum handler
handler = Mangum(
    app,
    lifespan="off",  # Lambda doesn't support lifespan
    api_gateway_base_path="/v1"  # Match API Gateway stage
)