"""
Azure OpenAI client configuration and utilities for the HF titration agent.
"""

import os
from typing import Optional
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()


class AzureOpenAIClient:
    """Azure OpenAI client wrapper."""
    
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        
        if not self.api_key or not self.endpoint:
            raise ValueError(
                "Azure OpenAI credentials not found. Please set AZURE_OPENAI_API_KEY "
                "and AZURE_OPENAI_ENDPOINT in .env file"
            )
        
        print(f"Initializing Azure OpenAI Client:")
        print(f"  Endpoint: {self.endpoint}")
        print(f"  Deployment: {self.deployment_name}")
        print(f"  API Version: {self.api_version}")
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
    
    def get_client(self):
        """Get the Azure OpenAI client."""
        return self.client
    
    def get_deployment_name(self):
        """Get the deployment name."""
        return self.deployment_name
    
    def test_connection(self):
        """Test the Azure OpenAI connection."""
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )
            print("✅ Azure OpenAI connection test successful!")
            return True
        except Exception as e:
            print(f"❌ Azure OpenAI connection test failed: {e}")
            return False


# Global client instance
_llm_client: Optional[AzureOpenAIClient] = None


def get_llm_client() -> AzureOpenAIClient:
    """Get or create the global LLM client instance."""
    global _llm_client
    if _llm_client is None:
        _llm_client = AzureOpenAIClient()
        # Test connection on first initialization
        _llm_client.test_connection()
    return _llm_client


def configure_agents_sdk():
    """Configure the OpenAI Agents SDK to use Azure OpenAI."""
    from agents import set_default_openai_client
    
    client = get_llm_client()
    
    # Set environment variables for OpenAI SDK to use Azure
    os.environ["OPENAI_API_TYPE"] = "azure"
    os.environ["OPENAI_API_KEY"] = client.api_key
    os.environ["OPENAI_API_VERSION"] = client.api_version
    os.environ["OPENAI_AZURE_ENDPOINT"] = client.endpoint
    os.environ["OPENAI_AZURE_DEPLOYMENT"] = client.deployment_name
    
    # Disable tracing
    os.environ["LANGSMITH_TRACING"] = "false"
    
    set_default_openai_client(client.get_client())
    print(f"🔧 Configured Agents SDK and environment for Azure OpenAI deployment: {client.get_deployment_name()}")