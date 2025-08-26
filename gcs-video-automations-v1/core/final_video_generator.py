#!/usr/bin/env python3
"""
Trivia video generator - Final Version

This script is a faithful implementation of the user-provided reference script.
It generates a trivia video with the correct visual styling, fonts, and animations.
"""
import asyncio
import csv
import json
import math
import os
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required. Try: pip install Pillow", file=sys.stderr)
    raise

try:
    from google.cloud import storage, texttospeech
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

# Add src directory to path for local execution
backend_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if backend_src_path not in sys.path:
    sys.path.insert(0, backend_src_path)

# --- Configuration ---
ASSETS_DIR = "cloud_assets"  # Local temp directory for cloud assets
DEFAULT_OUT_DIR = "output_final"
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"  # Bucket for job CSV files
TTS_VOICE = "en-US-Neural2-F"
TTS_SPEED = 1.0

DEFAULT_FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
DEFAULT_BOLD_FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
DEFAULT_THIN_FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/HelveticaNeue-Light.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]

@dataclass
class SlideBoxes:
    BASE_W: int = 1920
    BASE_H: int = 1080
    question_px: Tuple[int, int, int, int] = (300, 265, 1332, 227)
    answer_a_px: Tuple[int, int, int, int] = (378, 569, 523, 110)
    answer_b_px: Tuple[int, int, int, int] = (1014, 568, 526, 113)
    answer_c_px: Tuple[int, int, int, int] = (379, 768, 517, 106)
    answer_d_px: Tuple[int, int, int, int] = (1018, 770, 519, 107)
    timer_px: Tuple[int, int, int, int] = (597, 114, 713, 126)
    correct_px: Tuple[int, int, int, int] = (576, 486, 759, 157)

# --- Utility Functions ---
def run(cmd: List[str]):
    log_path = os.path.join(DEFAULT_OUT_DIR, "ffmpeg_log.txt")
    print("$", " ".join(shlex.quote(c) for c in cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        with open(log_path, "a") as f: f.write(proc.stdout + proc.stderr)
    except subprocess.CalledProcessError as e:
        with open(log_path, "a") as f: f.write(e.stdout + e.stderr)
        print(f"FFmpeg command failed. Full log at: {log_path}")
        raise RuntimeError(f"Command failed with exit code {e.returncode}") from e

def ffprobe_wh(video_path: str) -> Tuple[int, int]:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]).decode("utf-8").strip()
    return tuple(map(int, out.split("x")))

def get_audio_duration(path: str) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", path]).decode("utf-8").strip()
    return float(out)

def pick_font(candidates: List[str]) -> str:
    for cand in candidates:
        if os.path.exists(cand): return cand
    raise FileNotFoundError(f"No usable font found in candidates: {candidates}")

def scale_box(box, w, h, base_w=1920, base_h=1080):
    l, t, bw, bh = box
    return int(l * w / base_w), int(t * h / base_h), int(bw * w / base_w), int(bh * h / base_h)

def prepare_ext_clip(src_path: str, target_w: int, target_h: int, tmp_dir: str, name: str) -> str:
    """Re-encode an external clip to match target resolution, preserving aspect ratio."""
    out_path = os.path.join(tmp_dir, f"{name}.mp4")
    run([
        "ffmpeg", "-y",
        "-i", src_path,
        "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "48000",
        out_path,
    ])
    return out_path

def ensure_dir(p: str): Path(p).mkdir(parents=True, exist_ok=True)

# --- GCS, TTS, and Text Rendering ---
def download_gcs_asset(bucket_name, source, dest):
    if not GOOGLE_CLOUD_AVAILABLE: 
        raise RuntimeError("Google Cloud libraries not installed. Cannot download assets.")
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source)
        ensure_dir(os.path.dirname(dest))
        blob.download_to_filename(dest)
        print(f"  📥 Downloaded: {source}")
    except Exception as e:
        print(f"  ❌ Download FAILED for gs://{bucket_name}/{source}: {e}")
        raise FileNotFoundError(f"Failed to download required asset: gs://{bucket_name}/{source}") from e

def generate_google_tts(text, path):
    if not GOOGLE_CLOUD_AVAILABLE:
        raise RuntimeError("Google Cloud libraries not installed. Cannot generate TTS.")
    try:
        client = texttospeech.TextToSpeechClient()
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_config = texttospeech.VoiceSelectionParams(language_code="en-US", name=TTS_VOICE)
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=TTS_SPEED)
        response = client.synthesize_speech(input=synthesis_input, voice=voice_config, audio_config=audio_config)
        with open(path, "wb") as out: out.write(response.audio_content)
        return get_audio_duration(path)
    except Exception as e:
        print(f"  ❌ Google TTS FAILED for text: '{text[:30]}...': {e}")
        raise RuntimeError(f"Failed to generate TTS audio.") from e

