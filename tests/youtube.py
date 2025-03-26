from yt_dlp import YoutubeDL
import json

URL = "https://www.youtube.com/watch?v=NvX9EsqEeuU"
ydl_opts = {'format': 'best[height<=720]'}
with YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(URL, download=False)
    if not info:
        print("No video info found")
    else:
        title = info.get("title", None)
        duration = info.get("duration", None)
        print(f"Descargando: {title} ({duration} segundos)")
        ydl.download([URL])
            