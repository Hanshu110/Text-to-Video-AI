import streamlit as st
import asyncio
import os
import sys
import time
import json
from datetime import datetime
import subprocess
import threading
from pathlib import Path

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import your utility functions
try:
    from utility.script.script_generator import generate_script
    from utility.audio.audio_generator import generate_audio
    from utility.captions.timed_captions_generator import generate_timed_captions
    from utility.video.background_video_generator import generate_video_url
    from utility.render.render_engine import get_output_media
    from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
    import edge_tts
    import whisper_timestamped as whisper
except ImportError as e:
    st.error(f"Import error: {e}")
    st.error("Please make sure all dependencies are installed. Check requirements.txt")
    
# Verify environment variables are loaded
if not os.getenv('OPENAI_API_KEY'):
    st.error("⚠️ OPENAI_API_KEY not found in environment variables!")
    st.error("Please make sure your .env file is in the project root and contains:")
    st.code("OPENAI_API_KEY=your_api_key_here")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="AI Text-to-Video Generator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: black;
    }
    
    .progress-step {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #2196f3;
        color: black;
    }
    
    .success-step {
        background: #e8f5e8;
        border-left-color: #4caf50;
        color:black;
    }
    
    .error-step {
        background: #ffebee;
        border-left-color: #f44336;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>🎬 AI Text-to-Video Generator</h1>
    <p>Transform your ideas into engaging videos with AI-powered script generation, voice synthesis, and automatic video editing</p>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'generation_status' not in st.session_state:
    st.session_state.generation_status = 'ready'
if 'generated_files' not in st.session_state:
    st.session_state.generated_files = {}
if 'progress_logs' not in st.session_state:
    st.session_state.progress_logs = []

# Sidebar
with st.sidebar:
    st.header("🎯 Configuration")
    
    # Audio settings
    st.subheader("🎵 Audio Settings")
    voice_options = [
        "en-US-AriaNeural",
        "en-US-JennyNeural", 
        "en-US-GuyNeural",
        "en-US-DavisNeural",
        "en-US-AmberNeural"
    ]
    selected_voice = st.selectbox("Voice", voice_options)
    
    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        max_retries = st.slider("Max Retries", 1, 5, 3)
        timeout_duration = st.slider("Timeout (seconds)", 30, 120, 60)

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💡 Create Your Video")
    
    # Topic input
    topic = st.text_area(
        "Enter your video topic or script idea:",
        placeholder="e.g., 'The future of renewable energy and its impact on climate change'",
        height=100,
        help="Be specific and detailed for better results"
    )
    
    # Generate button
    generate_button = st.button("🚀 Generate Video", disabled=(not topic or st.session_state.generation_status == 'generating'))
    
    if generate_button and topic:
        st.session_state.generation_status = 'generating'
        st.session_state.generated_files = {}
        st.session_state.progress_logs = []
        st.rerun()

with col2:
    st.header("🎬 Features")
    
    features = [
        ("🤖 AI Script Generation", "Intelligent content creation"),
        ("🎙️ Voice Synthesis", "High-quality text-to-speech"),
        ("📝 Auto Captions", "Timed subtitle generation"),
        ("🎥 Video Matching", "Smart background video selection"),
        ("🎬 Auto Editing", "Professional video compilation")
    ]
    
    for feature, description in features:
        st.markdown(f"""
        <div class="feature-card">
            <h4>{feature}</h4>
            <p>{description}</p>
        </div>
        """, unsafe_allow_html=True)

# Video generation pipeline
if st.session_state.generation_status == 'generating':
    st.header("🔄 Generation in Progress")
    
    # Progress container
    progress_container = st.container()
    
    # Status containers
    status_containers = {
        'script': st.empty(),
        'audio': st.empty(),
        'captions': st.empty(),
        'search': st.empty(),
        'video': st.empty(),
        'render': st.empty()
    }
    
    # Progress bar
    progress_bar = st.progress(0)
    overall_status = st.empty()
    
    async def robust_audio_generation(text, filename, max_retries=3):
        """Generate audio with retry logic"""
        for attempt in range(max_retries):
            try:
                st.session_state.progress_logs.append(f"Audio generation attempt {attempt + 1}/{max_retries}")
                await asyncio.wait_for(generate_audio(text, filename), timeout=timeout_duration)
                return True
            except Exception as e:
                st.session_state.progress_logs.append(f"Audio attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep((attempt + 1) * 3)
        return False
    
    async def fallback_audio_generation(text, filename):
        """Fallback audio generation"""
        try:
            st.session_state.progress_logs.append("Trying fallback audio generation...")
            communicate = edge_tts.Communicate(text, selected_voice)
            await communicate.save(filename)
            return True
        except Exception as e:
            st.session_state.progress_logs.append(f"Fallback audio failed: {str(e)}")
            return False
    
    def update_status(step, status, message):
        """Update step status"""
        if status == 'success':
            status_containers[step].markdown(f"""
            <div class="progress-step success-step">
                <strong>✅ {step.title()}</strong>: {message}
            </div>
            """, unsafe_allow_html=True)
        elif status == 'error':
            status_containers[step].markdown(f"""
            <div class="progress-step error-step">
                <strong>❌ {step.title()}</strong>: {message}
            </div>
            """, unsafe_allow_html=True)
        else:
            status_containers[step].markdown(f"""
            <div class="progress-step">
                <strong>⏳ {step.title()}</strong>: {message}
            </div>
            """, unsafe_allow_html=True)
    
    # Main generation pipeline
    async def generation_pipeline():
        try:
            # Step 1: Generate Script
            update_status('script', 'processing', 'Generating script...')
            progress_bar.progress(10)
            
            response = generate_script(topic)
            st.session_state.generated_files['script'] = response
            update_status('script', 'success', 'Script generated successfully!')
            progress_bar.progress(20)
            
            # Step 2: Generate Audio
            update_status('audio', 'processing', 'Generating audio...')
            filename = f"audio_tts_{int(time.time())}.wav"
            
            success = await robust_audio_generation(response, filename)
            if not success:
                success = await fallback_audio_generation(response, filename)
            
            if success:
                st.session_state.generated_files['audio'] = filename
                update_status('audio', 'success', 'Audio generated successfully!')
                progress_bar.progress(40)
            else:
                update_status('audio', 'error', 'Audio generation failed!')
                return False
            
            # Step 3: Generate Captions
            update_status('captions', 'processing', 'Generating timed captions...')
            progress_bar.progress(50)
            
            timed_captions = generate_timed_captions(filename)
            st.session_state.generated_files['captions'] = timed_captions
            update_status('captions', 'success', 'Captions generated successfully!')
            progress_bar.progress(60)
            
            # Step 4: Generate Search Terms
            update_status('search', 'processing', 'Generating video search queries...')
            progress_bar.progress(70)
            
            search_terms = getVideoSearchQueriesTimed(response, timed_captions)
            st.session_state.generated_files['search_terms'] = search_terms
            update_status('search', 'success', 'Search terms generated!')
            progress_bar.progress(80)
            
            # Step 5: Generate Background Videos
            update_status('video', 'processing', 'Finding background videos...')
            
            background_video_urls = generate_video_url(search_terms, video_server)
            background_video_urls = merge_empty_intervals(background_video_urls)
            st.session_state.generated_files['background_videos'] = background_video_urls
            update_status('video', 'success', 'Background videos found!')
            progress_bar.progress(90)
            
            # Step 6: Render Final Video
            update_status('render', 'processing', 'Rendering final video...')
            
            final_video = get_output_media(filename, timed_captions, background_video_urls, video_server)
            st.session_state.generated_files['final_video'] = final_video
            update_status('render', 'success', 'Video rendered successfully!')
            progress_bar.progress(100)
            
            return True
            
        except Exception as e:
            st.error(f"Generation failed: {str(e)}")
            st.session_state.progress_logs.append(f"Error: {str(e)}")
            return False
    
    # Run the pipeline
    if asyncio.run(generation_pipeline()):
        st.session_state.generation_status = 'completed'
        st.rerun()
    else:
        st.session_state.generation_status = 'failed'
        st.rerun()

# Results section
if st.session_state.generation_status == 'completed':
    st.header("🎉 Generation Complete!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Generated Script")
        if 'script' in st.session_state.generated_files:
            st.text_area("Script", st.session_state.generated_files['script'], height=200, disabled=True)
    
    with col2:
        st.subheader("🎵 Audio File")
        if 'audio' in st.session_state.generated_files:
            audio_file = st.session_state.generated_files['audio']
            if os.path.exists(audio_file):
                st.audio(audio_file)
            else:
                st.warning("Audio file not found")
    
    # Video player
    st.subheader("🎬 Final Video")
    if 'final_video' in st.session_state.generated_files:
        video_file = st.session_state.generated_files['final_video']
        if os.path.exists(video_file):
            st.video(video_file)
            
            # Download button
            with open(video_file, 'rb') as f:
                st.download_button(
                    label="📥 Download Video",
                    data=f.read(),
                    file_name=f"generated_video_{int(time.time())}.mp4",
                    mime="video/mp4"
                )
        else:
            st.warning("Video file not found")
    
    # Reset button
    if st.button("🔄 Generate Another Video"):
        st.session_state.generation_status = 'ready'
        st.session_state.generated_files = {}
        st.session_state.progress_logs = []
        st.rerun()

elif st.session_state.generation_status == 'failed':
    st.error("❌ Generation failed. Please check the logs and try again.")
    
    if st.button("🔄 Try Again"):
        st.session_state.generation_status = 'ready'
        st.session_state.generated_files = {}
        st.session_state.progress_logs = []
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem; color: #666;">
    <p>🚀 AI Text-to-Video Generator | Built with Streamlit</p>
    <p>Transform your ideas into engaging videos with the power of AI</p>
</div>
""", unsafe_allow_html=True)
