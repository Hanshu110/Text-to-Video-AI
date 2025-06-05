from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
import os
import edge_tts
import json
import asyncio
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse
import sys

# Robust audio generation function with retry logic
async def robust_audio_generation(text, filename, max_retries=3):
    """Generate audio with retry logic and fallback options"""
    
    for attempt in range(max_retries):
        try:
            print(f"Audio generation attempt {attempt + 1}/{max_retries}...")
            await asyncio.wait_for(generate_audio(text, filename), timeout=60)
            print("Audio generated successfully!")
            return True
            
        except asyncio.TimeoutError:
            print(f"Attempt {attempt + 1} timed out after 60 seconds")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3  # Wait 3, 6, 9 seconds
                print(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
            
        except Exception as e:
            print(f"Audio generation error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"Waiting {wait_time} seconds before retry...")
                await asyncio.sleep(wait_time)
    
    print("All audio generation attempts failed")
    return False

# Alternative audio generation using different approach
async def fallback_audio_generation(text, filename):
    """Fallback audio generation with different settings"""
    try:
        print("Trying fallback audio generation...")
        
        # Try with different voice
        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
        await asyncio.wait_for(communicate.save(filename), timeout=45)
        
        print("Fallback audio generation successful!")
        return True
        
    except Exception as e:
        print(f"Fallback audio generation failed: {e}")
        
        # Try gTTS as final fallback
        try:
            from gtts import gTTS
            print("Trying gTTS as final fallback...")
            
            tts = gTTS(text=text, lang='en', slow=False)
            # Convert mp3 to wav if needed
            if filename.endswith('.wav'):
                temp_file = filename.replace('.wav', '_temp.mp3')
                tts.save(temp_file)
                
                # Convert mp3 to wav using pydub
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_mp3(temp_file)
                    audio.export(filename, format="wav")
                    os.remove(temp_file)
                    print("gTTS generation successful!")
                    return True
                except ImportError:
                    print("pydub not installed, saving as mp3")
                    os.rename(temp_file, filename.replace('.wav', '.mp3'))
                    return True
            else:
                tts.save(filename)
                print("gTTS generation successful!")
                return True
                
        except ImportError:
            print("gTTS not available. Install with: pip install gtts")
        except Exception as gtts_error:
            print(f"gTTS failed: {gtts_error}")
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")

    args = parser.parse_args()
    SAMPLE_TOPIC = args.topic
    SAMPLE_FILE_NAME = "audio_tts.wav"
    VIDEO_SERVER = "pexel"

    print(f"[INFO] Topic: {SAMPLE_TOPIC}")
    
    # Step 1: Generate Script
    try:
        print("Generating script...")
        response = generate_script(SAMPLE_TOPIC)
        print("Script generated successfully!")
        print("Script: {}".format(response))
    except Exception as e:
        print(f"Script generation failed: {e}")
        sys.exit(1)

    # Step 2: Generate Audio with robust error handling
    async def audio_pipeline():
        # Try main audio generation
        success = await robust_audio_generation(response, SAMPLE_FILE_NAME)
        
        if not success:
            print("Trying fallback methods...")
            success = await fallback_audio_generation(response, SAMPLE_FILE_NAME)
        
        if not success:
            print("All audio generation methods failed!")
            print("   Troubleshooting tips:")
            print("   1. Check your internet connection")
            print("   2. Try using a VPN")
            print("   3. Install gTTS: pip install gtts pydub")
            print("   4. Update edge-tts: pip install --upgrade edge-tts")
            return False
        
        return True

    # Run audio generation
    audio_success = asyncio.run(audio_pipeline())
    
    if not audio_success:
        print("Cannot proceed without audio. Exiting.")
        sys.exit(1)

    # Step 3: Generate Timed Captions
    try:
        print("Generating timed captions...")
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        print("Timed captions generated successfully!")
        print(timed_captions)
    except Exception as e:
        print(f"Timed captions generation failed: {e}")
        sys.exit(1)

    # Step 4: Generate Search Terms
    try:
        print("Generating video search queries...")
        search_terms = getVideoSearchQueriesTimed(response, timed_captions)
        print("Search terms generated!")
        print(search_terms)
    except Exception as e:
        print(f"Search terms generation failed: {e}")
        search_terms = None

    # Step 5: Generate Background Videos
    background_video_urls = None
    if search_terms is not None:
        try:
            print("Generating background video URLs...")
            background_video_urls = generate_video_url(search_terms, VIDEO_SERVER)
            print("Background videos found!")
            print(background_video_urls)
        except Exception as e:
            print(f"Background video generation failed: {e}")
            print("Proceeding without background video")
    else:
        print("No background video (no search terms)")

    # Step 6: Merge Empty Intervals
    if background_video_urls is not None:
        try:
            background_video_urls = merge_empty_intervals(background_video_urls)
            print("Video intervals merged!")
        except Exception as e:
            print(f"Video interval merging failed: {e}")

    # Step 7: Render Final Video
    if background_video_urls is not None:
        try:
            print("Rendering final video...")
            video = get_output_media(SAMPLE_FILE_NAME, timed_captions, background_video_urls, VIDEO_SERVER)
            print("Video rendering completed!")
            print(f"Final video: {video}")
        except Exception as e:
            print(f"Video rendering failed: {e}")
            print("Final video generation unsuccessful")
    else:
        print("No video generated (no background videos available)")