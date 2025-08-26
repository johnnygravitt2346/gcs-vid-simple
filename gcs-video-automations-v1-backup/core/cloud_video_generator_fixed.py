#!/usr/bin/env python3
"""
Cloud-Native Trivia Video Generator - FIXED VERSION
Uses proper text scaling with Pillow and includes full video assembly.
"""

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
import asyncio

# Cloud dependencies
from google.cloud import storage
from google.cloud import texttospeech

# Pillow for intelligent text rendering
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required. Try: pip install Pillow", file=sys.stderr)
    raise

# ------------------------------ Config ------------------------------
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"
TTS_VOICE = "en-US-Neural2-F"
TTS_SPEED = 1.0

# Asset paths - hybrid approach: cache large videos, stream small assets
ASSETS_BUCKET = os.getenv("ASSETS_BUCKET", GCS_ASSETS_BUCKET)
ASSETS_BASE_PATH = os.getenv("ASSETS_BASE_PATH", GCS_ASSET_BASE_PATH)

# Large video templates (will be cached locally)
TEMPLATE_1 = "1.mp4"
TEMPLATE_2 = "2.mp4" 
TEMPLATE_3 = "3.mp4"

# Small assets (streamed from GCS)
TIMER_VIDEO = "slide_timer_bar_5s.mp4"
TIMER_PNG = "slide_timer_bar_full_striped.png"
TICKING_AUDIO = "ticking_clock_mechanical_5s.wav"
DING_AUDIO = "ding_correct_answer_long.wav"

# Intro/Outro videos (live-action)
INTRO_VIDEO = "An_energetic_game_202508201332_sdz6d.mp4"
OUTRO_VIDEO = "A_single_explosive_202508201347_hctna.mp4"

@dataclass
class SlideBoxes:
    """Bounding boxes for template layout. Values are pixel boxes (left, top, width, height) at base resolution."""
    BASE_W: int = 1920
    BASE_H: int = 1080
    
    # Question slide (1.mp4) - Updated question box coordinates (moved down 5%)
    question_px: Tuple[int, int, int, int] = (300, 265, 1332, 227)
    answer_a_px: Tuple[int, int, int, int] = (378, 569, 523, 110)
    answer_b_px: Tuple[int, int, int, int] = (1014, 568, 526, 113)
    answer_c_px: Tuple[int, int, int, int] = (379, 768, 517, 106)
    answer_d_px: Tuple[int, int, int, int] = (1018, 770, 519, 107)
    
    # Timer bar placement on question slide (white rectangle at top)
    timer_px: Tuple[int, int, int, int] = (597, 114, 713, 126)
    
    # Answer slide (3.mp4) - Updated coordinates
    correct_px: Tuple[int, int, int, int] = (576, 486, 759, 157)

@dataclass
class JobInfo:
    """Job information for cloud processing"""
    job_id: str
    channel: str
    gcs_csv_path: str
    output_bucket: str
    output_path: str

