import requests
import anthropic

API_ERROR_PREFIX = "[API_ERROR]"
OLLAMA_ERROR_PREFIX = "[OLLAMA_ERROR]"


def ollama_generate(prompt: str, model: str = "llama3.1:8b") -> str:
    """Generate text using local Ollama server."""
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "")
    except requests.exceptions.ConnectionError:
        return f"{OLLAMA_ERROR_PREFIX} Could not connect to Ollama. Please install Ollama from https://ollama.com and run: ollama serve"
    except requests.exceptions.Timeout:
        return f"{OLLAMA_ERROR_PREFIX} Ollama request timed out. The model may be loading or the prompt is too long."
    except requests.exceptions.RequestException as e:
        return f"{OLLAMA_ERROR_PREFIX} Ollama error: {str(e)}"


def claude_generate(prompt: str, api_key: str) -> str:
    """Generate text using Claude API."""
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.BadRequestError as e:
        if "credit balance is too low" in str(e):
            return f"{API_ERROR_PREFIX} Your Anthropic credit balance is too low. Please add credits at console.anthropic.com to continue using Claude."
        raise


def generate_markdown(provider: str, prompt: str, api_key: str = None) -> str:
    """Route to the appropriate LLM provider."""
    if provider == "Local (Ollama)":
        return ollama_generate(prompt)
    elif provider == "Claude (Anthropic)":
        if not api_key:
            return f"{API_ERROR_PREFIX} Claude API key is required for this provider."
        return claude_generate(prompt, api_key)
    else:
        return f"{API_ERROR_PREFIX} Unknown provider: {provider}"
