import streamlit as st
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Environment variables
from dotenv import load_dotenv
load_dotenv()

# Asyncio fix for Streamlit
import asyncio
import nest_asyncio
nest_asyncio.apply()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import utilities
try:
    from utility.script.script_generator import generate_script
    from utility.audio.audio_generator import generate_audio
    from utility.captions.timed_captions_generator import generate_timed_captions
    from utility.video.background_video_generator import generate_video_url
    from utility.render.render_engine import get_output_media
    from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
    import edge_tts
    import whisper_timestamped as whisper
    from gtts import gTTS
    from pydub import AudioSegment
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Check OPENAI_API_KEY
if not os.getenv('OPENAI_API_KEY'):
    st.error("⚠️ OPENAI_API_KEY not found in environment variables!")
    st.stop()

# Page config
st.set_page_config(page_title="AI Text-to-Video Generator", page_icon="🎬", layout="wide")

# CSS
st.markdown("""
<style>
/* Main header */
.main-header {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);padding: 2rem;border-radius: 10px;margin-bottom: 2rem;text-align: center;color: white;}
/* Feature cards */
.feature-card {background: #f8f9fa;padding: 1.5rem;border-radius: 10px;border-left: 4px solid #667eea;margin: 1rem 0;box-shadow: 0 2px 4px rgba(0,0,0,0.1);color: black;}
/* Progress steps */
.progress-step {background: #e3f2fd;padding: 1rem;border-radius: 8px;margin: 0.5rem 0;border-left: 3px solid #2196f3;color: black;}
.success-step {background: #e8f5e8;border-left-color: #4caf50;color:black;}
.error-step {background: #ffebee;border-left-color: #f44336;}
/* Buttons */
.stButton > button {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);color: white;border: none;padding: 0.75rem 2rem;border-radius: 25px;font-weight: 600;width: 100%;transition: all 0.3s ease;}
.stButton > button:hover {transform: translateY(-2px);box-shadow: 0 4px 8px rgba(0,0,0,0.2);}
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🎬 AI Text-to-Video Generator</h1>
    <p>Transform your ideas into engaging videos with AI-powered script, TTS, captions, and video editing</p>
</div>
""", unsafe_allow_html=True)

# Session state
if 'status' not in st.session_state:
    st.session_state.status = 'ready'
if 'files' not in st.session_state:
    st.session_state.files = {}
if 'logs' not in st.session_state:
    st.session_state.logs = []

# Sidebar
with st.sidebar:
    st.header("🎯 Settings")
    # Voice selection
    voice_options = ["en-US-AriaNeural","en-US-JennyNeural","en-US-GuyNeural","en-US-DavisNeural","en-US-AmberNeural"]
    selected_voice = st.selectbox("Voice", voice_options)
    # Advanced
    with st.expander("⚙️ Advanced"):
        max_retries = st.slider("Max Retries", 1, 5, 3)
        timeout_duration = st.slider("Timeout (s)", 30, 120, 60)

# Input
topic = st.text_area("Enter your video topic:", height=100, placeholder="e.g., The future of AI in healthcare")
generate_button = st.button("🚀 Generate Video", disabled=(not topic or st.session_state.status=='generating'))

# Utilities
async def generate_audio_async(text, filename):
    """Robust audio generation: Edge TTS → gTTS fallback"""
    # Edge TTS
    for attempt in range(max_retries):
        try:
            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(filename)
            st.session_state.logs.append("Audio generated via Edge TTS")
            return True
        except Exception as e:
            st.session_state.logs.append(f"Edge TTS failed attempt {attempt+1}: {e}")
            await asyncio.sleep(3*(attempt+1))
    # gTTS fallback
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        temp_mp3 = filename.replace('.wav','_temp.mp3')
        tts.save(temp_mp3)
        audio = AudioSegment.from_mp3(temp_mp3)
        audio.export(filename, format="wav")
        os.remove(temp_mp3)
        st.session_state.logs.append("Audio generated via gTTS fallback")
        return True
    except Exception as e:
        st.session_state.logs.append(f"gTTS failed: {e}")
        return False

def update_step(name, status, message):
    """Display step status"""
    container = st.empty()
    color_class = 'success-step' if status=='success' else 'error-step' if status=='error' else ''
    container.markdown(f"""
    <div class="progress-step {color_class}">
        <strong>{'✅' if status=='success' else '❌' if status=='error' else '⏳'} {name.title()}</strong>: {message}
    </div>
    """, unsafe_allow_html=True)

async def run_pipeline(topic_input):
    """Main pipeline"""
    try:
        update_step('Script', 'processing','Generating script...')
        script = generate_script(topic_input)
        st.session_state.files['script'] = script
        update_step('Script','success','Script generated')
        
        update_step('Audio','processing','Generating audio...')
        audio_file = f"audio_{int(time.time())}.wav"
        success = await generate_audio_async(script, audio_file)
        if not success: 
            update_step('Audio','error','Audio generation failed, check logs')
            return False
        st.session_state.files['audio'] = audio_file
        update_step('Audio','success','Audio generated')
        
        update_step('Captions','processing','Generating timed captions...')
        captions = generate_timed_captions(audio_file)
        st.session_state.files['captions'] = captions
        update_step('Captions','success','Captions generated')
        
        update_step('Search','processing','Generating search queries...')
        try:
            search_terms = getVideoSearchQueriesTimed(script, captions)
        except Exception:
            # fallback search terms
            search_terms = [word for word in script.split() if len(word)>3][:25]
        st.session_state.files['search_terms'] = search_terms
        update_step('Search','success','Search queries ready')
        
        update_step('Video','processing','Finding background videos...')
        try:
            background_videos = generate_video_url(search_terms,'pexel')
            background_videos = merge_empty_intervals(background_videos)
        except Exception:
            background_videos = None
        st.session_state.files['background_videos'] = background_videos
        update_step('Video','success','Background videos ready')
        
        update_step('Render','processing','Rendering final video...')
        try:
            final_video = get_output_media(audio_file,captions,background_videos,'pexel')
            st.session_state.files['final_video'] = final_video
        except Exception:
            final_video = None
        update_step('Render','success','Video rendered' if final_video else 'Video rendering skipped')
        return True
    except Exception as e:
        st.error(f"Pipeline error: {e}")
        return False

# Trigger generation
if generate_button and topic:
    st.session_state.status='generating'
    asyncio.run(run_pipeline(topic))
    st.session_state.status='completed'
    st.experimental_rerun()

# Results
if st.session_state.status=='completed':
    st.subheader("📝 Script")
    st.text_area("Script", st.session_state.files.get('script',''), height=200, disabled=True)
    
    st.subheader("🎵 Audio")
    if 'audio' in st.session_state.files and os.path.exists(st.session_state.files['audio']):
        st.audio(st.session_state.files['audio'])
    
    st.subheader("🎬 Final Video")
    if 'final_video' in st.session_state.files and os.path.exists(st.session_state.files['final_video']):
        st.video(st.session_state.files['final_video'])
        with open(st.session_state.files['final_video'],'rb') as f:
            st.download_button("📥 Download Video", f.read(), file_name=f"video_{int(time.time())}.mp4", mime="video/mp4")
    
    if st.button("🔄 Generate Another"):
        st.session_state.status='ready'
        st.session_state.files={}
        st.session_state.status = 'completed'
# Streamlit automatically reruns when a widget or session_state changes
