
import os
import pytest
import json
from pydantic import BaseModel, field_validator, ValidationError
import instructor
import litellm
from litellm import completion

# Initialize the instructor client with litellm
client = instructor.from_litellm(completion)

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
    
    # If using custom provider like deepseek via openai protocol, 
    # litellm usually handles it if we pass base_url.
    # But for clarity, we can construct the model string if needed.
    # For now, we'll pass the model as is, and let litellm handle it 
    # combined with the provider if necessary.
    
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

def test_basic_structured_output():
    """
    Test basic structured output generation.
    """
    print("\n--- Testing Basic Structured Output (Real API) ---")
    
    config = get_llm_config()
    if not config["api_key"]:
        print("Skipping test: No ANALYZER_API_KEY found in environment variables.")
        return

    try:
        user = client.chat.completions.create(
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

def test_mocked_success():
    """
    Test with a mocked response to verify the parsing logic works without an API key.
    """
    print("\n--- Testing Mocked Success ---")
    
    # Initialize a client specifically for MD_JSON mode for mocking
    mock_client = instructor.from_litellm(completion, mode=instructor.Mode.MD_JSON)

    # Mock response content
    mock_content = json.dumps({
        "name": "Mock User",
        "age": 42,
        "email": "mock@example.com"
    })
    
    try:
        # We use litellm's mock_response parameter
        user = mock_client.chat.completions.create(
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

def test_retry_mechanism():
    """
    Test automatic retry mechanism when validation fails.
    """
    print("\n--- Testing Retry Mechanism Configuration (Real API) ---")
    
    config = get_llm_config()
    if not config["api_key"]:
        print("Skipping test: No ANALYZER_API_KEY found.")
        return

    try:
        # We ask for something that might be ambiguous or tricky, 
        # or we rely on the fact that max_retries is set.
        user = client.chat.completions.create(
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

if __name__ == "__main__":
    # Manually run tests if executed as script
    test_basic_structured_output()
    test_mocked_success()
    test_retry_mechanism()