# --------------------------- Utility funcs --------------------------
def run(cmd: List[str]) -> None:
    """Execute FFmpeg command with cloud-native paths"""
    print("$", " ".join(shlex.quote(c) for c in cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(proc.stdout.decode("utf-8", errors="ignore"))
        raise RuntimeError(f"Command failed with exit code {proc.returncode}")

def run_capture(cmd: List[str]) -> str:
    """Execute command and capture output"""
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout.decode("utf-8", errors="ignore"))
    return proc.stdout.decode("utf-8", errors="ignore").strip()

def ffprobe_wh(gcs_path: str) -> Tuple[int, int]:
    """Get video dimensions from GCS path"""
    out = run_capture([
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=s=x:p=0",
        gcs_path
    ])
    return tuple(map(int, out.split("x")))

def get_audio_duration_seconds(audio_path: str) -> float:
    """Get audio duration in seconds"""
    out = run_capture([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ])
    return float(out)

def normalize_clip_for_concat(input_path: str, output_path: str, target_w: int = 1920, target_h: int = 1080) -> None:
    """Normalize a video clip to exact target resolution for consistent concatenation"""
    run([
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v", "libx264",
        "-preset", "medium",
        "-profile:v", "high",
        "-crf", "23",
        "-b:v", "3M",
        "-maxrate", "5M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "60",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        output_path
    ])

def ensure_dir(path: str) -> None:
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def scale_box_from_base(box_px: Tuple[int, int, int, int], base_w: int, base_h: int, w: int, h: int) -> Tuple[int, int, int, int]:
    """Scale a base 1920x1080 pixel box to actual w x h size."""
    l, t, bw, bh = box_px
    sx = w / float(base_w)
    sy = h / float(base_h)
    return int(round(l * sx)), int(round(t * sy)), int(round(bw * sx)), int(round(bh * sy))

def get_asset_path(asset_name: str, cache_dir: str) -> str:
    """Get asset path - download from GCS if not cached"""
    local_path = os.path.join(cache_dir, asset_name)
    
    if not os.path.exists(local_path):
        # Download from GCS
        client = storage.Client()
        bucket = client.bucket(ASSETS_BUCKET)
        blob = bucket.blob(f"{ASSETS_BASE_PATH}/{asset_name}")
        local_path = os.path.join(cache_dir, asset_name)
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        print(f"📥 Downloading {asset_name} from gs://{ASSETS_BUCKET}/{ASSETS_BASE_PATH}/{asset_name} to cache...")
        blob.download_to_filename(local_path)
        print(f"✅ Downloaded {asset_name} to {local_path}")
    
    return local_path

def read_csv_from_gcs(gcs_path: str) -> List[dict]:
    """Read CSV data from GCS"""
    client = storage.Client()
    
    # Parse GCS path
    if gcs_path.startswith("gs://"):
        parts = gcs_path.split("/")
        bucket_name = parts[2]
        blob_path = "/".join(parts[3:])
    else:
        raise ValueError(f"Invalid GCS path: {gcs_path}")
    
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    # Download CSV content
    csv_content = blob.download_as_text()
    
    # Parse CSV
    reader = csv.DictReader(csv_content.splitlines())
    return list(reader)

# --------------------------- Smart Text Rendering --------------------------
def render_text_to_png(text: str, box_w: int, box_h: int, font_path: str, out_path: str, is_bold: bool = False) -> None:
    """Render text to PNG with intelligent sizing and wrapping - produces perfect text images"""
    
    # Calculate padding (10% of box dimensions)
    padding_w = int(box_w * 0.1)
    padding_h = int(box_h * 0.1)
    
    # Calculate text area dimensions
    text_area_w = box_w - 2 * padding_w
    text_area_h = box_h - 2 * padding_h
    
    # Create transparent RGBA image
    img = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    def wrap_text(txt: str, font, max_width: int) -> str:
        """Wrap text to fit within max width using word boundaries"""
        words = txt.split()
        lines = []
        current_line = []
        
        for word in words:
            # Test if adding this word fits
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width or not current_line:
                current_line.append(word)
            else:
                # Word doesn't fit, start new line
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
        
        # Add remaining line
        if current_line:
            lines.append(" ".join(current_line))
        
        return "\n".join(lines)
    
    def find_optimal_font_size(txt: str, min_size: int, max_size: int) -> tuple[int, str]:
        """Binary search for optimal font size that fits perfectly"""
        low, high = min_size, max_size
        best_size, best_wrapped_text = min_size, txt
        
        while low <= high:
            mid = (low + high) // 2
            
            try:
                # Create font at this size
                font = ImageFont.truetype(font_path, mid)
                
                # Wrap text and measure dimensions
                wrapped = wrap_text(txt, font, text_area_w)
                bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=6)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # Check if text fits with padding
                if text_width <= text_area_w and text_height <= text_area_h:
                    # This size fits, try larger
                    best_size, best_wrapped_text = mid, wrapped
                    low = mid + 1
                else:
                    # Too large, try smaller
                    high = mid - 1
                    
            except Exception:
                # Font creation failed, try smaller
                high = mid - 1
        
        return best_size, best_wrapped_text
    
    # Find optimal font size using binary search
    min_font_size = 12
    max_font_size = 120 if is_bold else 90
    
    font_size, wrapped_text = find_optimal_font_size(text, min_font_size, max_font_size)
    
    # Create final font and measure text
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=6)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate center position
    x = padding_w + (text_area_w - text_width) // 2
    y = padding_h + (text_area_h - text_height) // 2
    
    # Draw text with enhanced shadow for maximum pop
    shadow_offset = 3 if is_bold else 2
    shadow_alpha = 180 if is_bold else 140
    
    # Draw shadow first (black shadow for maximum contrast)
    draw.multiline_text((x+shadow_offset, y+shadow_offset), wrapped_text, font=font, fill=(0, 0, 0, shadow_alpha), spacing=6)
    
    # Draw main text in black for maximum readability
    draw.multiline_text((x, y), wrapped_text, font=font, fill="#000000", spacing=6)
    
    # Save as transparent PNG
    img.save(out_path, "PNG")

