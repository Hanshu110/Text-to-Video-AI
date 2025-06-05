import whisper_timestamped as whisper
from whisper_timestamped import load_model, transcribe_timestamped
import re
import os
import traceback

def generate_timed_captions(audio_filename, model_size="base"):
    """
    Generate timed captions with multiple fallback methods
    """
    try:
        print(f"Debug: Starting caption generation for {audio_filename}")
        print(f"Debug: Model size: {model_size}")
        
        # Check if audio file exists and is valid
        if not os.path.exists(audio_filename):
            raise FileNotFoundError(f"Audio file not found: {audio_filename}")
        
        file_size = os.path.getsize(audio_filename)
        print(f"Debug: Audio file size: {file_size} bytes")
        
        if file_size == 0:
            raise ValueError("Audio file is empty (0 bytes)")
        
        print("Debug: Loading Whisper model...")
        WHISPER_MODEL = load_model(model_size)
        print("Debug: Model loaded successfully")
        
        # Try multiple transcription methods in order of preference
        methods = [
            ("whisper_timestamped_conservative", transcribe_with_conservative_settings),
            ("whisper_timestamped_basic", transcribe_with_basic_settings),
            ("fallback_regular_whisper", transcribe_with_regular_whisper),
            ("simple_timing", create_simple_timed_captions)
        ]
        
        for method_name, method_func in methods:
            try:
                print(f"Debug: Trying {method_name}...")
                result = method_func(WHISPER_MODEL, audio_filename)
                if result:
                    print(f"Debug: {method_name} succeeded!")
                    return getCaptionsWithTime(result)
            except Exception as e:
                print(f"Debug: {method_name} failed: {str(e)}")
                continue
        
        # If all methods fail, return empty captions
        print("Debug: All transcription methods failed, returning empty captions")
        return []
        
    except Exception as e:
        print(f"Error in generate_timed_captions: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return []

def transcribe_with_conservative_settings(model, audio_filename):
    """Most conservative settings to avoid attention weight issues"""
    try:
        return transcribe_timestamped(
            model, 
            audio_filename, 
            verbose=False, 
            fp16=False,
            language="en",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            condition_on_previous_text=False
            # Removed word_timestamps parameter as it's causing issues
        )
    except Exception as e:
        print(f"Conservative settings failed: {e}")
        raise e

def transcribe_with_basic_settings(model, audio_filename):
    """Basic settings without advanced features"""
    try:
        return transcribe_timestamped(
            model, 
            audio_filename, 
            verbose=False, 
            fp16=False,
            language="en"
            # Removed word_timestamps parameter
        )
    except Exception as e:
        print(f"Basic settings failed: {e}")
        raise e

def transcribe_with_regular_whisper(model, audio_filename):
    """Fallback to regular whisper without timestamped version"""
    try:
        import whisper
        
        # Load regular whisper model if we don't have it
        if not hasattr(model, 'transcribe'):
            model = whisper.load_model("base")
        
        result = model.transcribe(
            audio_filename,
            language="en",
            word_timestamps=True
        )
        
        # Convert regular whisper format to timestamped format
        if 'segments' in result:
            return result
        else:
            # Create basic structure if segments are missing
            return {
                'text': result.get('text', ''),
                'segments': [{
                    'start': 0,
                    'end': 10,  # Default duration
                    'text': result.get('text', ''),
                    'words': []
                }]
            }
    except Exception as e:
        print(f"Regular whisper fallback failed: {e}")
        return None

def create_simple_timed_captions(model, audio_filename):
    """Create simple captions without word-level timing"""
    try:
        import whisper
        
        # Use basic whisper transcription
        if not hasattr(model, 'transcribe'):
            model = whisper.load_model("base")
            
        result = model.transcribe(audio_filename, language="en")
        text = result.get('text', '')
        
        if not text:
            return None
            
        # Estimate duration (very rough)
        estimated_duration = len(text) * 0.05  # ~20 chars per second
        
        return {
            'text': text,
            'segments': [{
                'start': 0,
                'end': max(estimated_duration, 5.0),
                'text': text,
                'words': []
            }]
        }
    except Exception as e:
        print(f"Simple caption creation failed: {e}")
        return None

def splitWordsBySize(words, maxCaptionSize):
    halfCaptionSize = maxCaptionSize / 2
    captions = []
    while words:
        caption = words[0]
        words = words[1:]
        while words and len(caption + ' ' + words[0]) <= maxCaptionSize:
            caption += ' ' + words[0]
            words = words[1:]
            if len(caption) >= halfCaptionSize and words:
                break
        captions.append(caption)
    return captions

def getTimestampMapping(whisper_analysis):
    try:
        print("Debug: Creating timestamp mapping...")
        index = 0
        locationToTimestamp = {}
        
        if 'segments' not in whisper_analysis:
            print("Debug: No segments found in whisper analysis")
            return {}
        
        segments = whisper_analysis['segments']
        print(f"Debug: Processing {len(segments)} segments")
        
        for seg_idx, segment in enumerate(segments):
            if 'words' not in segment or not segment['words']:
                print(f"Debug: No words in segment {seg_idx}")
                continue
                
            words = segment['words']
            print(f"Debug: Segment {seg_idx} has {len(words)} words")
            
            for word_idx, word in enumerate(words):
                if not isinstance(word, dict):
                    continue
                
                # Handle both 'text' and 'word' keys (different whisper versions)
                word_text = None
                if 'text' in word:
                    word_text = str(word['text']).strip()
                elif 'word' in word:
                    word_text = str(word['word']).strip()
                
                if not word_text or 'start' not in word or 'end' not in word:
                    print(f"Debug: Skipping incomplete word data at segment {seg_idx}, word {word_idx}")
                    continue
                    
                if word_text:
                    start_index = index
                    end_index = index + len(word_text)
                    locationToTimestamp[(start_index, end_index)] = {
                        'start': float(word['start']),
                        'end': float(word['end'])
                    }
                    index = end_index + 1
        
        print(f"Debug: Created {len(locationToTimestamp)} timestamp mappings")
        return locationToTimestamp
        
    except Exception as e:
        print(f"Error in getTimestampMapping: {str(e)}")
        traceback.print_exc()
        return {}

def cleanWord(word):
    return re.sub(r'[^\w\s\-_"\'\']', '', word)

def interpolateTimeFromDict(word_position, d, search_type='end'):
    if not d:
        return None
        
    # First try exact matches
    for (start, end), timestamps in d.items():
        if start <= word_position < end:
            return timestamps.get(search_type)
    
    # If no exact match, find the closest range
    closest_time = None
    min_distance = float('inf')
    
    for (start, end), timestamps in d.items():
        if word_position >= end:
            distance = word_position - end
            if distance < min_distance:
                min_distance = distance
                closest_time = timestamps.get(search_type)
    
    return closest_time

def getCaptionsWithTime(whisper_analysis, maxCaptionSize=15, considerPunctuation=False):
    try:
        print("Debug: Starting getCaptionsWithTime")
        
        # Validate input
        if not whisper_analysis or not isinstance(whisper_analysis, dict):
            raise ValueError("Invalid whisper_analysis")
        
        if 'text' not in whisper_analysis:
            raise ValueError("No 'text' field in whisper_analysis")
        
        text = whisper_analysis['text']
        if not text or not str(text).strip():
            print("Debug: Empty or whitespace-only text")
            return []
        
        text = str(text).strip()
        print(f"Debug: Processing text: '{text[:100]}...'")
        
        # Get word-to-timestamp mapping
        wordLocationToTime = getTimestampMapping(whisper_analysis)
        
        # Initialize variables
        text_position = 0
        start_time = 0
        CaptionsPairs = []
        
        # Split text into caption-sized chunks
        if considerPunctuation:
            sentences = re.split(r'(?<=[.!?]) +', text)
            words = [word for sentence in sentences for word in splitWordsBySize(sentence.split(), maxCaptionSize)]
        else:
            original_words = text.split()
            words = splitWordsBySize(original_words, maxCaptionSize)
        
        print(f"Debug: Split into {len(words)} caption chunks")
        
        # If we have no timestamp mapping, create simple time-based captions
        if not wordLocationToTime:
            print("Debug: No timestamp mapping available, using estimated timing")
            
            # Try to get total duration from segments
            total_duration = 10.0  # Default
            if whisper_analysis.get('segments'):
                try:
                    last_segment = whisper_analysis['segments'][-1]
                    if 'end' in last_segment and last_segment['end']:
                        total_duration = float(last_segment['end'])
                except (IndexError, KeyError, ValueError, TypeError):
                    pass
            
            duration_per_caption = total_duration / len(words) if words else 1.0
            
            for i, caption_text in enumerate(words):
                if str(caption_text).strip():
                    start_time = i * duration_per_caption
                    end_time = (i + 1) * duration_per_caption
                    
                    if not considerPunctuation:
                        caption_text = cleanWord(str(caption_text))
                    
                    caption_text = str(caption_text).strip()
                    if caption_text:
                        CaptionsPairs.append(((start_time, end_time), caption_text))
            
            print(f"Debug: Created {len(CaptionsPairs)} estimated caption pairs")
            return CaptionsPairs
        
        # Process each caption chunk with timestamps
        for i, caption_text in enumerate(words):
            caption_text = str(caption_text).strip()
            if not caption_text:
                continue
                
            # Calculate position in original text
            if i == 0:
                text_position = len(caption_text)
            else:
                text_position += len(caption_text) + 1  # +1 for space
            
            # Get end time for this caption
            end_time = interpolateTimeFromDict(text_position, wordLocationToTime, 'end')
            
            if end_time is None:
                # Fallback timing
                if CaptionsPairs:
                    last_end = CaptionsPairs[-1][0][1]
                    estimated_duration = len(caption_text) * 0.1
                    end_time = last_end + estimated_duration
                else:
                    end_time = len(caption_text) * 0.1
            
            # Ensure we have a valid end_time
            if end_time is None:
                end_time = start_time + len(caption_text) * 0.1
            
            # Clean the caption text if needed
            if not considerPunctuation:
                caption_text = cleanWord(caption_text)
            
            caption_text = caption_text.strip()
            if caption_text and end_time is not None:
                CaptionsPairs.append(((start_time, end_time), caption_text))
                start_time = end_time
        
        print(f"Debug: Generated {len(CaptionsPairs)} caption pairs")
        return CaptionsPairs
        
    except Exception as e:
        print(f"Error in getCaptionsWithTime: {str(e)}")
        traceback.print_exc()
        return []
