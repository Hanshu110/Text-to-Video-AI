import os
import json
import re
from openai import OpenAI

groq_key = os.environ.get("GROQ_API_KEY")
if groq_key and len(groq_key) > 30:
    from groq import Groq
    model = "llama3-70b-8192"
    client = Groq(api_key=groq_key)
else:
    OPENAI_API_KEY = os.getenv("OPENAI_KEY")
    model = "gpt-4o"
    client = OpenAI(api_key=OPENAI_API_KEY)

def extract_json_from_response(content):
    """Extract JSON from AI response that might have extra text."""
    # Remove markdown code blocks if present
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
    
    # Try to find JSON object using regex
    json_pattern = r'\{[^{}]*"script"\s*:\s*"[^"]*"[^{}]*\}'
    match = re.search(json_pattern, content, re.DOTALL)
    
    if match:
        return match.group(0)
    
    # If no match, try to find the content between first { and last }
    start = content.find('{')
    end = content.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        return content[start:end+1]
    
    return content

def generate_script(topic):
    prompt = (
        """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos.
        
        Your facts shorts are concise, each lasting less than 50 seconds (approximately 140 words).
        
        They are incredibly engaging and original. When a user requests a specific type of facts short, you will create it.
        
        For instance, if the user asks for:
        Weird facts
        You would produce content like this:
        
        Weird facts you don't know:
        - Bananas are berries, but strawberries aren't.
        - A single cloud can weigh over a million pounds.
        - There's a species of jellyfish that is biologically immortal.
        - Honey never spoils; archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.
        - The shortest war in history was between Britain and Zanzibar on August 27, 1896. Zanzibar surrendered after 38 minutes.
        - Octopuses have three hearts and blue blood.
        
        You are now tasked with creating the best short script based on the user's requested type of 'facts'.
        
        Keep it brief, highly interesting, and unique.
        
        IMPORTANT: Output ONLY a valid JSON object with the key 'script'. Do not include any explanatory text, markdown formatting, or additional content outside the JSON.
        
        Example format:
        {"script": "Your script content here"}
        """
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": topic}
            ],
            temperature=0.7,
            max_tokens=500
        )

        content = response.choices[0].message.content.strip()
        print(f"Raw AI response: {content}")  # Debug output
        
        # Try multiple parsing strategies
        parsing_strategies = [
            # Strategy 1: Direct parsing
            lambda x: json.loads(x),
            
            # Strategy 2: Extract JSON from mixed content
            lambda x: json.loads(extract_json_from_response(x)),
            
            # Strategy 3: Clean whitespace and special characters
            lambda x: json.loads(x.strip().replace('\n', ' ').replace('\r', '')),
            
            # Strategy 4: Remove potential markdown
            lambda x: json.loads(x.strip().strip('`').replace('```json', '').replace('```', '')),
        ]
        
        for i, strategy in enumerate(parsing_strategies, 1):
            try:
                parsed = strategy(content)
                if isinstance(parsed, dict) and 'script' in parsed:
                    print(f"✅ Successfully parsed using strategy {i}")
                    return parsed['script']
                elif isinstance(parsed, dict):
                    print(f"⚠️ Strategy {i} parsed JSON but no 'script' key found")
                    # Return the first string value if no 'script' key
                    for value in parsed.values():
                        if isinstance(value, str):
                            return value
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"❌ Strategy {i} failed: {str(e)}")
                continue
        
        # If all strategies fail, try to extract content manually
        if content.startswith('{') and '}' in content:
            # Find script content between quotes
            script_match = re.search(r'"script"\s*:\s*"([^"]*)"', content, re.DOTALL)
            if script_match:
                print("✅ Extracted script using regex fallback")
                return script_match.group(1)
        
        # Last resort: return cleaned content
        print("⚠️ All parsing failed, returning cleaned raw content")
        return content.strip().strip('`').replace('```json', '').replace('```', '')
        
    except Exception as e:
        print(f"❌ Error in generate_script: {str(e)}")
        return f"Error generating script: {str(e)}"

# Test function
def test_script_generator():
    """Test the script generator with a sample topic."""
    test_topic = "space facts"
    script = generate_script(test_topic)
    print(f"\n📝 Generated script for '{test_topic}':")
    print(f"Script: {script}")
    print(f"Length: {len(script.split())} words")

if __name__ == "__main__":
    test_script_generator()
