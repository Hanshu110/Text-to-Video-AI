from openai import OpenAI
import os
import json
import re
from datetime import datetime
from utility.utils import log_response, LOG_TYPE_GPT

if len(os.environ.get("GROQ_API_KEY", "")) > 30:
    from groq import Groq
    model = "llama3-70b-8192"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
else:
    model = "gpt-4o"
    OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

log_directory = ".logs/gpt_logs"

prompt = """# Instructions

Given the following video script and timed captions, extract three visually concrete and specific keywords for each time segment that can be used to search for background videos. The keywords should be short and capture the main essence of the sentence. They can be synonyms or related terms. If a caption is vague or general, consider the next timed caption for more context. If a keyword is a single word, try to return a two-word keyword that is visually concrete. If a time frame contains two or more important pieces of information, divide it into shorter time frames with one keyword each. Ensure that the time periods are strictly consecutive and cover the entire length of the video. Each keyword should cover between 2-4 seconds. The output should be in JSON format, like this: [[[t1, t2], ["keyword1", "keyword2", "keyword3"]], [[t2, t3], ["keyword4", "keyword5", "keyword6"]], ...]. Please handle all edge cases, such as overlapping time segments, vague or general captions, and single-word keywords.

For example, if the caption is 'The cheetah is the fastest land animal, capable of running at speeds up to 75 mph', the keywords should include 'cheetah running', 'fastest animal', and '75 mph'. Similarly, for 'The Great Wall of China is one of the most iconic landmarks in the world', the keywords should be 'Great Wall of China', 'iconic landmark', and 'China landmark'.

Important Guidelines:

Use only English in your text queries.
Each search string must depict something visual.
The depictions have to be extremely visually concrete, like rainy street, or cat sleeping.
'emotional moment' <= BAD, because it doesn't depict something visually.
'crying child' <= GOOD, because it depicts something visual.
The list must always contain the most relevant and appropriate query searches.
['Car', 'Car driving', 'Car racing', 'Car parked'] <= BAD, because it's 4 strings.
['Fast car'] <= GOOD, because it's 1 string.
['Un chien', 'une voiture rapide', 'une maison rouge'] <= BAD, because the text query is NOT in English.

IMPORTANT: Return ONLY a valid JSON array. Do not include any explanatory text, markdown formatting, or additional content outside the JSON array.

Note: Your response should be the JSON array only and no extra text or data.
"""

def extract_json_array_from_response(content):
    """Extract JSON array from AI response that might have extra text."""
    # Remove markdown code blocks if present
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE)
    content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
    content = content.strip()
    
    # Try to find JSON array using regex
    json_array_pattern = r'\[\s*\[\s*\[\s*[\d\.,\s]+\]\s*,\s*\[.*?\]\s*\].*?\]'
    match = re.search(json_array_pattern, content, re.DOTALL)
    
    if match:
        return match.group(0)
    
    # If no match, try to find content between first [ and last ]
    start = content.find('[')
    end = content.rfind(']')
    
    if start != -1 and end != -1 and end > start:
        return content[start:end+1]
    
    return content

def fix_json_format(json_str):
    """Fix common JSON formatting issues."""
    try:
        # Replace typographical quotes with standard quotes
        json_str = json_str.replace("'", "'").replace("'", "'")
        json_str = json_str.replace(""", '"').replace(""", '"')
        json_str = json_str.replace("'", '"')
        
        # Fix single quotes to double quotes (but be careful about contractions)
        json_str = re.sub(r"'([^']*)'(?=\s*[,\]\}])", r'"\1"', json_str)
        
        # Fix missing commas between array elements
        json_str = re.sub(r'(\])\s*(\[)', r'\1,\2', json_str)
        
        # Fix trailing commas
        json_str = re.sub(r',\s*(\]|\})', r'\1', json_str)
        
        # Ensure proper spacing
        json_str = re.sub(r'\s+', ' ', json_str)
        
        return json_str.strip()
        
    except Exception as e:
        print(f"Error in fix_json_format: {e}")
        return json_str