def render_text_to_png(text, box_w, box_h, font_path, out_path, is_bold=False):
    padding_w, padding_h = int(box_w * 0.1), int(box_h * 0.1)
    text_area_w, text_area_h = box_w - 2 * padding_w, box_h - 2 * padding_h
    img = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def wrap(txt, font, max_w):
        words = txt.split(); lines, cur = [], [];
        for word in words:
            candidate = " ".join(cur + [word]).strip()
            if draw.textbbox((0,0), candidate, font=font)[2] <= max_w or not cur: cur.append(word)
            else: lines.append(" ".join(cur)); cur = [word]
        if cur: lines.append(" ".join(cur))
        return "\n".join(lines)

    def fit(txt, min_s, max_s):
        low, high = min_s, max_s; best_s, best_t = min_s, txt
        while low <= high:
            mid = (low + high) // 2
            font = ImageFont.truetype(font_path, mid)
            wrapped = wrap(txt, font, text_area_w)
            _, _, w, h = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=6)
            if w <= text_area_w and h <= text_area_h: best_s, best_t = mid, wrapped; low = mid + 1
            else: high = mid - 1
        return best_s, best_t

    font_size, wrapped = fit(text, 12, 120 if is_bold else 90)
    font = ImageFont.truetype(font_path, font_size)
    _, _, text_w, text_h = draw.multiline_textbbox((0,0), wrapped, font=font, spacing=6)
    x, y = padding_w + (text_area_w - text_w) / 2, padding_h + (text_area_h - text_h) / 2

    if is_bold: draw.multiline_text((x+2, y+2), wrapped, font=font, fill=(0,0,0,96), align="center", spacing=6)
    draw.multiline_text((x, y), wrapped, font=font, fill="#111111", align="center", spacing=6)
    img.save(out_path)

# --- Video Composition ---
def build_question_clip(idx, row, bg, fonts, w, h, tmp, out, boxes):
    q_text, a_text, b_text, c_text, d_text = row.get("question"), row.get("answer_a"), row.get("answer_b"), row.get("answer_c"), row.get("answer_d")
    tts_path = os.path.join(tmp, f"q_{idx}.mp3")
    tts_dur = generate_google_tts(f"{q_text} A: {a_text}. B: {b_text}. C: {c_text}. D: {d_text}.", tts_path)
    
    clip_dur, timer_start = tts_dur + 5.0, round(tts_dur, 3)
    
    bx_q, bx_a, bx_b, bx_c, bx_d, bx_tm = (scale_box(b, w, h) for b in (boxes.question_px, boxes.answer_a_px, boxes.answer_b_px, boxes.answer_c_px, boxes.answer_d_px, boxes.timer_px))
    
    q_png = os.path.join(tmp, f"q_{idx}.png"); render_text_to_png(q_text, bx_q[2], bx_q[3], fonts['bold'], q_png, is_bold=True)
    a_png = os.path.join(tmp, f"a_{idx}.png"); render_text_to_png(a_text, bx_a[2], bx_a[3], fonts['thin'], a_png)
    b_png = os.path.join(tmp, f"b_{idx}.png"); render_text_to_png(b_text, bx_b[2], bx_b[3], fonts['thin'], b_png)
    c_png = os.path.join(tmp, f"c_{idx}.png"); render_text_to_png(c_text, bx_c[2], bx_c[3], fonts['thin'], c_png)
    d_png = os.path.join(tmp, f"d_{idx}.png"); render_text_to_png(d_text, bx_d[2], bx_d[3], fonts['thin'], d_png)

    timer_vid, timer_png, tick_sfx = os.path.join(ASSETS_DIR, "slide_timer_bar_5s.mp4"), os.path.join(ASSETS_DIR, "slide_timer_bar_full_striped.png"), os.path.join(ASSETS_DIR, "ticking_clock_mechanical_5s.wav")
    
    vf = ";".join([
        f"[2:v]format=rgba,scale={bx_q[2]}:{bx_q[3]},fade=in:st=1:d=0.5:alpha=1[q]",
        f"[3:v]format=rgba,scale={bx_a[2]}:{bx_a[3]},fade=in:st=1:d=0.5:alpha=1[a]",
        f"[4:v]format=rgba,scale={bx_b[2]}:{bx_b[3]},fade=in:st=1:d=0.5:alpha=1[b]",
        f"[5:v]format=rgba,scale={bx_c[2]}:{bx_c[3]},fade=in:st=1:d=0.5:alpha=1[c]",
        f"[6:v]format=rgba,scale={bx_d[2]}:{bx_d[3]},fade=in:st=1:d=0.5:alpha=1[d]",
        f"[7:v]format=rgba,scale={bx_tm[2]}:{bx_tm[3]}[t_static]",
        f"[8:v]format=rgba,scale={bx_tm[2]}:{bx_tm[3]},trim=0:5,setpts=PTS+{timer_start}/TB[t_run]",
        f"[0:v][q]overlay={bx_q[0]}:{bx_q[1]}[v1]",
        f"[v1][a]overlay={bx_a[0]}:{bx_a[1]}[v2]",
        f"[v2][b]overlay={bx_b[0]}:{bx_b[1]}[v3]",
        f"[v3][c]overlay={bx_c[0]}:{bx_c[1]}[v4]",
        f"[v4][d]overlay={bx_d[0]}:{bx_d[1]}[v5]",
        f"[v5][t_static]overlay={bx_tm[0]}:{bx_tm[1]}:enable='lt(t,{timer_start})'[v6]",
        f"[v6][t_run]overlay={bx_tm[0]}:{bx_tm[1]}:enable='gte(t,{timer_start})'[v]"
    ])
    af = f"[1:a]apad=pad_dur=5[tts];[9:a]adelay={int(timer_start*1000)}|{int(timer_start*1000)}[tick];[tts][tick]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    
    out_path = os.path.join(out, f"q_{idx}.mp4")
    run(["ffmpeg", "-y", "-i", bg, "-i", tts_path, "-loop", "1", "-t", str(clip_dur), "-i", q_png, "-loop", "1", "-t", str(clip_dur), "-i", a_png, "-loop", "1", "-t", str(clip_dur), "-i", b_png, "-loop", "1", "-t", str(clip_dur), "-i", c_png, "-loop", "1", "-t", str(clip_dur), "-i", d_png, "-loop", "1", "-t", str(clip_dur), "-i", timer_png, "-i", timer_vid, "-i", tick_sfx, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(clip_dur), out_path])
    return out_path

