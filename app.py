import os
import re
import subprocess
import streamlit as st
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi
from PIL import Image

st.set_page_config(page_title="YouTube Title & Thumbnail Generator", layout="wide")

st.title("🎯 YouTube ऑटो टाइटल और थंबनेल जेनरेटर")
st.caption("YouTube लिंक डालें - टाइटल्स और थंबनेल फ्रेम्स एक ही जगह पाएं बिना फोन का डेटा खर्च किए।")

# साइडबार में API Key का इनपुट
with st.sidebar:
    st.header("⚙️ सेटिंग्स")
    gemini_api_key = st.text_input("Gemini API Key डालें:", type="password")
    st.markdown("[Google AI Studio से फ्री Key प्राप्त करें](https://aistudio.google.com/)")

# वीडियो ID निकालने का फंक्शन
def extract_video_id(url):
    pattern = r"(?:v=|\/|youtu\.be\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

# ट्रांसक्रिप्ट निकालने का फंक्शन
def get_transcript(video_id):
    try:
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['hi', 'en'])
        text = " ".join([item['text'] for item in transcript_data])
        return text[:4000]  # शुरुआती मुख्य टेक्स्ट
    except Exception:
        return None

# लो-रेजोल्यूशन में फ्रेम्स निकालने का फंक्शन (कम से कम डेटा खर्च)
def extract_frames(video_url, num_frames=6):
    os.makedirs("temp_frames", exist_ok=True)
    for f in os.listdir("temp_frames"):
        os.remove(os.path.join("temp_frames", f))

    # yt-dlp से केवल 360p स्ट्रीम का सीधा URL निकालना (फाइल डाउनलोड नहीं होगी)
    cmd_url = f'yt-dlp -f "worst[ext=mp4]/worst" -g "{video_url}"'
    stream_url = subprocess.check_output(cmd_url, shell=True).decode('utf-8').strip()

    # ffmpeg द्वारा वीडियो में से फ्रेम्स निकालना
    cmd_ffmpeg = f'ffmpeg -ss 00:00:30 -i "{stream_url}" -vf "fps=1/45" -frames:v {num_frames} temp_frames/frame_%02d.jpg -y'
    subprocess.run(cmd_ffmpeg, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    frames = [os.path.join("temp_frames", f) for f in sorted(os.listdir("temp_frames")) if f.endswith(".jpg")]
    return frames

# मुख्य इनपुट
url_input = st.text_input("अपनी YouTube वीडियो का लिंक यहाँ पेस्ट करें:")

if st.button("🚀 जनरेट करें", type="primary"):
    if not url_input:
        st.warning("कृपया पहले YouTube वीडियो का लिंक डालें।")
    elif not gemini_api_key:
        st.warning("कृपया साइडबार में अपनी Gemini API Key डालें।")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("अमान्य YouTube लिंक। कृपया सही लिंक डालें।")
        else:
            with st.spinner("1/2: वायरल टाइटल्स बनाए जा रहे हैं..."):
                transcript = get_transcript(video_id)
                client = genai.Client(api_key=gemini_api_key)
                
                prompt = f"""
                तुम एक एक्सपर्ट YouTube स्ट्रैटेजिस्ट हो। 
                नीचे दी गई वीडियो ट्रांसक्रिप्ट को समझो और 5 बहुत ही कैची, हाई-CTR और क्लिकेबल टाइटल्स (हिंदी/हिंग्लिश मिक्स) बनाओ。
                
                ट्रांसक्रिप्ट: {transcript if transcript else 'ट्रांसक्रिप्ट उपलब्ध नहीं है, वीडियो विषय के अनुसार आकर्षक टाइटल दें。'}
                
                केवल 5 टाइटल्स की नंबर लिस्ट बनाकर दो。
                """
                response = client.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=prompt
                )

            st.subheader("📝 तैयार किए गए वायरल टाइटल्स:")
            st.write(response.text)

            st.divider()

            with st.spinner("2/2: वीडियो में से बेस्ट थंबनेल फ्रेम्स निकाले जा रहे हैं..."):
                try:
                    frames = extract_frames(url_input)
                    st.subheader("🖼️ बेस्ट थंबनेल फ्रेम्स (इन्हें डाउनलोड करके इस्तेमाल करें):")
                    
                    cols = st.columns(3)
                    for idx, frame_path in enumerate(frames):
                        img = Image.open(frame_path)
                        with cols[idx % 3]:
                            st.image(img, use_container_width=True)
                            with open(frame_path, "rb") as file:
                                st.download_button(
                                    label=f"फ्रेम {idx+1} डाउनलोड करें",
                                    data=file,
                                    file_name=f"thumbnail_frame_{idx+1}.jpg",
                                    mime="image/jpeg",
                                    key=f"dl_{idx}"
                                )
                except Exception as e:
                    st.error("फ्रेम्स निकालने में समस्या आई। सुनिश्चित करें कि वीडियो पब्लिक या अनलिस्टेड है。")
                  