def validate_and_fix_search_terms(data):
    """Validate and fix the structure of search terms data."""
    if not isinstance(data, list):
        return []
    
    fixed_data = []
    
    for item in data:
        try:
            if not isinstance(item, list) or len(item) != 2:
                continue
                
            time_segment, keywords = item
            
            # Validate time segment
            if not isinstance(time_segment, list) or len(time_segment) != 2:
                continue
                
            start_time, end_time = time_segment
            
            # Ensure times are numbers
            try:
                start_time = float(start_time)
                end_time = float(end_time)
            except (ValueError, TypeError):
                continue
            
            # Validate keywords
            if not isinstance(keywords, list):
                continue
                
            # Clean and validate keywords
            clean_keywords = []
            for keyword in keywords:
                if isinstance(keyword, str) and keyword.strip():
                    clean_keywords.append(keyword.strip())
            
            # Ensure we have at least one keyword
            if clean_keywords:
                fixed_data.append([[start_time, end_time], clean_keywords])
                
        except Exception as e:
            print(f"Error processing item: {e}")
            continue
    
    return fixed_data

def create_fallback_search_terms(script, captions_timed):
    """Create fallback search terms when AI generation fails."""
    try:
        fallback_terms = []
        
        # Extract key nouns and concepts from the script
        # Simple keyword extraction
        words = re.findall(r'\b[A-Z][a-z]+\b|\b[a-z]{4,}\b', script)
        unique_words = list(set(words))[:10]  # Get unique words, limit to 10
        
        # Create time segments based on captions
        if captions_timed:
            segment_duration = 3.0  # 3 seconds per segment
            total_duration = captions_timed[-1][0][1] if captions_timed else 30.0
            
            current_time = 0.0
            word_index = 0
            
            while current_time < total_duration:
                end_time = min(current_time + segment_duration, total_duration)
                
                # Get keywords for this segment
                keywords = []
                for i in range(3):  # Try to get 3 keywords
                    if word_index < len(unique_words):
                        keywords.append(unique_words[word_index])
                        word_index += 1
                    else:
                        # Fallback to generic terms
                        generic_terms = ["nature scene", "landscape view", "abstract background"]
                        keywords.append(generic_terms[i % len(generic_terms)])
                
                fallback_terms.append([[current_time, end_time], keywords])
                current_time = end_time
        
        else:
            # If no captions, create simple segments
            fallback_terms = [
                [[0.0, 10.0], ["nature scene", "landscape view", "abstract background"]],
                [[10.0, 20.0], ["city view", "modern building", "urban scene"]],
                [[20.0, 30.0], ["sky view", "clouds", "peaceful scene"]]
            ]
        
        print(f"Created {len(fallback_terms)} fallback search terms")
        return fallback_terms
        
    except Exception as e:
        print(f"Error creating fallback search terms: {e}")
        return [[[0.0, 30.0], ["nature scene", "landscape view", "peaceful background"]]]

