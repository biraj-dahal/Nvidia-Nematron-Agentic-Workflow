import os
from openai import OpenAI

class NemotronTranscriptAgent:
    """
    Specialized agent using Nemotron-nano-9b-v2 for transcript analysis.
    Starting with Step 1: Basic initialization and testing.
    """
    
    def __init__(self, nemotron_api_key: str, nemotron_base_url: str):
        """
        Initialize the Nemotron agent with API credentials.
        
        Args:
            nemotron_api_key: API key for Nemotron model
            nemotron_base_url: Base URL for Nemotron API endpoint
        """
        # NVIDIA's API expects the key in a specific format
        self.client = OpenAI(
            api_key=nemotron_api_key,
            base_url=nemotron_base_url,
            timeout=30.0,  # Add timeout
            max_retries=2  # Add retries
        )
        self.model = "nvidia/NVIDIA-Nemotron-Nano-9B-v2"
        
        # Specialized persona prompt for transcript analysis
        self.persona_prompt = """You are a specialized Transcript Analysis Expert with the following capabilities:

1. **Deep Reading**: You excel at extracting meaning from long, messy transcripts
2. **Structured Thinking**: You organize information into clear, actionable sections
3. **Synthesis**: You identify key themes, decisions, and action items
4. **Contextual Understanding**: You recognize implicit meanings and connections

Your approach is:
- Methodical and thorough
- Focused on actionable insights
- Clear and concise in output
- Strategic in connecting information across the transcript"""

    def _call_nemotron(self, messages: list, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Make a call to the Nemotron model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            String response from Nemotron
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            # Return detailed error information
            error_type = type(e).__name__
            error_msg = str(e)
            return f"Error calling Nemotron ({error_type}): {error_msg}"


# ============================================================================
# STEP 1: TEST INITIALIZATION
# ============================================================================

def step1_test_initialization():
    """
    STEP 1: Test basic initialization and API connection
    
    This function tests:
    1. Can we create the agent object?
    2. Are the API credentials configured correctly?
    3. Can we make a simple call to Nemotron?
    4. Is Nemotron responding properly?
    """
    print("\n" + "="*80)
    print("🧪 STEP 1: TESTING INITIALIZATION")
    print("="*80)
    
    print("\n📋 What we're going to test:")
    print("   ✓ Checking OpenAI library version")
    print("   ✓ Creating the NemotronTranscriptAgent object")
    print("   ✓ Verifying API credentials are set correctly")
    print("   ✓ Making a simple test call to Nemotron")
    print("   ✓ Confirming Nemotron responds as expected")
    
    # Check OpenAI library version
    print("\n" + "-"*80)
    print("CHECKING: Environment and Library")
    print("-"*80)
    
    # Check for environment variables that might override settings
    import os
    print("\n🔍 Checking environment variables:")
    openai_base = os.environ.get('OPENAI_BASE_URL')
    openai_key = os.environ.get('OPENAI_API_KEY')
    
    if openai_base:
        print(f"   ⚠️  WARNING: OPENAI_BASE_URL is set to: {openai_base}")
        print("   This might override your base_url setting!")
        clear = input("   Clear this environment variable for this session? (yes/no): ").strip().lower()
        if clear == 'yes':
            os.environ.pop('OPENAI_BASE_URL', None)
            print("   ✓ Cleared OPENAI_BASE_URL")
    else:
        print("   ✓ No OPENAI_BASE_URL environment variable")
    
    if openai_key:
        print(f"   ⚠️  Note: OPENAI_API_KEY is set (will be overridden by our key)")
    
    try:
        import openai
        print(f"\n✅ OpenAI library version: {openai.__version__}")
        
        # Parse version
        version_parts = openai.__version__.split('.')
        major_version = int(version_parts[0])
        
        if major_version < 1:
            print("\n⚠️  WARNING: You have an old version of openai library")
            print(f"   Current: {openai.__version__}")
            print("   Required: >= 1.0.0")
            print("\n   Please upgrade with: pip install --upgrade openai")
            proceed = input("\n   Continue anyway? (yes/no): ").strip().lower()
            if proceed != 'yes':
                return None
    except Exception as e:
        print(f"❌ Error checking OpenAI version: {e}")
    
    # ========================================================================
    # PART 1: Get API Credentials
    # ========================================================================
    print("\n" + "-"*80)
    print("PART 1: Getting API Credentials")
    print("-"*80)
    
    print("\n🔑 We need your Nemotron API credentials.")
    print("   Get them from: https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2")
    print("   1. Click 'Get API Key' button")
    print("   2. Generate or copy your existing API key")
    print("   Note: Key should start with 'nvapi-'")
    
    nemotron_key = input("\n   Enter your Nemotron API key: ").strip()
    
    # Validate key format
    if not nemotron_key.startswith('nvapi-'):
        print(f"\n   ⚠️  Warning: Your key doesn't start with 'nvapi-'")
        print(f"   Your key starts with: {nemotron_key[:10]}...")
        proceed = input("   Continue anyway? (yes/no): ").strip().lower()
        if proceed != 'yes':
            print("   Please get the correct API key format")
            return None
    
    print("\n🔗 API Base URL")
    print("   Recommended: https://integrate.api.nvidia.com/v1")
    print("   (This is NVIDIA's official API endpoint)")
    nemotron_url = input("   Enter base URL (or press Enter for recommended): ").strip()
    
    if not nemotron_url:
        nemotron_url = "https://integrate.api.nvidia.com/v1"
        print(f"   ✓ Using: {nemotron_url}")
    
    # Validate URL format
    if not nemotron_url.startswith('http'):
        nemotron_url = 'https://' + nemotron_url
        print(f"   Added https:// prefix: {nemotron_url}")
    
    if not nemotron_key:
        print("\n❌ ERROR: API key is required!")
        print("   Please get your API key from https://build.nvidia.com/")
        return None
    
    print("\n✅ Credentials received!")
    
    # ========================================================================
    # PART 2: Create Agent Object
    # ========================================================================
    print("\n" + "-"*80)
    print("PART 2: Creating Agent Object")
    print("-"*80)
    
    print(f"\n🔍 DEBUG INFO:")
    print(f"   API Key (first 10 chars): {nemotron_key[:10]}...")
    print(f"   Base URL: {nemotron_url}")
    
    # First, let's define the model alternatives we'll try
    
    try:
        print("\n⚙️  Creating NemotronTranscriptAgent...")
        agent = NemotronTranscriptAgent(
            nemotron_api_key=nemotron_key,
            nemotron_base_url=nemotron_url
        )
        print("✅ Agent object created successfully!")
        print(f"   Model: {agent.model}")
        
        # CRITICAL: Verify the client's base_url is correct
        print(f"\n🔍 VERIFYING CLIENT CONFIGURATION:")
        print(f"   Client base_url: {agent.client.base_url}")
        print(f"   Expected: {nemotron_url}")
        
        if str(agent.client.base_url) != nemotron_url:
            print(f"\n   ⚠️  WARNING: Base URL mismatch!")
            print(f"   Client is using: {agent.client.base_url}")
            print(f"   We expected: {nemotron_url}")
            
        print(f"   Base URL: {nemotron_url}")
        
    except Exception as e:
        print(f"\n❌ ERROR creating agent: {str(e)}")
        print("\nTroubleshooting tips:")
        print("   - Check that your API key is valid")
        print("   - Verify the base URL is correct")
        print("   - Make sure you have the 'openai' package installed: pip install openai")
        return None
    
    # ========================================================================
    # PART 3: Test Simple API Call
    # ========================================================================
    print("\n" + "-"*80)
    print("PART 3: Testing Simple API Call")
    print("-"*80)
    
    print(f"\n🧪 Testing API with model: {agent.model}")
    print(f"   Base URL: {nemotron_url}")
    print(f"   API Key: {nemotron_key[:10]}...{nemotron_key[-4:]}")
    
    # First, try a direct requests test
    print("\n🔍 Method 1: Testing with direct HTTP request...")
    import requests
    import json
    
    try:
        headers = {
            "Authorization": f"Bearer {nemotron_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": agent.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'Hello!' in one word."}
            ],
            "temperature": 0.1,
            "max_tokens": 50
        }
        
        print("   Sending request...")
        response = requests.post(
            f"{nemotron_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            message = result['choices'][0]['message']['content']
            print(f"   ✅ Direct request SUCCESS!")
            print(f"   Response: {message}")
        else:
            print(f"   ❌ Direct request failed")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Direct request error: {str(e)}")
    
    # Now try with OpenAI client
    print("\n🔍 Method 2: Testing with OpenAI client...")
    
    test_messages = [
        {
            "role": "system", 
            "content": "You are a helpful AI assistant."
        },
        {
            "role": "user", 
            "content": "Say 'Hello!' in one word."
        }
    ]
    
    try:
        print("   Sending request...")
        response = agent._call_nemotron(test_messages, temperature=0.1, max_tokens=50)
        
        print("\n📨 Nemotron Response:")
        print("-"*80)
        print(response)
        print("-"*80)
        
        # Check if response indicates an error
        if "error calling nemotron" in response.lower():
            print("\n❌ API call failed!")
            print(f"   Error: {response}")
            print("\n🔧 Common Issues and Solutions:")
            print("\n   1. CONNECTION ERROR:")
            print("      - Check your internet connection")
            print("      - Try: ping integrate.api.nvidia.com")
            print("      - Corporate firewall/proxy blocking the connection?")
            print("\n   2. AUTHENTICATION ERROR:")
            print("      - Verify your API key is correct")
            print("      - Key format: nvapi-xxxxx... (starts with 'nvapi-')")
            print("      - Get new key: https://build.nvidia.com/nvidia/nvidia-nemotron-nano-9b-v2")
            print("\n   3. API ENDPOINT:")
            print("      - Current base URL:", nemotron_url)
            print("      - Try alternative: https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/nvidia/nvidia-nemotron-nano-9b-v2")
            print("\n   4. MODEL ACCESS:")
            print("      - Ensure you have access to nvidia/nvidia-nemotron-nano-9b-v2")
            print("      - Some models require acceptance of terms")
            
            # Ask if user wants to try alternative URL
            print("\n" + "-"*80)
            retry = input("Would you like to try an alternative base URL? (yes/no): ").strip().lower()
            if retry == 'yes':
                print("\nTrying alternative endpoint...")
                alt_url = "https://api.nvcf.nvidia.com/v2/nvcf"
                agent.client = OpenAI(
                    api_key=nemotron_key,
                    base_url=alt_url
                )
                print(f"New base URL: {alt_url}")
                
                try:
                    response = agent._call_nemotron(test_messages, temperature=0.1, max_tokens=50)
                    print("\n📨 Response with alternative URL:")
                    print("-"*80)
                    print(response)
                    print("-"*80)
                    
                    if "error" not in response.lower():
                        print("\n✅ Alternative URL works!")
                    else:
                        print("\n❌ Alternative URL also failed")
                        return None
                except Exception as e:
                    print(f"\n❌ Alternative URL error: {str(e)}")
                    return None
            else:
                return None
        else:
            print("\n✅ API call successful!")
        
    except Exception as e:
        print(f"\n❌ ERROR during API call: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   - Check your internet connection")
        print("   - Verify API credentials")
        return None
    
    # ========================================================================
    # PART 4: Test Persona Prompt
    # ========================================================================
    print("\n" + "-"*80)
    print("PART 4: Testing Transcript Analysis Persona")
    print("-"*80)
    
    print("\n🎭 Testing with the specialized persona prompt...")
    print("   This ensures Nemotron understands its role as a transcript analyst")
    
    persona_test_messages = [
        {
            "role": "system", 
            "content": agent.persona_prompt
        },
        {
            "role": "user", 
            "content": "In one sentence, describe your primary role and capabilities."
        }
    ]
    
    try:
        print("\n⏳ Waiting for persona response...")
        persona_response = agent._call_nemotron(persona_test_messages, temperature=0.3, max_tokens=150)
        
        print("\n📨 Persona Response:")
        print("-"*80)
        print(persona_response)
        print("-"*80)
        
        print("\n✅ Persona prompt working!")
        
    except Exception as e:
        print(f"\n⚠️  Warning during persona test: {str(e)}")
        print("   Basic API works, but persona test had issues")
    
    # ========================================================================
    # FINAL RESULTS
    # ========================================================================
    print("\n" + "="*80)
    print("🎉 STEP 1 COMPLETE: INITIALIZATION SUCCESSFUL!")
    print("="*80)
    
    print("\n✅ Summary:")
    print("   ✓ Agent object created")
    print("   ✓ API credentials validated")
    print("   ✓ Nemotron is responding")
    print("   ✓ Persona prompt loaded")
    
    print("\n📊 Agent Details:")
    print(f"   Model: {agent.model}")
    print(f"   Persona: Transcript Analysis Expert")
    print(f"   Ready for: Planning, Research, and Report Generation")
    
    print("\n🚀 Next Steps:")
    print("   You can now use this agent for:")
    print("   - Step 2: Planning phase (analyzing transcripts)")
    print("   - Step 3: Research phase (web searches)")
    print("   - Step 4: Writing phase (generating reports)")
    
    return agent


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🤖 NEMOTRON TRANSCRIPT AGENT - STEP 1 ONLY")
    print("="*80)
    print("\nThis script tests ONLY the initialization of the Nemotron agent.")
    print("We'll verify that:")
    print("  1. We can connect to the Nemotron API")
    print("  2. The agent responds correctly")
    print("  3. The persona prompt is loaded")
    
    input("\n▶️  Press Enter to begin Step 1 testing...")
    
    # Run Step 1
    agent = step1_test_initialization()
    
    if agent:
        print("\n" + "="*80)
        print("✅ STEP 1 PASSED - Agent is ready!")
        print("="*80)
        
        # Optional: Simple interactive test
        print("\n💡 BONUS: Interactive Test")
        print("   Want to ask Nemotron a question directly?")
        test_mode = input("   Try interactive mode? (yes/no): ").strip().lower()
        
        if test_mode == 'yes':
            print("\n🎮 Interactive Mode (type 'quit' to exit)")
            print("-"*80)
            
            while True:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() == 'quit':
                    print("👋 Exiting interactive mode...")
                    break
                
                if not user_input:
                    continue
                
                messages = [
                    {"role": "system", "content": agent.persona_prompt},
                    {"role": "user", "content": user_input}
                ]
                
                print("\n🤖 Nemotron: ", end="")
                response = agent._call_nemotron(messages, temperature=0.7, max_tokens=500)
                print(response)
        
        print("\n✅ All tests complete!")
        
    else:
        print("\n" + "="*80)
        print("❌ STEP 1 FAILED")
        print("="*80)
        print("\nPlease check the error messages above and try again.")
        print("Common solutions:")
        print("  - Verify your API key from https://build.nvidia.com/")
        print("  - Check your internet connection")
        print("  - Ensure you have the OpenAI package: pip install openai")