
# 🎬 Text-to-Video AI Generator

Turn a simple topic like `"Artificial Intelligence"` into a fully rendered short video with AI-generated script, narration, captions, and background clips — all from a simple Streamlit interface.  
Powered by OpenAI / Groq, Edge TTS, Whisper, MoviePy, and more. 🔥

---

## 🚀 Features

- ✍️ Script generation using OpenAI or Groq (LLaMA-3)
- 🗣️ Audio narration using Edge TTS
- 🕒 Timed captions auto-generated using Whisper
- 🎞️ Auto-fetched background videos
- 🎬 Final video rendering using MoviePy + ImageMagick
- 🖥️ Interactive frontend via Streamlit
- 📥 Downloadable output video

---

## 🧰 Tech Stack

| Layer         | Tools Used                                       |
|---------------|--------------------------------------------------|
| Script AI     | OpenAI GPT-4o or Groq LLaMA-3                    |
| Audio TTS     | Microsoft Edge TTS (`edge-tts`)                  |
| Captions      | `whisper-timestamped` + `whisper` (GitHub)       |
| Video Editing | `moviepy`, `ffmpeg`, `ImageMagick`               |
| UI            | `streamlit`                                      |

---

## 📦 Requirements

Install all dependencies:

```bash
pip install -r requirements.txt
````

Or install individually:

```bash
pip install openai groq edge-tts streamlit moviepy whisper_timestamped python-dotenv
pip install git+https://github.com/openai/whisper.git
```

---

## ⚙️ Additional Installations

### 🔧 FFmpeg

* Download from: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
* Extract and add the `bin/` folder to your system `PATH`.

### 🧙 ImageMagick

* Download from: [https://imagemagick.org/script/download.php](https://imagemagick.org/script/download.php)
* During setup:

  * ✅ Check **“Install legacy utilities”**
  * ✅ Check **“Add to system PATH”**
* In code, set the path:

```python
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"D:\ImageMagick-7.1.1-Q16\magick.exe"})
```

---

## 🔐 API Keys

Create a `.env` file in your project root:

```
OPENAI_API_KEY=your_openai_key_here
GROQ_API_KEY=your_groq_key_here
PEXELS_KEY=your_pexels_key_if_used
```

---

## 🧪 How to Run

```bash
streamlit run streamlit_app.py
```

Access the app at:
[http://localhost:8501](http://localhost:8501)

---

## 🛠️ Folder Structure

```
📦 Text-To-Video-AI/
├── app.py
├── streamlit_app.py
├── utility/
│   ├── script/
│   ├── audio/
│   ├── captions/
│   ├── video/
│   └── render/
├── rendered_video.mp4
├── .env
├── requirements.txt
└── README.md
```

---

## 📸 Screenshots

> Add a few screenshots/gifs here showing:
>
> ![image](https://github.com/user-attachments/assets/2e362167-b970-40f9-b90f-478cb9101f8d)

> ![image](https://github.com/user-attachments/assets/c3e6a45a-a10b-483a-bcb1-3737ebfd8908)

---

## 🙌 Credits

* [OpenAI](https://openai.com/)
* [Groq](https://console.groq.com/)
* [MoviePy](https://zulko.github.io/moviepy/)
* [Edge-TTS](https://github.com/rany2/edge-tts)
* [Streamlit](https://streamlit.io/)
* [ImageMagick](https://imagemagick.org/)

---

## 📬 Contact

Built with ❤️ by \HANISH
Pull requests & ⭐ stars welcome!