def getVideoSearchQueriesTimed(script, captions_timed, max_retries=3):
    """Generate video search queries with robust error handling."""
    
    if not captions_timed:
        print("No captions provided, creating fallback search terms")
        return create_fallback_search_terms(script, [])
    
    end_time = captions_timed[-1][0][1]
    
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to generate search queries...")
            
            # Get AI response
            raw_content = call_OpenAI(script, captions_timed)
            print(f"Raw AI response (first 200 chars): {raw_content[:200]}...")
            
            # Try multiple parsing strategies
            parsing_strategies = [
                # Strategy 1: Direct parsing
                lambda x: json.loads(x),
                
                # Strategy 2: Extract and parse JSON array
                lambda x: json.loads(extract_json_array_from_response(x)),
                
                # Strategy 3: Fix formatting and parse
                lambda x: json.loads(fix_json_format(x)),
                
                # Strategy 4: Combined extraction and fixing
                lambda x: json.loads(fix_json_format(extract_json_array_from_response(x))),
                
                # Strategy 5: Replace single quotes and parse
                lambda x: json.loads(x.replace("'", '"')),
            ]
            
            for i, strategy in enumerate(parsing_strategies, 1):
                try:
                    print(f"Trying parsing strategy {i}...")
                    parsed_data = strategy(raw_content)
                    
                    if isinstance(parsed_data, list):
                        # Validate and fix the structure
                        validated_data = validate_and_fix_search_terms(parsed_data)
                        
                        if validated_data:
                            # Check if we have coverage for the full duration
                            last_end = validated_data[-1][0][1] if validated_data else 0
                            
                            if abs(last_end - end_time) <= 2.0:  # Allow 2 second tolerance
                                print(f"✅ Successfully parsed with strategy {i}")
                                print(f"Generated {len(validated_data)} search term segments")
                                return validated_data
                            else:
                                print(f"⚠️ Strategy {i} parsed but duration mismatch: {last_end} vs {end_time}")
                        else:
                            print(f"⚠️ Strategy {i} parsed but validation failed")
                    else:
                        print(f"⚠️ Strategy {i} didn't return a list")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Strategy {i} JSON error: {str(e)}")
                    continue
                except Exception as e:
                    print(f"❌ Strategy {i} failed: {str(e)}")
                    continue
            
            print(f"All parsing strategies failed for attempt {attempt + 1}")
            
            if attempt < max_retries - 1:
                print("Retrying with modified prompt...")
                # You could modify the prompt here for retry
            
        except Exception as e:
            print(f"Error in attempt {attempt + 1}: {str(e)}")
            
            if attempt < max_retries - 1:
                print("Retrying...")
            
    # If all attempts fail, create fallback
    print("All attempts failed, creating fallback search terms...")
    return create_fallback_search_terms(script, captions_timed)

def call_OpenAI(script, captions_timed):
    """Call OpenAI API with improved error handling."""
    try:
        user_content = """Script: {}
Timed Captions:{}
""".format(script, "".join(map(str, captions_timed)))
        
        print("Sending request to AI...")
        
        response = client.chat.completions.create(
            model=model,
            temperature=0.3,  # Lower temperature for more consistent formatting
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        text = response.choices[0].message.content.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        print("AI response received successfully")
        log_response(LOG_TYPE_GPT, script, text)
        
        return text
        
    except Exception as e:
        print(f"Error calling AI API: {str(e)}")
        raise e

def merge_empty_intervals(segments):
    """Merge empty intervals with improved error handling."""
    try:
        if not segments or not isinstance(segments, list):
            return []
            
        merged = []
        i = 0
        
        while i < len(segments):
            try:
                interval, url = segments[i]
                
                if url is None:
                    # Find consecutive None intervals
                    j = i + 1
                    while j < len(segments) and segments[j][1] is None:
                        j += 1
                    
                    # Merge consecutive None intervals with the previous valid URL
                    if i > 0 and merged:
                        prev_interval, prev_url = merged[-1]
                        if prev_url is not None and len(prev_interval) >= 2 and len(interval) >= 2:
                            if prev_interval[1] == interval[0]:
                                # Update the last merged interval
                                end_time = segments[j-1][0][1] if j > i+1 else interval[1]
                                merged[-1] = [[prev_interval[0], end_time], prev_url]
                            else:
                                merged.append([interval, prev_url if merged else None])
                        else:
                            merged.append([interval, None])
                    else:
                        merged.append([interval, None])
                    
                    i = j
                else:
                    merged.append([interval, url])
                    i += 1
                    
            except (IndexError, TypeError, ValueError) as e:
                print(f"Error processing segment at index {i}: {e}")
                i += 1
                continue
        
        return merged
        
    except Exception as e:
        print(f"Error in merge_empty_intervals: {e}")
        return segments  # Return original if merging fails
