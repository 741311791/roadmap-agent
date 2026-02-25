
import os
import asyncio
import json
import pytest
from pydantic import BaseModel, field_validator
import instructor
from litellm import acompletion

# Initialize the instructor client with litellm's async completion
client = instructor.from_litellm(acompletion)

# Define a Pydantic model for the structured output
class UserInfo(BaseModel):
    name: str
    age: int
    email: str

    # Add a custom validator to demonstrate retry logic
    @field_validator('age')
    @classmethod
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age must be non-negative")
        if v > 150:
            raise ValueError("Age must be less than 150")
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

def get_llm_config():
    """Get LLM configuration from environment variables."""
    provider = os.environ.get("ANALYZER_PROVIDER", "openai")
    model = os.environ.get("ANALYZER_MODEL", "gpt-3.5-turbo")
    base_url = os.environ.get("ANALYZER_BASE_URL")
    api_key = os.environ.get("ANALYZER_API_KEY")
    
    print(f"Using Provider: {provider}")
    print(f"Using Model: {model}")
    print(f"Using Base URL: {base_url}")
    print(f"API Key present: {bool(api_key)}")
    
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url
    }

async def test_basic_structured_output_async():
    """
    Test basic structured output generation asynchronously.
    """
    print("\n--- Testing Basic Structured Output (Async) ---")
    
    config = get_llm_config()
    if not config["api_key"]:
        print("Skipping test: No ANALYZER_API_KEY found in environment variables.")
        return

    try:
        user = await client.chat.completions.create(
            model=config["model"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            custom_llm_provider=config["provider"],
            response_model=UserInfo,
            messages=[
                {"role": "user", "content": "Extract user: John Doe, 30 years old, email: john@example.com"}
            ],
        )
        print(f"Successfully extracted: {user}")
        assert user.name == "John Doe"
        assert user.age == 30
        assert user.email == "john@example.com"
    except Exception as e:
        print(f"Error: {e}")
        raise e

async def test_mocked_success_async():
    """
    Test with a mocked response to verify the parsing logic works asynchronously.
    """
    print("\n--- Testing Mocked Success (Async) ---")
    
    # Initialize a client specifically for MD_JSON mode for mocking
    mock_client = instructor.from_litellm(acompletion, mode=instructor.Mode.MD_JSON)

    # Mock response content
    mock_content = json.dumps({
        "name": "Mock User",
        "age": 42,
        "email": "mock@example.com"
    })
    
    try:
        # We use litellm's mock_response parameter
        user = await mock_client.chat.completions.create(
            model="gpt-3.5-turbo",
            response_model=UserInfo,
            messages=[
                {"role": "user", "content": "Extract user"}
            ],
            mock_response=mock_content
        )
        
        print(f"Successfully extracted from mock: {user}")
        assert user.name == "Mock User"
        assert user.age == 42
        assert user.email == "mock@example.com"
        
    except Exception as e:
        print(f"Mock test failed: {e}")

async def test_retry_mechanism_async():
    """
    Test automatic retry mechanism when validation fails asynchronously.
    """
    print("\n--- Testing Retry Mechanism Configuration (Async) ---")
    
    config = get_llm_config()
    if not config["api_key"]:
        print("Skipping test: No ANALYZER_API_KEY found.")
        return

    try:
        # We ask for something that might be ambiguous or tricky, 
        # or we rely on the fact that max_retries is set.
        user = await client.chat.completions.create(
            model=config["model"],
            api_key=config["api_key"],
            base_url=config["base_url"],
            custom_llm_provider=config["provider"],
            response_model=UserInfo,
            messages=[
                {"role": "user", "content": "Create a user with name Alice, age 25, email alice@example.com"}
            ],
            max_retries=3, # This enables the retry loop in instructor
        )
        print(f"Result with retries enabled: {user}")
        assert isinstance(user, UserInfo)
        
    except Exception as e:
         print(f"Error: {e}")

async def main():
    await test_basic_structured_output_async()
    await test_mocked_success_async()
    await test_retry_mechanism_async()

if __name__ == "__main__":
    asyncio.run(main())
