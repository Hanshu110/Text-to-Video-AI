import streamlit as st
import subprocess
import os

st.set_page_config(page_title="🎬 Text-to-Video Generator", layout="centered")

st.title("🎥 AI Text-to-Video Generator")
st.markdown("Turn any topic into a video using AI — script, audio, visuals & captions 🎯")

# User input
topic = st.text_input("📌 Enter a topic (e.g., Artificial Intelligence)", "")

if st.button("🚀 Generate Video"):
    if not topic.strip():
        st.warning("Please enter a topic to generate a video.")
    else:
        with st.spinner("🧠 Generating video from AI... please wait. This may take 1–3 minutes."):
            result = subprocess.run(
                ["python", "app.py", topic],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

        # Show logs
        with st.expander("📜 View processing log"):
            st.markdown("#### ✅ Standard Output:")
            st.code(result.stdout or "No output", language="text")

            st.markdown("#### ⚠️ Error Log (if any):")
            st.code(result.stderr or "No errors", language="text")

        # Show video if available
        if os.path.exists("rendered_video.mp4"):
            st.success("✅ Video rendered successfully!")
            st.video("rendered_video.mp4")

            st.markdown("""
                <style>
                .stDownloadButton button {
                    background-color: #00c6ff;
                    color: white;
                    font-weight: bold;
                    border-radius: 10px;
                    padding: 0.75em 1.5em;
                    transition: all 0.3s ease;
                }
                .stDownloadButton button:hover {
                    background-color: #007acc;
                    transform: scale(1.05);
                }
                </style>
            """, unsafe_allow_html=True)

            with open("rendered_video.mp4", "rb") as file:
                st.download_button(
                    label="⬇️ Download Final Video",
                    data=file,
                    file_name="ai_generated_video.mp4",
                    mime="video/mp4",
                )
        else:
            st.error("❌ Video generation failed. Please check the logs.")