def build_answer_clip(idx, row, template, fonts, w, h, tmp, out, boxes):
    correct_letter = row.get("correct_answer", "A").upper()
    correct_text = row.get(f"answer_{correct_letter.lower()}")
    tts_path = os.path.join(tmp, f"ans_{idx}.mp3")
    tts_dur = generate_google_tts(f"The correct answer is {correct_letter}: {correct_text}", tts_path)
    clip_dur = tts_dur + 1.0

    bx = scale_box(boxes.correct_px, w, h)
    correct_png = os.path.join(tmp, f"correct_{idx}.png"); render_text_to_png(correct_text, bx[2], bx[3], fonts['bold'], correct_png, is_bold=True)
    
    ding_sfx = os.path.join(ASSETS_DIR, "ding_correct_answer_long.wav")
    
    vf = f"[1:v]format=rgba,scale={bx[2]}:{bx[3]},fade=in:st=0.5:d=0.5:alpha=1[c];[0:v][c]overlay={bx[0]}:{bx[1]}[v]"
    af = f"[2:a]apad=pad_dur=1[tts];[3:a]atrim=duration=1.5[ding];[ding][tts]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    
    out_path = os.path.join(out, f"ans_{idx}.mp4")
    run(["ffmpeg", "-y", "-i", template, "-loop", "1", "-t", str(clip_dur), "-i", correct_png, "-i", tts_path, "-i", ding_sfx, "-filter_complex", f"{vf};{af}", "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", str(clip_dur), out_path])
    return out_path

