import edge_tts
import asyncio
import aiohttp

# Your original function with timeout protection
async def generate_audio(text, outputFilename):
    """
    Generate audio using Edge TTS with timeout protection
    Keeps your original voice: en-AU-WilliamNeural
    """
    try:
        communicate = edge_tts.Communicate(text, "en-AU-WilliamNeural")
        # Add timeout to prevent hanging
        await asyncio.wait_for(communicate.save(outputFilename), timeout=60)
        
    except asyncio.TimeoutError:
        print("⚠️ Connection timed out, trying with different settings...")
        # Retry with shorter timeout and different approach
        await generate_audio_retry(text, outputFilename)
        
    except aiohttp.ServerTimeoutError:
        print("⚠️ Server timeout, retrying...")
        await generate_audio_retry(text, outputFilename)
        
    except Exception as e:
        print(f"⚠️ Error with primary method: {e}")
        await generate_audio_retry(text, outputFilename)

# Retry function with multiple attempts
async def generate_audio_retry(text, outputFilename, max_attempts=3):
    """
    Retry audio generation with fallback voices
    """
    # Keep your preferred Australian voice first, then add backups
    voices = [
        "en-AU-WilliamNeural",  # Your original choice
        "en-AU-NatashaNeural",  # Another Australian voice
        "en-US-AriaNeural",     # US backup
        "en-GB-RyanNeural"      # UK backup
    ]
    
    for attempt in range(max_attempts):
        for voice in voices:
            try:
                print(f"Attempt {attempt + 1}: Trying {voice}")
                communicate = edge_tts.Communicate(text, voice)
                
                # Try with progressively longer timeouts
                timeout = 30 + (attempt * 15)  # 30s, 45s, 60s
                await asyncio.wait_for(communicate.save(outputFilename), timeout=timeout)
                
                print(f"✅ Success with {voice}")
                return
                
            except (asyncio.TimeoutError, aiohttp.ServerTimeoutError):
                print(f"⚠️ Timeout with {voice}")
                continue
            except Exception as e:
                print(f"⚠️ Error with {voice}: {str(e)[:50]}...")
                continue
        
        # Wait between full attempts
        if attempt < max_attempts - 1:
            wait_time = (attempt + 1) * 2
            print(f"Waiting {wait_time} seconds before next attempt...")
            await asyncio.sleep(wait_time)
    
    # If all Edge TTS attempts fail, try gTTS as final backup
    print("🔄 All Edge TTS attempts failed, trying gTTS backup...")
    if not generate_audio_gtts_backup(text, outputFilename):
        raise Exception("All audio generation methods failed")

# Simple gTTS backup (optional - only used if Edge TTS completely fails)
def generate_audio_gtts_backup(text, outputFilename):
    """
    Simple gTTS backup - only used if Edge TTS completely fails
    """
    try:
        from gtts import gTTS
        print("Using gTTS as backup...")
        
        tts = gTTS(text=text, lang='en', slow=False)
        
        # Handle wav format
        if outputFilename.endswith('.wav'):
            # Save as mp3 first
            mp3_file = outputFilename.replace('.wav', '.mp3')
            tts.save(mp3_file)
            
            # Try to convert to wav
            try:
                from pydub import AudioSegment
                audio = AudioSegment.from_mp3(mp3_file)
                audio.export(outputFilename, format="wav")
                import os
                os.remove(mp3_file)
            except ImportError:
                print("⚠️ Keeping as mp3 (install pydub for wav conversion)")
                import os
                os.rename(mp3_file, outputFilename.replace('.wav', '.mp3'))
        else:
            tts.save(outputFilename)
        
        print("✅ gTTS backup successful")
        return True
        
    except ImportError:
        print("❌ gTTS not available (install with: pip install gtts)")
        return False
    except Exception as e:
        print(f"❌ gTTS backup failed: {e}")
        return False
