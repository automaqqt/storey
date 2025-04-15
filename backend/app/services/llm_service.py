import os
import httpx
from ollama import Client as OllamaClient

from ..utils.json_clean import robust_json_load
from ..core.config import settings
from ..models.schema import LlmJsonResponse
import json
import re
from typing import List, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()

# Map of model IDs to provider configurations
MODEL_PROVIDERS = {
  "google/gemini-2.5-pro-exp-03-25:free": {
    "provider": "openrouter",
    "model_name": "google/gemini-2.5-pro-exp-03-25:free"
  },
  "google/gemini-2.0-flash-exp:free": {
    "provider": "openrouter",
    "model_name": "google/gemini-2.0-flash-exp:free"
  },
  "google/gemini-2.0-flash-thinking-exp-1219:free": {
    "provider": "openrouter",
    "model_name": "google/gemini-2.0-flash-thinking-exp-1219:free"
  },
  "deepseek/deepseek-chat-v3-0324:free": {
    "provider": "openrouter",
    "model_name": "deepseek/deepseek-chat-v3-0324:free"
  },
  "deepseek/deepseek-r1:free": {
    "provider": "openrouter",
    "model_name": "deepseek/deepseek-r1:free"
  },
  "qwen/qwq-32b:free": {
    "provider": "openrouter",
    "model_name": "qwen/qwq-32b:free"
  },
  "google/gemma-3-27b-it:free": {
    "provider": "openrouter",
    "model_name": "google/gemma-3-27b-it:free"
  },
  "meta-llama/llama-3.3-70b-instruct:free": {
    "provider": "openrouter",
    "model_name": "meta-llama/llama-3.3-70b-instruct:free"
  },
  "meta-llama/llama-3.2-3b-instruct:free": {
    "provider": "openrouter",
    "model_name": "meta-llama/llama-3.2-3b-instruct:free"
  }
}

# --- Sanitizer Function (Python version) ---
def sanitize_llm_json_response(raw_json_string: Optional[str]) -> Optional[dict]:
    if not raw_json_string or not isinstance(raw_json_string, str):
        print("Sanitize Error: Input is not a valid string.")
        return None

    trimmed_input = raw_json_string.strip()

    # --- Early Exit Check ---
    try:
        parsed_quick = json.loads(trimmed_input)
        if (isinstance(parsed_quick, dict) and
            isinstance(parsed_quick.get('storySegment'), str) and
            isinstance(parsed_quick.get('choices'), list) and
            len(parsed_quick['choices']) >= 2 and  # Allow for at least 2 choices
            all(isinstance(c, str) for c in parsed_quick['choices'])):
            return parsed_quick
        else:
            print("Sanitize Warning: Input parsed but structure mismatch.")
    except json.JSONDecodeError:
        pass # Proceed to full sanitization

    print("Sanitize Info: Running full sanitization.")
    
    # Try to find and extract JSON from common patterns
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    json_match = re.search(json_pattern, trimmed_input)
    
    if json_match:
        trimmed_input = json_match.group(1).strip()
    
    # Ensure we have a valid JSON object
    first_brace = trimmed_input.find('{')
    last_brace = trimmed_input.rfind('}')

    if first_brace == -1:
        print("Sanitize Error (Full): No opening '{'.")
        return None

    if last_brace == -1 or last_brace < first_brace:
        if trimmed_input.endswith('"') or trimmed_input.endswith(']'):
            trimmed_input += '}'
            print("Sanitize Warning (Full): Appended missing '}'.")
        else:
             print("Sanitize Warning (Full): Closing '}' seems missing.")
    else:
        trimmed_input = trimmed_input[first_brace : last_brace + 1]

    # Fix quotes in choices using regex
    choices_match = re.search(r'"choices"\s*:\s*\[([^\]]*)\]', trimmed_input)
    if choices_match:
        original_choices_block = choices_match.group(0)
        choices_content = choices_match.group(1).strip()
        if choices_content.endswith(','):
            choices_content = choices_content[:-1].strip()
            print("Sanitize Warning (Full): Removed trailing comma in choices.")

        items = [item.strip() for item in choices_content.split(',') if item.strip()]
        fixed_items = []
        for item in items:
            if item.startswith('"') and item.endswith('"'):
                fixed_items.append(item)
            elif item.startswith("'") and item.endswith("'"):
                 inner = item[1:-1].replace('"', '\\"')
                 fixed_items.append(f'"{inner}"')
            elif item.replace('.', '', 1).isdigit() or (item.startswith('-') and item[1:].replace('.', '', 1).isdigit()): # Handle numbers
                 fixed_items.append(item) # Keep numbers as is
            else:
                escaped = item.replace('"', '\\"')
                fixed_items.append(f'"{escaped}"')

        fixed_choices_content = ', '.join(fixed_items)
        fixed_choices_block = f'"choices": [{fixed_choices_content}]'
        trimmed_input = trimmed_input.replace(original_choices_block, fixed_choices_block)

    # --- Final Parse ---
    try:
        final_parsed = json.loads(trimmed_input)
         # Final validation
        if not (isinstance(final_parsed, dict) and
                isinstance(final_parsed.get('storySegment'), str) and
                isinstance(final_parsed.get('choices'), list) and
                len(final_parsed['choices']) >= 2 and
                all(isinstance(c, str) for c in final_parsed['choices'])):
             print("Sanitize Warning (Full): Parsed object structure invalid AFTER sanitization.")
             return None # Be strict after sanitizing
        return final_parsed
    except json.JSONDecodeError as e:
        print(f"Sanitize Error (Full): Final parse failed. {e}")
        print(f"Final sanitized string was: {trimmed_input}")
        return None