def find_font() -> str:
    """Find a reliable font that works in cloud environments"""
    
    # Common Linux font paths (cloud-friendly)
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
    ]
    
    # Check each candidate
    for font_path in font_candidates:
        if os.path.exists(font_path):
            print(f"✅ Found font: {font_path}")
            return font_path
    
    # Fallback: try to find any TTF font
    import glob
    fallback_fonts = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    if fallback_fonts:
        print(f"✅ Found fallback font: {fallback_fonts[0]}")
        return fallback_fonts[0]
    
    raise FileNotFoundError("No suitable fonts found in cloud environment. Install fonts-dejavu-core package.")

# --------------------------- TTS Generation --------------------------
def tts_generate_mp3(text: str, out_dir: str, base_name: str) -> str:
    """Generate TTS using Google Cloud Text-to-Speech API"""
    out_path = os.path.join(out_dir, f"{base_name}.mp3")
    
    try:
        # Set up the client with service account credentials
        client = texttospeech.TextToSpeechClient()
        
        # Configure the TTS request
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        # Voice configuration
        voice_config = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=TTS_VOICE,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        
        # Audio configuration
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=TTS_SPEED,
            sample_rate_hertz=44100
        )
        
        # Perform the TTS request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_config,
            audio_config=audio_config
        )
        
        # Save the audio content
        with open(out_path, "wb") as out:
            out.write(response.audio_content)
        
        print(f"Generated Google Cloud TTS: '{text[:30]}...' with voice {TTS_VOICE}")
        return out_path
        
    except Exception as e:
        print(f"Google Cloud TTS failed: {e}")
        raise