# --- Main Execution ---
async def main(argv):
    ensure_dir(DEFAULT_OUT_DIR); ensure_dir(os.path.join(DEFAULT_OUT_DIR, "tmp")); ensure_dir(os.path.join(DEFAULT_OUT_DIR, "clips"))
    
    # --- Asset Management ---
    # Define assets to download from GCS
    gcs_asset_files = [ "1.mp4", "2.mp4", "3.mp4", "ding_correct_answer_long.wav", "ticking_clock_mechanical_5s.wav", "slide_timer_bar_5s.mp4", "slide_timer_bar_full_striped.png", "An_energetic_game_202508201332_sdz6d.mp4", "A_single_explosive_202508201347_hctna.mp4" ]
    
    print("📦 Downloading required assets from GCS...")
    for asset in gcs_asset_files:
        dest_path = os.path.join(ASSETS_DIR, asset)
        if not os.path.exists(dest_path):
            download_gcs_asset(GCS_ASSETS_BUCKET, f"{GCS_ASSET_BASE_PATH}/{asset}", dest_path)

    # --- Strict Asset Check ---
    all_required_assets = gcs_asset_files
    missing_assets = [f for f in all_required_assets if not os.path.exists(os.path.join(ASSETS_DIR, f))]
    if missing_assets:
        print("\n❌ ERROR: Incomplete asset list. The following required files are missing:")
        for missing in missing_assets:
            print(f"  - {missing}")
        sys.exit(1)
    print("✅ All assets are ready.")

    # Get Questions
    try:
        from gemini_feeder import FeederRequest, GeminiFeeder
        api_key = os.environ.get("GEMINI_API_KEY")
        feeder = GeminiFeeder(api_key=api_key)
        # Simplified local run for now
        csv_path = os.path.join(DEFAULT_OUT_DIR, "tmp", "gemini.csv")
        with open(csv_path, "w") as f:
            f.write("question,answer_a,answer_b,answer_c,answer_d,correct_answer\n")
            f.write('"Which sport is known as ""the king of sports""?","Basketball","Baseball","Tennis","Soccer","D"\n')
    except Exception as e:
        print(f"Gemini feeder failed: {e}. Using fallback.")
        csv_path = "fallback.csv" # Create a fallback
    
    rows = list(csv.DictReader(open(csv_path)))
    
    fonts = {'bold': pick_font(DEFAULT_BOLD_FONT_CANDIDATES), 'thin': pick_font(DEFAULT_THIN_FONT_CANDIDATES + DEFAULT_FONT_CANDIDATES)}
    
    # Prepare backgrounds
    q_bg = os.path.join(DEFAULT_OUT_DIR, "tmp", "q_bg.mp4")
    run(["ffmpeg", "-y", "-i", os.path.join(ASSETS_DIR, "1.mp4"), "-i", os.path.join(ASSETS_DIR, "2.mp4"), "-filter_complex", "[0:v][1:v]concat=n=2:v=1[outv]", "-map", "[outv]", "-c:v", "libx264", "-pix_fmt", "yuv420p", q_bg])
    ans_template = os.path.join(ASSETS_DIR, "3.mp4")
    w, h = ffprobe_wh(ans_template)
    
    # Prepare intro/outro by re-encoding to match target resolution
    intro_path = prepare_ext_clip(os.path.join(ASSETS_DIR, "An_energetic_game_202508201332_sdz6d.mp4"), w, h, os.path.join(DEFAULT_OUT_DIR, "tmp"), "intro_prepared")
    outro_path = prepare_ext_clip(os.path.join(ASSETS_DIR, "A_single_explosive_202508201347_hctna.mp4"), w, h, os.path.join(DEFAULT_OUT_DIR, "tmp"), "outro_prepared")

    # Build clips
    clips = []
    for i, row in enumerate(rows[:1]): # Limit to 1 for test
        q = build_question_clip(i, row, q_bg, fonts, w, h, os.path.join(DEFAULT_OUT_DIR, "tmp"), os.path.join(DEFAULT_OUT_DIR, "clips"), SlideBoxes())
        a = build_answer_clip(i, row, ans_template, fonts, w, h, os.path.join(DEFAULT_OUT_DIR, "tmp"), os.path.join(DEFAULT_OUT_DIR, "clips"), SlideBoxes())
        clip_out = os.path.join(DEFAULT_OUT_DIR, "clips", f"clip_{i}.mp4")
        run(["ffmpeg", "-y", "-i", q, "-i", a, "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]", clip_out])
        clips.append(clip_out)
        
    # Final concat
    final_clips = [intro_path] + clips + [outro_path]
    final_out = os.path.join(DEFAULT_OUT_DIR, "final_video.mp4")
    inputs = "".join([f"[{i}:v][{i}:a]" for i in range(len(final_clips))])
    filter_complex = f"{inputs}concat=n={len(final_clips)}:v=1:a=1[v][a]"
    cmd = ["ffmpeg", "-y"]
    for p in final_clips: cmd.extend(["-i", p])
    cmd.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]", final_out])
    run(cmd)
    
    print(f"\n🎉 Video Creation Complete! -> {final_out}")

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
