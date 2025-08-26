#!/usr/bin/env python3
"""
Cloud-Native Trivia Video Generator
Uses the exact same video generation logic as the local version
but streams all assets from GCS and runs on cloud GPU machines.

This is designed to be deployed on the GPU worker fleet.
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

# ------------------------------ Config ------------------------------
GCS_ASSETS_BUCKET = "trivia-automations-2"
GCS_ASSET_BASE_PATH = "channel-test/video-assets"
GCS_JOBS_BUCKET = "trivia-automation"
TTS_VOICE = "en-US-Neural2-F"
TTS_SPEED = 1.0

# Asset paths - hybrid approach: cache large videos, stream small assets
# Allow overriding via environment variables to support per-project asset locations
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
        gcs_path,
    ])
    w, h = out.split("x")
    return int(w), int(h)

def escape_drawtext_text(text: str) -> str:
    """Escape special characters for ffmpeg drawtext"""
    s = text.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace(":", "\\:")
    s = s.replace("[", "\\[").replace("]", "\\]")
    s = s.replace("\r", "").replace("\n", "\\n")
    return s

def get_audio_duration_seconds(gcs_path: str) -> float:
    """Get audio duration from GCS path"""
    out = run_capture([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        gcs_path,
    ])
    try:
        return float(out)
    except Exception:
        return 0.0

def ensure_dir(p: str) -> None:
    """Ensure directory exists"""
    Path(p).mkdir(parents=True, exist_ok=True)

def get_asset_path(asset_name: str, cache_dir: str = None) -> str:
    """Get asset path for any asset. If cache_dir is provided, ensure a local cached copy exists and return its path.

    This avoids relying on ffmpeg support for gs:// URLs and works in constrained environments.
    """
    if cache_dir:
        local_path = os.path.join(cache_dir, asset_name)
        if not os.path.exists(local_path):
            download_gcs_asset(asset_name, cache_dir)
        return local_path
    # Fallback to GCS path if no cache directory was provided
    return f"gs://{ASSETS_BUCKET}/{ASSETS_BASE_PATH}/{asset_name}"

def download_gcs_asset(asset_name: str, cache_dir: str) -> str:
    """Download a GCS asset to local cache using Google Cloud Storage client."""
    client = storage.Client()
    bucket = client.bucket(ASSETS_BUCKET)
    blob = bucket.blob(f"{ASSETS_BASE_PATH}/{asset_name}")
    local_path = os.path.join(cache_dir, asset_name)
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    print(f"📥 Downloading {asset_name} from gs://{ASSETS_BUCKET}/{ASSETS_BASE_PATH}/{asset_name} to cache...")
    blob.download_to_filename(local_path)
    print(f"✅ Downloaded {asset_name} to {local_path}")
    return local_path

def scale_box_from_base(box_px: Tuple[int, int, int, int], base_w: int, base_h: int, w: int, h: int) -> Tuple[int, int, int, int]:
    """Scale a base 1920x1080 pixel box to actual w x h size."""
    l, t, bw, bh = box_px
    sx = w / float(base_w)
    sy = h / float(base_h)
    return int(round(l * sx)), int(round(t * sy)), int(round(bw * sx)), int(round(bh * sy))

def detect_timer_bar_crop(video_path: str) -> Tuple[int,int,int,int]:
    """Detects a bright rectangular bar region in the first frame of the timer video."""
    try:
        cap = cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise RuntimeError("Cannot read timer frame")
        
        ih, iw = frame.shape[:2]
        
        # Use a simple, reliable fallback approach for now
        # Crop a centered horizontal bar that's 80% width and 15% height
        w = int(iw * 0.80)
        h = int(ih * 0.15)
        x = (iw - w) // 2
        y = int(ih * 0.10)
        
        # Ensure all values are within bounds
        x = max(0, min(x, iw - 1))
        y = max(0, min(y, ih - 1))
        w = min(w, iw - x)
        h = min(h, ih - y)
        
        return (x, y, w, h)
    except Exception:
        # Robust fallback - ensure values fit within typical timer video dimensions (1200x272)
        return (120, 40, 960, 40)

def tts_generate_mp3(text: str, out_dir: str, base_name: str) -> str:
    """Generate TTS using Google Cloud Text-to-Speech API."""
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

def build_question_clip(idx: int, row: dict, template_path: str, fontfile: str, w: int, h: int, tmp_dir: str, out_dir: str, boxes: SlideBoxes, pause_after_seconds: float = 5.0) -> Tuple[str, float]:
    """Build question clip using GCS streaming - same logic as local version"""
    
    q_text = (row.get("question") or row.get("Question") or row.get("Question:") or row.get("Question ") or "")
    a_text = row.get("option_a") or row.get("A") or row.get("OptionA") or row.get("Option A") or "A"
    b_text = row.get("option_b") or row.get("B") or row.get("OptionB") or row.get("Option B") or "B"
    c_text = row.get("option_c") or row.get("C") or row.get("OptionC") or row.get("Option C") or "C"
    d_text = row.get("option_d") or row.get("D") or row.get("OptionD") or row.get("Option D") or "D"
    
    # Compose TTS text
    tts_script = f"{q_text} A, {a_text}. B, {b_text}. C, {c_text}. D, {d_text}."
    audio_path = tts_generate_mp3(tts_script, tmp_dir, f"q_{idx:03d}")
    audio_dur = get_audio_duration_seconds(audio_path)
    
    # Use a single, quantized start time for the timer/beep to keep perfect sync
    timer_start_s = round(audio_dur, 3)
    
    # Hold on the question after TTS finishes
    clip_duration = max(1.0, audio_dur + float(pause_after_seconds))
    
    # Compute boxes in pixels - scale provided base boxes to actual template size
    bx_q = scale_box_from_base(boxes.question_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_a = scale_box_from_base(boxes.answer_a_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_b = scale_box_from_base(boxes.answer_b_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_c = scale_box_from_base(boxes.answer_c_px, boxes.BASE_W, boxes.BASE_H, w, h)
    bx_d = scale_box_from_base(boxes.answer_d_px, boxes.BASE_W, boxes.BASE_H, w, h)
    
    # Move bottom row answers (C and D) up by total 3 pixels
    bx_c = (bx_c[0], bx_c[1]-3, bx_c[2], bx_c[3])
    bx_d = (bx_d[0], bx_d[1]-3, bx_d[2], bx_d[3])
    
    # Font sizes - simplified for cloud version
    q_font_size = 72
    a_font_size = 48
    
    # Escape text for drawtext filter
    def escape_drawtext(text: str) -> str:
        safe = text.replace("'", "'")
        safe = safe.replace("\n", "\\n")
        return safe.replace(":", "\\:").replace("%", "\\%")
    
    # Build drawtext filters for question and answers
    drawtext_filters = []
    
    # Question text (appears immediately)
    drawtext_filters.append(
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(q_text)}':fontsize={q_font_size}:"
        f"fontcolor=#111111:line_spacing=6:"
        f"x={bx_q[0]}+({bx_q[2]}-text_w)/2:y={bx_q[1]}+({bx_q[3]}-text_h)/2:"
        f"alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,1))'"
    )
    
    # Answer A
    drawtext_filters.append(
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(a_text)}':fontsize={a_font_size}:"
        f"fontcolor=#111111:line_spacing=6:"
        f"x={bx_a[0]}+({bx_a[2]}-text_w)/2:y={bx_a[1]}+({bx_a[3]}-text_h)/2:"
        f"alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,1))'"
    )
    
    # Answer B
    drawtext_filters.append(
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(b_text)}':fontsize={a_font_size}:"
        f"fontcolor=#111111:line_spacing=6:"
        f"x={bx_b[0]}+({bx_b[2]}-text_w)/2:y={bx_b[1]}+({bx_b[3]}-text_h)/2:"
        f"alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,1))'"
    )
    
    # Answer C
    drawtext_filters.append(
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(c_text)}':fontsize={a_font_size}:"
        f"fontcolor=#111111:line_spacing=6:"
        f"x={bx_c[0]}+({bx_c[2]}-text_w)/2:y={bx_c[1]}+({bx_c[3]}-text_h)/2:"
        f"alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,1))'"
    )
    
    # Answer D
    drawtext_filters.append(
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(d_text)}':fontsize={a_font_size}:"
        f"fontcolor=#111111:line_spacing=6:"
        f"x={bx_d[0]}+({bx_d[2]}-text_w)/2:y={bx_d[1]}+({bx_d[3]}-text_h)/2:"
        f"alpha='if(lt(t,1.0),0,if(lt(t,1.5),(t-1.0)/0.5,1))'"
    )
    
    # Combine all drawtext filters for answers on base video
    vf_base = "[0:v]setpts=PTS-STARTPTS" + ("," + ",".join(drawtext_filters) if drawtext_filters else "") + "[base]"
    
    # Timer overlay: starts at audio_dur, plays for pause_after_seconds
    timer_box = scale_box_from_base(boxes.timer_px, boxes.BASE_W, boxes.BASE_H, w, h)
    tbx, tby, tbw, tbh = timer_box
    
    # Move up 18px and enlarge 5%
    tby_adj = max(0, tby - 18)
    tbw_adj = int(tbw * 1.05)
    tbh_adj = int(tbh * 1.05)
    tbx_adj = tbx - (tbw_adj - tbw)//2
    
    # Timer logic: PNG timer visible from beginning, video timer appears when TTS stops
    vf_timer_png = (
        f"[2:v]format=rgba,scale={tbw_adj}:{tbh_adj},setpts=PTS-STARTPTS[timer_png]"
    )
    
    # Video timer: appears when TTS stops (timer_start_s onwards)
    vf_timer_vid = (
        f"[3:v]format=rgba,scale={tbw_adj}:{tbh_adj},setpts=PTS-STARTPTS,"
        f"trim=start=0:end={pause_after_seconds},"
        f"setpts=PTS+{timer_start_s}/TB[timer_vid]"
    )
    
    # Compose overlays on base
    vf_final = (
        f"{vf_base};{vf_timer_png};{vf_timer_vid};"
        f"[base][timer_png]overlay={tbx_adj}:{tby_adj}:enable='lt(t,{timer_start_s})'[pretimer];"
        f"[pretimer][timer_vid]overlay={tbx_adj}:{tby_adj}:enable='gte(t,{timer_start_s})'[v]"
    )
    
    out_path = os.path.join(out_dir, f"question_{idx:03d}.mp4")
    
    # Audio: TTS + ticking sound during timer video period only
    # TTS audio with padding
    a_tts = f"[1:a]apad=pad_dur={pause_after_seconds},atrim=duration={clip_duration:.3f}[a_tts]"
    
    # Ticking sound: delay by timer_start_s milliseconds, then play for pause_after_seconds
    delay_ms = int(timer_start_s * 1000)
    a_tick = f"[4:a]adelay=delays={delay_ms}:all=1,atrim=duration={clip_duration:.3f}[a_tick]"
    
    # Mix TTS and ticking sound
    a_mix = f"[a_tts][a_tick]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    
    filter_complex = (
        f"{vf_final};{a_tts};{a_tick};{a_mix}"
    )
    
    # Use cached local asset paths for reliability in cloud workers
    run([
        "ffmpeg",
        "-y",
        "-i", template_path,  # [0:v] template (GCS path)
        "-i", audio_path,     # [1:a] TTS audio (local temp)
        "-loop", "1", "-t", f"{timer_start_s:.3f}", "-i", get_asset_path(TIMER_PNG, tmp_dir),  # [2:v] PNG timer
        "-i", get_asset_path(TIMER_VIDEO, tmp_dir),     # [3:v] timer video
        "-i", get_asset_path(TICKING_AUDIO, tmp_dir),   # [4:a] ticking sound
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",  # Use software encoding for compatibility
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
        "-shortest",
        out_path,
    ])
    
    return out_path, clip_duration

def build_answer_clip(idx: int, row: dict, template_path: str, fontfile: str, w: int, h: int, tmp_dir: str, out_dir: str, boxes: SlideBoxes) -> str:
    """Build answer clip using GCS streaming - same logic as local version"""
    
    # Get the answer key (A, B, C, D) and the corresponding text
    answer_key = row.get("answer_key") or row.get("Correct Answer") or "A"
    
    # Get the actual text of the correct answer based on the answer key
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
    
    bx = scale_box_from_base(boxes.correct_px, boxes.BASE_W, boxes.BASE_H, w, h)
    
    # Build TTS for the answer: "Correct answer {correct_text}."
    answer_tts = tts_generate_mp3(f"Correct answer {correct_text}.", tmp_dir, f"ans_{idx:03d}")
    
    # Duration equals answer TTS duration plus tail silence for breathing room
    tts_dur = get_audio_duration_seconds(answer_tts)
    tail_silence = 1.0
    ans_dur = max(1.5, tts_dur + tail_silence)
    
    out_path = os.path.join(out_dir, f"answer_{idx:03d}.mp4")
    
    # Escape text for drawtext filter
    def escape_drawtext(text: str) -> str:
        safe = text.replace("'", "'")
        safe = safe.replace("\n", "\\n")
        return safe.replace(":", "\\:").replace("%", "\\%")
    
    # Use drawtext with dynamic font size to fit JSON boundary
    fade_start, fade_end = 0.5, 1.0
    line_spacing = 6
    drawtext_filter = (
        f"drawtext=fontfile='{fontfile}':text='{escape_drawtext(correct_text)}':fontsize=72:"
        f"fontcolor=#000000:line_spacing={line_spacing}:x={bx[0]}+({bx[2]}-text_w)/2:y={bx[1]}+({bx[3]}-text_h)/2:"
        f"alpha='if(lt(t,{fade_start}),0,if(lt(t,{fade_end}),(t-{fade_start})/{fade_end-fade_start},1))'"
    )
    
    # Add ding SFX at start of answer clip via separate input
    filter_complex = (
        f"[0:v]{drawtext_filter}[v];"
        f"[1:a]apad=pad_dur={tail_silence:.3f},atrim=duration={ans_dur:.3f},asetpts=PTS-STARTPTS[a_tts];"
        f"[2:a]atrim=duration=1.5,asetpts=PTS-STARTPTS[a_ding];"
        f"[a_ding][a_tts]amix=inputs=2:duration=longest:dropout_transition=0[a]"
    )
    
    run([
        "ffmpeg",
        "-y",
        "-i", template_path,  # [0:v] template (GCS path)
        "-i", answer_tts,     # [1:a] TTS (local temp)
        "-i", get_asset_path(DING_AUDIO, tmp_dir),      # [2:a] ding
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",  # Use software encoding for compatibility
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
        "-shortest",
        out_path,
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
    """Use the robust concat filter method instead of unreliable concat demuxer."""
    if not file_paths:
        raise ValueError("No files to concatenate")
    
    if len(file_paths) == 1:
        # Single file, just copy it
        run(["ffmpeg", "-y", "-i", file_paths[0], "-c", "copy", out_path])
        return
    
    # Build the complex filter for multiple files
    inputs = []
    for i in range(len(file_paths)):
        inputs.extend([f"[{i}:v]", f"[{i}:a]"])
    
    filter_complex = f"{''.join(inputs)}concat=n={len(file_paths)}:v=1:a=1[v][a]"
    
    # Build the ffmpeg command with all inputs
    cmd = ["ffmpeg", "-y"]
    for path in file_paths:
        cmd.extend(["-i", path])
    cmd.extend([
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
        out_path,
    ])
    
    run(cmd)

def read_csv_from_gcs(gcs_path: str) -> List[dict]:
    """Read CSV data directly from GCS without downloading"""
    # Parse GCS path
    if gcs_path.startswith("gs://"):
        bucket_name = gcs_path.split("/")[2]
        blob_path = "/".join(gcs_path.split("/")[3:])
    else:
        raise ValueError("Invalid GCS path format")
    
    # Read CSV content from GCS
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    content = blob.download_as_text()
    
    # Parse CSV content
    rows = []
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        rows.append(row)
    
    return rows

def make_intro_outro(fontfile: str, w: int, h: int, out_dir: str) -> Tuple[str, str]:
    """Create intro and outro videos"""
    intro = os.path.join(out_dir, "intro.mp4")
    outro = os.path.join(out_dir, "outro.mp4")
    
    # Intro
    run([
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={w}x{h}:d=10",
        "-f", "lavfi",
        "-t", "10",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", f"drawtext=fontfile='{fontfile}':text='Trivia Time!':fontsize=96:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
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
        "-shortest",
        intro,
    ])
    
    # Outro
    run([
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=black:s={w}x{h}:d=10",
        "-f", "lavfi",
        "-t", "10",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", f"drawtext=fontfile='{fontfile}':text='Thanks for Playing!':fontsize=80:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
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
        "-shortest",
        outro,
    ])
    
    return intro, outro

def process_job(job_info: JobInfo) -> str:
    """Process a complete job using GCS streaming"""
    
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
    
    # Get asset paths using hybrid approach
    entrance = get_asset_path(TEMPLATE_1, asset_cache_dir)
    bridge = get_asset_path(TEMPLATE_2, asset_cache_dir)
    answer = get_asset_path(TEMPLATE_3, asset_cache_dir)
    
    # Get video dimensions from template
    w, h = ffprobe_wh(entrance)
    
    # Font file (use system font)
    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(fontfile):
        fontfile = "/System/Library/Fonts/Helvetica.ttc"  # macOS fallback
    
    boxes = SlideBoxes()
    
    question_paths = []
    answer_paths = []
    indiv_paths = []
    
    # Process each trivia question
    for i, row in enumerate(rows, 1):
        print(f"🎬 Processing question {i}/{len(rows)}")
        
        # Build question clip (using entrance + bridge)
        q_path, q_duration = build_question_clip(
            i, row, entrance, fontfile, w, h, tmp_dir, tmp_dir, boxes, pause_after_seconds=5.0
        )
        
        # Build answer clip
        a_path = build_answer_clip(
            i, row, answer, fontfile, w, h, tmp_dir, tmp_dir, boxes
        )
        
        question_paths.append(q_path)
        answer_paths.append(a_path)
        
        # Concatenate question + answer
        indiv_out = os.path.join(indiv_dir, f"clip_{i:03d}.mp4")
        concat_two(q_path, a_path, indiv_out)
        indiv_paths.append(indiv_out)
    
    # Create intro/outro
    intro, outro = make_intro_outro(fontfile, w, h, tmp_dir)
    
    # Final concatenation
    final_order = [intro] + indiv_paths + [outro]
    final_out = os.path.join(out_dir, "final_video.mp4")
    
    print(f"🎬 Final concatenation: {len(final_order)} clips")
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