# --------------------------- Video Generation --------------------------
def build_question_clip(idx: int, row: dict, template_path: str, fonts: dict, w: int, h: int, tmp_dir: str, out_dir: str, boxes: SlideBoxes, pause_after_seconds: float = 5.0) -> Tuple[str, float]:
    """Build question clip using smart text rendering"""
    
    # Extract text from CSV
    q_text = (row.get("question") or row.get("Question") or "")
    a_text = row.get("option_a") or row.get("A") or "A"
    b_text = row.get("option_b") or row.get("B") or "B"
    c_text = row.get("option_c") or row.get("C") or "C"
    d_text = row.get("option_d") or row.get("D") or "D"
    
    # Generate TTS
    tts_script = f"{q_text} A, {a_text}. B, {b_text}. C, {c_text}. D, {d_text}."
    audio_path = tts_generate_mp3(tts_script, tmp_dir, f"q_{idx:03d}")
    audio_dur = get_audio_duration_seconds(audio_path)
    
    # Calculate timing
    timer_start_s = round(audio_dur, 3)
    clip_duration = max(1.0, audio_dur + float(pause_after_seconds))
    
    # Scale boxes to actual video dimensions
    bx_q = scale_box_from_base(boxes.question_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_a = scale_box_from_base(boxes.answer_a_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_b = scale_box_from_base(boxes.answer_b_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_c = scale_box_from_base(boxes.answer_c_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_d = scale_box_from_base(boxes.answer_d_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_timer = scale_box_from_base(boxes.timer_px, boxes.BASE_W, boxes.BASE_H, w, h)
    
    # Adjust bottom row answers
    bx_c = (bx_c[0], bx_c[1]-3, bx_c[2], bx_c[3])
    bx_d = (bx_d[0], bx_d[1]-3, bx_d[2], bx_d[3])
    
    # Render text to PNG files with smart scaling
    q_png = os.path.join(tmp_dir, f"q_{idx:03d}.png")
    a_png = os.path.join(tmp_dir, f"a_{idx:03d}.png")
    b_png = os.path.join(tmp_dir, f"b_{idx:03d}.png")
    c_png = os.path.join(tmp_dir, f"c_{idx:03d}.png")
    d_png = os.path.join(tmp_dir, f"d_{idx:03d}.png")
    
    render_text_to_png(q_text, bx_q[2], bx_q[3], fonts['bold'], q_png, is_bold=True)
    render_text_to_png(a_text, bx_a[2], bx_a[3], fonts['thin'], a_png)
    render_text_to_png(b_text, bx_b[2], bx_b[3], fonts['thin'], b_png)
    render_text_to_png(c_text, bx_c[2], bx_c[3], fonts['thin'], c_png)
    render_text_to_png(d_text, bx_d[2], bx_d[3], fonts['thin'], d_png)
    
    # Get timer assets
    timer_vid = get_asset_path(TIMER_VIDEO, tmp_dir)
    timer_png = get_asset_path(TIMER_PNG, tmp_dir)
    tick_sfx = get_asset_path(TICKING_AUDIO, tmp_dir)
    
    # Build video filter complex
    vf_parts = [
        f"[2:v]format=rgba,scale={bx_q[2]}:{bx_q[3]},fade=in:st=1:d=0.5:alpha=1[q]",
        f"[3:v]format=rgba,scale={bx_a[2]}:{bx_a[3]},fade=in:st=1:d=0.5:alpha=1[a]",
        f"[4:v]format=rgba,scale={bx_b[2]}:{bx_b[3]},fade=in:st=1:d=0.5:alpha=1[b]",
        f"[5:v]format=rgba,scale={bx_c[2]}:{bx_c[3]},fade=in:st=1:d=0.5:alpha=1[c]",
        f"[6:v]format=rgba,scale={bx_d[2]}:{bx_d[3]},fade=in:st=1:d=0.5:alpha=1[d]",
        f"[7:v]format=rgba,scale={bx_timer[2]}:{bx_timer[3]}[t_static]",
        f"[8:v]format=rgba,scale={bx_timer[2]}:{bx_timer[3]},trim=0:{pause_after_seconds},setpts=PTS+{timer_start_s}/TB[t_run]",
        f"[0:v][q]overlay={bx_q[0]}:{bx_q[1]}[v1]",
        f"[v1][a]overlay={bx_a[0]}:{bx_a[1]}[v2]",
        f"[v2][b]overlay={bx_b[0]}:{bx_b[1]}[v3]",
        f"[v3][c]overlay={bx_c[0]}:{bx_c[1]}[v4]",
        f"[v4][d]overlay={bx_d[0]}:{bx_d[1]}[v5]",
        f"[v5][t_static]overlay={bx_timer[0]}:{bx_timer[1]}:enable='lt(t,{timer_start_s})'[v6]",
        f"[v6][t_run]overlay={bx_timer[0]}:{bx_timer[1]}:enable='gte(t,{timer_start_s})'[v]"
    ]
    
    # Build audio filter complex
    af_parts = [
        f"[1:a]apad=pad_dur={pause_after_seconds}[tts]",
        f"[9:a]adelay={int(timer_start_s*1000)}|{int(timer_start_s*1000)}[tick]",
        f"[tts][tick]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    ]
    
    vf = ";".join(vf_parts)
    af = ";".join(af_parts)
    
    out_path = os.path.join(out_dir, f"question_{idx:03d}.mp4")
    
    # Run FFmpeg command
    run([
        "ffmpeg", "-y",
        "-i", template_path,  # [0:v] background template
        "-i", audio_path,     # [1:a] TTS audio
        "-loop", "1", "-t", str(clip_duration), "-i", q_png,      # [2:v] question text
        "-loop", "1", "-t", str(clip_duration), "-i", a_png,      # [3:v] answer A
        "-loop", "1", "-t", str(clip_duration), "-i", b_png,      # [4:v] answer B
        "-loop", "1", "-t", str(clip_duration), "-i", c_png,      # [5:v] answer C
        "-loop", "1", "-t", str(clip_duration), "-i", d_png,      # [6:v] answer D
        "-loop", "1", "-t", str(clip_duration), "-i", timer_png,  # [7:v] timer static
        "-i", timer_vid,      # [8:v] timer video
        "-i", tick_sfx,       # [9:a] ticking sound
        "-filter_complex", f"{vf};{af}",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-profile:v", "high",
        "-crf", "23",
        "-b:v", "3M",
        "-maxrate", "5M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "60",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        "-t", str(clip_duration),
        out_path
    ])
    
    return out_path, clip_duration

def build_answer_clip(idx: int, row: dict, template_path: str, fonts: dict, w: int, h: int, tmp_dir: str, out_dir: str, boxes: SlideBoxes) -> str:
    """Build answer clip using smart text rendering"""
    
    # Get the answer key and corresponding text
    answer_key = row.get("answer_key") or row.get("Correct Answer") or "A"
    
    if answer_key == "A":
        correct_text = row.get("option_a") or "Option A"
    elif answer_key == "B":
        correct_text = row.get("option_b") or "Option B"
    elif answer_key == "C":
        correct_text = row.get("option_c") or "Option C"
    elif answer_key == "D":
        correct_text = row.get("option_d") or "Option D"
    else:
        correct_text = "Correct Answer"
    
    # Generate TTS
    tts_script = f"Correct answer {correct_text}."
    answer_tts = tts_generate_mp3(tts_script, tmp_dir, f"ans_{idx:03d}")
    
    # Calculate duration
    tts_dur = get_audio_duration_seconds(answer_tts)
    tail_silence = 1.0
    ans_dur = max(1.5, tts_dur + tail_silence)
    
    # Scale answer box
    bx = scale_box_from_base(boxes.correct_px, boxes.BASE_W, boxes.BASE_H, w, h)
    
    # Render answer text to PNG
    correct_png = os.path.join(tmp_dir, f"correct_{idx:03d}.png")
    render_text_to_png(correct_text, bx[2], bx[3], fonts['bold'], correct_png, is_bold=True)
    
    # Get ding sound
    ding_sfx = get_asset_path(DING_AUDIO, tmp_dir)
    
    # Build video filter complex
    vf = f"[1:v]format=rgba,scale={bx[2]}:{bx[3]},fade=in:st=0.5:d=0.5:alpha=1[c];[0:v][c]overlay={bx[0]}:{bx[1]}[v]"
    
    # Build audio filter complex
    af = f"[2:a]apad=pad_dur={tail_silence}[tts];[3:a]atrim=duration=1.5[ding];[ding][tts]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    
    out_path = os.path.join(out_dir, f"answer_{idx:03d}.mp4")
    
    # Run FFmpeg command
    run([
        "ffmpeg", "-y",
        "-i", template_path,  # [0:v] background template
        "-loop", "1", "-t", str(ans_dur), "-i", correct_png,  # [1:v] answer text
        "-i", answer_tts,     # [2:a] TTS audio
        "-i", ding_sfx,       # [3:a] ding sound
        "-filter_complex", f"{vf};{af}",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-profile:v", "high",
        "-crf", "23",
        "-b:v", "3M",
        "-maxrate", "5M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "60",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        "-t", str(ans_dur),
        out_path
    ])
    
    return out_path

def concat_two(q_path: str, a_path: str, out_path: str) -> None:
    """Concatenate question and answer clips"""
    run([
        "ffmpeg",
        "-y",
        "-i", q_path,
        "-i", a_path,
        "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-profile:v", "high",
        "-crf", "23",
        "-b:v", "3M",
        "-maxrate", "5M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "60",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        out_path,
    ])

def concat_many_ordered(file_paths: List[str], out_path: str) -> None:
    """Concatenate multiple video files in order"""
    if not file_paths:
        raise ValueError("No files to concatenate")
    
    if len(file_paths) == 1:
        # Single file, just copy it
        run(["ffmpeg", "-y", "-i", file_paths[0], "-c", "copy", out_path])
        return
    
    # Build filter complex for multiple files
    filter_parts = []
    for i in range(len(file_paths)):
        filter_parts.append(f"[{i}:v][{i}:a]")
    
    filter_complex = "".join(filter_parts) + f"concat=n={len(file_paths)}:v=1:a=1[v][a]"
    
    # Build input arguments
    input_args = []
    for path in file_paths:
        input_args.extend(["-i", path])
    
    # Run FFmpeg
    cmd = ["ffmpeg", "-y"] + input_args + [
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-profile:v", "high",
        "-crf", "23",
        "-b:v", "3M",
        "-maxrate", "5M",
        "-bufsize", "6M",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-g", "60",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-ar", "48000",
        out_path
    ]
    
    run(cmd)

def get_live_action_intro_outro(tmp_dir: str) -> Tuple[str, str]:
    """Get live-action intro and outro videos from GCS assets"""
    
    # These are the actual live-action host videos
    intro_video = get_asset_path(INTRO_VIDEO, tmp_dir)
    outro_video = get_asset_path(OUTRO_VIDEO, tmp_dir)
    
    print("🎬 Using live-action intro/outro videos")
    return intro_video, outro_video

def process_job(job_info: JobInfo) -> str:
    """Process a complete job using smart text rendering and full assembly"""
    
    print(f"🚀 Processing job {job_info.job_id} for channel {job_info.channel}")
    
    # Create temporary directories
    tmp_dir = tempfile.mkdtemp(prefix=f"job_{job_info.job_id}_")
    out_dir = os.path.join(tmp_dir, "output")
    indiv_dir = os.path.join(out_dir, "individual_clips")
    
    ensure_dir(out_dir)
    ensure_dir(indiv_dir)
    
    # Read CSV data from GCS
    print(f"📊 Reading trivia data from {job_info.gcs_csv_path}")
    rows = read_csv_from_gcs(job_info.gcs_csv_path)
    
    # Create asset cache directory
    asset_cache_dir = os.path.join(tmp_dir, "asset_cache")
    ensure_dir(asset_cache_dir)
    
    # Get asset paths
    entrance = get_asset_path(TEMPLATE_1, asset_cache_dir)
    bridge = get_asset_path(TEMPLATE_2, asset_cache_dir)
    answer = get_asset_path(TEMPLATE_3, asset_cache_dir)
    
    # Get video dimensions
    w, h = ffprobe_wh(entrance)
    
    # Setup fonts using cloud-aware font detection
    print("🔤 Setting up fonts for cloud environment...")
    try:
        regular_font = find_font()
        bold_font = find_font()  # We'll use the same font but make it bold via size
        
        fonts = {
            'regular': regular_font,
            'bold': regular_font,     # Same font, will be made bold via size
            'thin': regular_font      # Same font, will be made thinner via size
        }
        print("✅ Fonts configured successfully")
    except Exception as e:
        print(f"⚠️ Font setup failed: {e}")
        print("🔄 Falling back to system default fonts...")
        # Fallback to system fonts
        fonts = {
            'regular': '/System/Library/Fonts/Helvetica.ttc',
            'bold': '/System/Library/Fonts/Helvetica.ttc',
            'thin': '/System/Library/Fonts/Helvetica.ttc'
        }
    
    boxes = SlideBoxes()
    
    question_paths = []
    answer_paths = []
    indiv_paths = []
    
    # Process each trivia question
    for i, row in enumerate(rows, 1):
        print(f"🎬 Processing question {i}/{len(rows)}")
        
        # Build question clip with smart text rendering
        q_path, q_duration = build_question_clip(
            i, row, entrance, fonts, w, h, tmp_dir, tmp_dir, boxes, pause_after_seconds=5.0
        )
        
        # Build answer clip with smart text rendering
        a_path = build_answer_clip(
            i, row, answer, fonts, w, h, tmp_dir, tmp_dir, boxes
        )
        
        question_paths.append(q_path)
        answer_paths.append(a_path)
        
        # Concatenate question + answer
        indiv_out = os.path.join(indiv_dir, f"clip_{i:03d}.mp4")
        concat_two(q_path, a_path, indiv_out)
        indiv_paths.append(indiv_out)
    
    # Get live-action intro/outro videos and normalize them to 1920x1080
    print("🎬 Getting live-action intro/outro videos...")
    intro_raw, outro_raw = get_live_action_intro_outro(tmp_dir)
    
    # Normalize intro and outro to exact 1920x1080 resolution
    intro_normalized = os.path.join(tmp_dir, "intro_normalized.mp4")
    outro_normalized = os.path.join(tmp_dir, "outro_normalized.mp4")
    
    print("🎬 Normalizing intro/outro to 1920x1080...")
    normalize_clip_for_concat(intro_raw, intro_normalized, 1920, 1080)
    normalize_clip_for_concat(outro_raw, outro_normalized, 1920, 1080)
    
    # TEST MODE: Process only the first trivia clip for faster debugging
    print("🧪 TEST MODE: Processing only first trivia clip for faster debugging")
    test_clips = [indiv_paths[0]] if indiv_paths else []
    
    # Final concatenation: Intro + Single Test Clip + Outro
    final_order = [intro_normalized] + test_clips + [outro_normalized]
    final_out = os.path.join(out_dir, "final_video.mp4")
    
    print(f"🎬 Final concatenation: {len(final_order)} clips (TEST MODE)")
    concat_many_ordered(final_order, final_out)
    
    # Upload final video to GCS
    print(f"☁️ Uploading final video to {job_info.output_path}")
    client = storage.Client()
    bucket = client.bucket(job_info.output_bucket)
    blob = bucket.blob(job_info.output_path)
    blob.upload_from_filename(final_out)
    
    print(f"✅ Job {job_info.job_id} completed successfully!")
    print(f"📁 Final video: {job_info.output_path}")
    
    # Cleanup temporary files
    import shutil
    shutil.rmtree(tmp_dir)
    
    return job_info.output_path

def main():
    """Main entry point for cloud video generation"""
    
    # Example usage
    job_info = JobInfo(
        job_id="test-job-001",
        channel="channel-test",
        gcs_csv_path="gs://trivia-automation/jobs/channel-test/job-001/questions.csv",
        output_bucket="trivia-automation",
        output_path="final_videos/channel-test/job-001/final_video.mp4"
    )
    
    try:
        output_path = process_job(job_info)
        print(f"🎉 Video generation completed: {output_path}")
    except Exception as e:
        print(f"❌ Video generation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