# --- End Sanitizer ---

# --- LLM Interaction Logic ---
async def generate_llm_response(
    system_prompt: str, 
    user_prompt: str, 
    model: Optional[str] = None,
    temperature: float = 0.7
) -> Tuple[Optional[dict], Optional[str]]:
    """Calls the configured LLM and returns the sanitized JSON response and raw response."""
    raw_response_content = None
    
    # Ensure temperature is within valid range
    temperature = max(0.0, min(1.0, temperature))
    
    # Determine which model and provider to use
    llm_type = settings.llm_type
    model_name = settings.llm_model_name
    
    # Override with custom model if provided
    if model and model in MODEL_PROVIDERS:
        provider_config = MODEL_PROVIDERS[model]
        llm_type = provider_config["provider"]
        model_name = provider_config["model_name"]
        print(f"Using custom model: {model} ({llm_type}/{model_name})")
    
    print(f"Using temperature: {temperature}")
    
    try:
        if llm_type == "ollama":
            print(f"LLM: Calling Ollama with model {model_name}...")
            client = OllamaClient(host=settings.llm_api_url.replace("/api/generate",""))
            response = client.generate(
                model=model_name,
                system=system_prompt,
                prompt=user_prompt,
                format='json',
                options={'temperature': temperature}
            )
            raw_response_content = response.get('response')

        elif llm_type == "openai_compatible":
            print(f"LLM: Calling OpenAI compatible API with model {model_name}...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 450,
                "response_format": {"type": "json_object"}
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(settings.openai_api_url, json=payload, timeout=900.0)
                response.raise_for_status()
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message'):
                    raw_response_content = data['choices'][0]['message'].get('content')
                else:
                     print("LLM Error: Invalid response structure from OpenAI API", data)
        
        elif llm_type == "anthropic":
            print(f"LLM: Calling Anthropic API with model {model_name}...")
            headers = {
                "Content-Type": "application/json",
                "x-api-key": os.getenv('ANTHROPIC_API_KEY'),
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": model_name,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": temperature,
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=120.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('content') and len(data['content']) > 0:
                    raw_response_content = data['content'][0].get('text')
                else:
                    print("LLM Error: Invalid response structure from Anthropic API", data)
        
        elif llm_type == "openrouter":
            print(f"LLM: Calling Openrouter with model {model_name}...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    },
                    json={
                        "model": model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2420,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=120.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message'):
                    raw_response_content = data['choices'][0]['message'].get('content')
                else:
                    print("LLM Error: Invalid response structure from OpenRouter API", data)

        elif llm_type == "deepseek_api":
            print(f"LLM: Calling Deepseek API with model {settings.openrouter_model}...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    },
                    json={
                        "model": settings.openrouter_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 2420,
                    },
                    timeout=120.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message'):
                    raw_response_content = data['choices'][0]['message'].get('content')
                else:
                    print("LLM Error: Invalid response structure from Deepseek API", data)
        else:
            print(f"LLM Error: Unsupported llm_type '{llm_type}'")
            return None, None

        print(f"LLM Raw Response (first 200 chars): {str(raw_response_content)[:200]}...")
        sanitized_data = robust_json_load(raw_response_content)
        
        if not sanitized_data:
            # Fall back to custom sanitizer if robust_json_load fails
            sanitized_data = sanitize_llm_json_response(raw_response_content)
            if not sanitized_data:
                print("LLM Error: Failed to sanitize/validate response after multiple attempts.")
                return None, raw_response_content
        
        return sanitized_data, raw_response_content

    except httpx.RequestError as e:
        print(f"LLM Connection Error: Could not connect to {e.request.url!r}. {e}")
        return None, str(e)
    except httpx.HTTPStatusError as e:
        print(f"LLM API Error: Status {e.response.status_code} from {e.request.url!r}. Response: {e.response.text[:200]}")
        return None, e.response.text
    except Exception as e:
        print(f"LLM Interaction Error: An unexpected error occurred: {e}")
        return None, str(e)


async def summarize_story(
    existing_summary: str, 
    recent_developments: List[str], 
    tale_title: str,
    model: Optional[str] = None,
    custom_system_prompt: Optional[str] = None,
    temperature: float = 0.7
) -> str:
    """Uses the LLM to summarize the story progress."""
    if not recent_developments:
        return existing_summary # No changes to summarize

    # Ensure temperature is within valid range
    temperature = max(0.0, min(1.0, temperature))
    
    # Use custom system prompt if provided
    if custom_system_prompt:
        system_prompt = custom_system_prompt
    else:
        system_prompt = f"You are an expert story summarizer. Condense the 'Existing Summary' and 'Recent Developments' into a single, updated, concise summary capturing the current plot state, characters, and setting of this interactive story based on the tale '{tale_title}'. Focus on information needed to continue the story logically. Output ONLY the updated summary text. DO IT IN GERMAN"

    developments_text = "\n".join(recent_developments)
    user_prompt = f"""Existing Summary:
                    {existing_summary}

                    Recent Developments:
                    {developments_text}

                    Updated Summary:"""
    
    print(f"LLM Summarizer: Calling LLM with temperature {temperature}...")
    
    try:
        # Determine which model and provider to use for summary
        llm_type = settings.llm_type
        model_name = settings.llm_model_name
        
        # Override with custom model if provided
        if model and model in MODEL_PROVIDERS:
            provider_config = MODEL_PROVIDERS[model]
            llm_type = provider_config["provider"]
            model_name = provider_config["model_name"]
            print(f"Using custom summary model: {model} ({llm_type}/{model_name})")
        
        summary_text = "Summary failed."  # Default
        
        if llm_type == "openai_compatible":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            payload = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 450,
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(settings.openai_api_url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message'):
                    summary_text = data['choices'][0]['message'].get('content', '').strip()
        
        elif llm_type == "anthropic":
            headers = {
                "Content-Type": "application/json",
                "x-api-key": os.getenv('ANTHROPIC_API_KEY'),
                "anthropic-version": "2023-06-01"
            }
            payload = {
                "model": model_name,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": temperature,
                "max_tokens": 450
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('content') and len(data['content']) > 0:
                    summary_text = data['content'][0].get('text', '').strip()
        
        elif llm_type == "openrouter" or llm_type == "deepseek_api":
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            model_to_use = model_name if llm_type == "openrouter" else settings.openrouter_model
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                    },
                    json={
                        "model": model_to_use,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": 450,
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('choices') and data['choices'][0].get('message'):
                    summary_text = data['choices'][0]['message'].get('content', '').strip()
        
        elif llm_type == "ollama":
            client = OllamaClient(host=settings.llm_api_url.replace("/api/generate",""))
            response = client.generate(
                model=model_name,
                system=system_prompt,
                prompt=user_prompt,
                options={'temperature': temperature}
            )
            summary_text = response.get('response', '').strip()

        if not summary_text or len(summary_text) < 10:
            print("LLM Summarizer: Got empty or too short summary, reverting.")
            return existing_summary # Revert if summary looks bad

        print(f"LLM Summarizer: New summary generated: {summary_text[:100]}...")
        return summary_text

    except Exception as e:
        print(f"LLM Summarizer Error: {e}")
        return existing_summary # Return old summary on error