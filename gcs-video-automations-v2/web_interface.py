#!/usr/bin/env python3
"""
🌐 Web Interface for GCS Video Automations
Access your trivia video generator from any computer!
"""

import os
import json
import asyncio
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
import tempfile

# Add core modules to path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/core")

from gemini_feeder_fixed import GeminiFeederFixed, FeederRequest
from cloud_video_generator_fixed import JobInfo, process_job
from core.channel_config import load_channel_config, save_channel_config, ChannelConfig
from core.path_resolver import get_path_resolver_for_channel
from core.asset_resolver import AssetResolver
from google.cloud import storage

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-this')
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
GCS_JOBS_BUCKET = "trivia-automations-2"  # Match the bucket used in path resolver
GEMINI_API_KEY = "AIzaSyC86DvHclKT7_zYmTWcSBnPX6uA3zP7_WE"  # Baked in API key
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

# Store active jobs
active_jobs = {}

@app.route('/')
def index():
    """Main page with trivia generator interface"""
    return render_template('index.html')


@app.route('/channels', methods=['GET'])
def list_channels():
    """List available channels by scanning the channels folder in the parent bucket."""
    try:
        client = storage.Client()
        # Use hardcoded bucket for web interface
        bucket = client.bucket("trivia-automations-2")
        prefix = "channels/"
        # List first-level channel directories
        blobs = bucket.list_blobs(prefix=prefix, delimiter="/")
        channels = []
        # The google-cloud-storage iterator populates _prefixes after iteration
        for _ in blobs:
            pass
        for p in blobs.prefixes:
            # p like 'channels/channel-id/'
            parts = p.strip('/').split('/')
            if len(parts) >= 2:
                channels.append(parts[1])
        # Ensure test-channel exists
        if "channel-test" not in channels:
            channels.insert(0, "channel-test")
        return jsonify({"channels": channels})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/channels/<channel_id>/preflight', methods=['GET'])
def channel_preflight(channel_id):
    """Run preflight validation for a channel's required assets."""
    try:
        # Ensure config exists
        _ = load_channel_config(channel_id)
        ar = AssetResolver(channel_id)
        ok, errors = ar.preflight_validate()
        return jsonify({"ok": ok, "errors": errors})
    except Exception as e:
        return jsonify({"ok": False, "errors": {"__root__": str(e)}}), 500


@app.route('/channels/<channel_id>/upload_csv', methods=['POST'])
def upload_csv(channel_id):
    """Upload a CSV, store under feeds/csv_input, and update canonical latest.csv."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        resolver = get_path_resolver_for_channel(channel_id)
        client = storage.Client()
        bucket = client.bucket("trivia-automations-2")  # Use hardcoded bucket

        # Ensure feeds directories exist by writing placeholders
        csv_folder = resolver.feeds_csv_input_uri()
        latest_uri = resolver.canonical_latest_csv_uri()

        # Write upload to timestamped csv in csv_input
        from datetime import datetime
        ts = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
        target_blob_path = f"{csv_folder.replace(f'gs://{resolver.parent_bucket}/','')}/{ts}.csv"
        blob = bucket.blob(target_blob_path)
        blob.upload_from_string(file.read(), content_type='text/csv')

        # Update canonical latest.csv
        latest_blob_path = latest_uri.replace("gs://trivia-automations-2/", "")
        latest_blob = bucket.blob(latest_blob_path)
        latest_blob.rewrite(blob)

        return jsonify({
            'message': 'CSV uploaded and canonical latest.csv updated',
            'csv_path': f"gs://trivia-automations-2/{target_blob_path}",
            'latest_csv': latest_uri
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate', methods=['POST'])
def start_generation():
    """Start trivia video generation"""
    try:
        data = request.get_json()
        num_questions = int(data.get('num_questions', 5))
        channel_id = data.get('channel_id', 'channel-test')
        input_mode = data.get('input_mode', 'gemini')  # 'gemini' or 'csv'
        category = data.get('category', 'general_knowledge')  # Get category from frontend
        gemini_api_key = data.get('gemini_api_key', '')  # Get API key from frontend
        
        if not (1 <= num_questions <= 10):
            return jsonify({'error': 'Number of questions must be between 1 and 10'}), 500
        
        # Check environment
        if not GOOGLE_APPLICATION_CREDENTIALS:
            return jsonify({'error': 'GOOGLE_APPLICATION_CREDENTIALS not configured'}), 500
        
        # Validate Gemini API key if using Gemini mode
        if input_mode == 'gemini':
            if not gemini_api_key or not gemini_api_key.strip():
                return jsonify({'error': 'Gemini API key required for Gemini mode'}), 400
            # Store the API key for this job
            GEMINI_API_KEY = gemini_api_key.strip()
        
        # Create job ID
        job_id = f"web-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Store job info FIRST
        active_jobs[job_id] = {
            'status': 'starting',
            'num_questions': num_questions,
            'channel_id': channel_id,
            'input_mode': input_mode,
            'category': category,
            'progress': 0,
            'current_step': 'Initializing...',
            'created_at': datetime.now().isoformat()
        }
        
        # Start generation in background AFTER storing job info
        thread = threading.Thread(
            target=run_generation_pipeline,
            args=(job_id, num_questions, channel_id, input_mode, category)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Generation started',
            'status': 'starting'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_generation_pipeline(job_id, num_questions, channel_id, input_mode, category):
    """Run the complete generation pipeline"""
    try:
        # Update job status
        active_jobs[job_id]['status'] = 'running'
        active_jobs[job_id]['progress'] = 10
        active_jobs[job_id]['current_step'] = 'Preparing input...'
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': 'running',
            'progress': 10,
            'current_step': 'Preparing input...'
        })
        
        client = storage.Client()
        resolver = get_path_resolver_for_channel(channel_id)
        
        if input_mode == 'gemini':
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 20,
                'current_step': f'Generating {num_questions} {category} trivia questions with Gemini...'
            })
            feeder = GeminiFeederFixed(api_key=GEMINI_API_KEY)
            
            # Log the received category for debugging
            print(f"🎯 Received category parameter: {category}")
            print(f"🎯 Category type: {type(category)}")
            
            # Use the user's selected category instead of auto-detecting from channel name
            # This gives users control over what type of trivia to generate
            if not category or category.strip() == "":
                category = "general_knowledge"
                print(f"⚠️ Category was empty, using default: {category}")
            
            user_category = category.lower().replace(" ", "_").replace("-", "_")
            
            # Map user-friendly category names to Gemini feeder presets
            category_mapping = {
                "sports": "sports",
                "general_knowledge": "general_knowledge", 
                "general": "general_knowledge",
                "science": "science",
                "history": "history",
                "geography": "geography",
                "music": "music",
                "entertainment": "entertainment",
                "movies": "entertainment",
                "tv": "entertainment",
                "art": "art",
                "literature": "literature",
                "technology": "technology",
                "space": "space",
                "animals": "animals",
                "food": "food",
                "travel": "travel",
                "politics": "politics",
                "business": "business",
                "fashion": "fashion"
            }
            
            # Get the mapped category or use the original if it's already a valid preset
            channel_category = category_mapping.get(user_category, user_category)
            
            # Fallback to general_knowledge if category is not recognized
            if channel_category not in feeder.prompt_presets:
                channel_category = "general_knowledge"
                socketio.emit('job_update', {
                    'job_id': job_id,
                    'progress': 24,
                    'current_step': f"⚠️ Category '{category}' not recognized, using 'general_knowledge' instead"
                })
            
            # Log the selected category for debugging
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 24,
                'current_step': f'Using selected category: {category} (mapped to: {channel_category})'
            })
            
            # Also log to console for debugging
            print(f"🎯 User selected category: {category}")
            print(f"🎯 Mapped to Gemini preset: {channel_category}")
            
            feeder_request = FeederRequest(
                channel_id=channel_id,
                prompt_preset=channel_category,
                quantity=num_questions,
                difficulty="medium",
                language_filter="en"
            )
            
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 25,
                'current_step': f'Generating {num_questions} {channel_category} trivia questions with Gemini...'
            })
            
            # Debug: Add more detailed logging
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 26,
                'current_step': f'Calling Gemini feeder with preset: {channel_category}'
            })
            
            try:
                dataset_uri = asyncio.run(feeder.generate_dataset(feeder_request))
                socketio.emit('job_update', {
                    'job_id': job_id,
                    'progress': 27,
                    'current_step': f'Gemini feeder completed successfully. Dataset URI: {dataset_uri}'
                })
            except Exception as e:
                socketio.emit('job_update', {
                    'job_id': job_id,
                    'progress': 27,
                    'current_step': f'Gemini feeder failed with error: {str(e)}'
                })
                raise
            
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 28,
                'current_step': f'Questions generated. Reading dataset from: {dataset_uri}'
            })
            
            # Read the generated questions for review
            # The dataset_uri should be a GCS path like gs://bucket/path/to/dataset
            if dataset_uri.startswith('gs://'):
                # Parse GCS URI
                parts = dataset_uri.replace('gs://', '').split('/')
                bucket_name = parts[0]
                file_path = '/'.join(parts[1:])
                
                # Look for questions.csv in the dataset directory
                src_bucket = client.bucket(bucket_name)
                src_blob = src_bucket.blob(f"{file_path}/questions.csv")
            else:
                # Fallback: assume it's already a full path
                dataset_csv = f"{dataset_uri}/questions.csv"
                src_bucket = client.bucket(dataset_csv.split('/')[2])
                src_blob = src_bucket.blob('/'.join(dataset_csv.split('/')[3:]))
            
            # Download and parse CSV to get questions for review
            csv_content = src_blob.download_as_text()
            import csv
            import io
            questions = []
            
            # Debug: Log the CSV content and field names
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 29,
                'current_step': f'Parsing CSV data... CSV length: {len(csv_content)} characters'
            })
            
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            # Debug: Log the field names
            field_names = csv_reader.fieldnames
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 29,
                'current_step': f'CSV fields: {", ".join(field_names) if field_names else "No fields found"}'
            })
            
            for row in csv_reader:
                # Get the answer key (A, B, C, or D)
                answer_key = row.get('answer_key', '')
                
                # Map answer key to actual answer text
                options = [
                    row.get('option_a', ''),
                    row.get('option_b', ''),
                    row.get('option_c', ''),
                    row.get('option_d', '')
                ]
                
                # Convert answer key to actual answer text
                if answer_key == 'A':
                    correct_answer = options[0]
                elif answer_key == 'B':
                    correct_answer = options[1]
                elif answer_key == 'C':
                    correct_answer = options[2]
                elif answer_key == 'D':
                    correct_answer = options[3]
                else:
                    correct_answer = f"Unknown ({answer_key})"
                
                questions.append({
                    'question': row.get('question', ''),
                    'options': options,
                    'correct_answer': correct_answer
                })
                
                # Debug: Log each question as it's parsed
                socketio.emit('job_update', {
                    'job_id': job_id,
                    'progress': 29,
                    'current_step': f'Parsed question {len(questions)}: "{row.get("question", "")[:50]}..."'
                })
            
            # Debug: Log total questions found
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 29,
                'current_step': f'Total questions found in CSV: {len(questions)} (requested: {num_questions})'
            })
            
            # Send questions for review (first 10 max)
            review_questions = questions[:10]
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 30,
                'current_step': f'{len(review_questions)} questions generated. Please review before proceeding.',
                'questions': review_questions
            })
            
            # Store questions for later approval
            active_jobs[job_id]['questions'] = review_questions
            active_jobs[job_id]['status'] = 'waiting_approval'
            active_jobs[job_id]['dataset_uri'] = dataset_uri  # Store dataset URI for later use
            
            # Wait for user approval - don't proceed automatically
            # The pipeline will continue when user clicks "Approve & Generate Video"
            socketio.emit('job_update', {
                'job_id': job_id,
                'progress': 30,
                'current_step': 'Waiting for question approval...',
                'status': 'waiting_approval'
            })
            
            # Return here - don't continue with video generation until approved
            return
        else:
            # Use existing canonical latest.csv (assumes user uploaded earlier)
            if not client.bucket("trivia-automations-2").blob(resolver.canonical_latest_csv_uri().replace("gs://trivia-automations-2/", "")).exists():
                raise RuntimeError("No canonical latest.csv found. Upload a CSV first or switch to Gemini mode.")
            dataset_uri = resolver.canonical_latest_csv_uri()
        
        # Step 2: Setup GCS structure
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 40,
            'current_step': 'Setting up cloud storage...'
        })
        
        job_path = f"jobs/{channel_id}/{job_id}"
        
        # Create jobs bucket if it doesn't exist
        try:
            bucket = client.bucket(GCS_JOBS_BUCKET)
            bucket.reload()
        except Exception:
            bucket = client.create_bucket(GCS_JOBS_BUCKET, location="us-central1")
        
        active_jobs[job_id]['progress'] = 50
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 50,
            'current_step': 'Processing trivia data...'
        })
        
        # Step 3: Save trivia to GCS
        csv_path = save_trivia_to_gcs(dataset_uri, job_path)
        
        active_jobs[job_id]['progress'] = 60
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 60,
            'current_step': 'Creating job manifest...'
        })
        
        # Step 4: Create job manifest
        manifest = create_job_manifest(job_path, csv_path, "dataset", channel_id)
        
        active_jobs[job_id]['progress'] = 70
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 70,
            'current_step': 'Starting video generation...'
        })
        
        # Step 5: Process video generation
        job_info = JobInfo(
            job_id=job_id,
            channel=manifest["channel"],
            gcs_csv_path=manifest["gcs_csv_path"],
            output_bucket=manifest["output_bucket"],
            output_path=manifest["output_path"]
        )
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 80,
            'current_step': 'Generating professional video...'
        })
        
        output_path = process_job(job_info)
        
        # Update manifest with completion
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.now().isoformat()
        manifest["final_video_path"] = output_path
        
        # Save updated manifest
        bucket = client.bucket(GCS_JOBS_BUCKET)
        manifest_blob = bucket.blob(f"jobs/{channel_id}/{job_id}/_MANIFEST.json")
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2),
            content_type="application/json"
        )
        
        # Job completed successfully
        active_jobs[job_id]['status'] = 'completed'
        active_jobs[job_id]['progress'] = 100
        active_jobs[job_id]['current_step'] = 'Video generation completed!'
        active_jobs[job_id]['output_path'] = output_path
        active_jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': 'completed',
            'progress': 100,
            'current_step': 'Video generation completed!',
            'output_path': output_path
        })
        
    except Exception as e:
        # Job failed
        active_jobs[job_id]['status'] = 'failed'
        active_jobs[job_id]['current_step'] = f'Error: {str(e)}'
        active_jobs[job_id]['error'] = str(e)
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': 'failed',
            'current_step': f'Error: {str(e)}',
            'error': str(e)
        })

def continue_video_generation(job_id, channel_id, input_mode, dataset_uri):
    """Continue video generation after question approval or CSV upload"""
    try:
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 42,
            'current_step': f'Initializing video generation for channel: {channel_id}'
        })
        
        client = storage.Client()
        resolver = get_path_resolver_for_channel(channel_id)
        
        # Step 2: Setup GCS structure
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 43,
            'current_step': 'Setting up cloud storage...'
        })
        
        job_path = f"jobs/{channel_id}/{job_id}"
        
        # Create jobs bucket if it doesn't exist
        try:
            bucket = client.bucket(GCS_JOBS_BUCKET)
            bucket.reload()
        except Exception:
            bucket = client.create_bucket(GCS_JOBS_BUCKET, location="us-central1")
        
        active_jobs[job_id]['progress'] = 50
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 50,
            'current_step': 'Processing trivia data...'
        })
        
        # Step 3: Save trivia to GCS
        csv_path = save_trivia_to_gcs(dataset_uri, job_path)
        
        active_jobs[job_id]['progress'] = 60
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 60,
            'current_step': 'Creating job manifest...'
        })
        
        # Step 4: Create job manifest
        manifest = create_job_manifest(job_path, csv_path, "dataset", channel_id)
        
        active_jobs[job_id]['progress'] = 70
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 70,
            'current_step': 'Starting video generation...'
        })
        
        # Step 5: Process video generation
        job_info = JobInfo(
            job_id=job_id,
            channel=manifest["channel"],
            gcs_csv_path=manifest["gcs_csv_path"],
            output_bucket=manifest["output_bucket"],
            output_path=manifest["output_path"]
        )
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 80,
            'current_step': 'Generating professional video...'
        })
        
        output_path = process_job(job_info)
        
        # Update manifest with completion
        manifest["status"] = "completed"
        manifest["completed_at"] = datetime.now().isoformat()
        manifest["final_video_path"] = output_path
        
        # Save updated manifest
        bucket = client.bucket(GCS_JOBS_BUCKET)
        manifest_blob = bucket.blob(f"jobs/{channel_id}/{job_id}/_MANIFEST.json")
        manifest_blob.upload_from_string(
            json.dumps(manifest, indent=2),
            content_type="application/json"
        )
        
        # Update job status
        active_jobs[job_id]['status'] = 'completed'
        active_jobs[job_id]['progress'] = 100
        active_jobs[job_id]['current_step'] = 'Video generation completed!'
        active_jobs[job_id]['output_path'] = output_path
        active_jobs[job_id]['completed_at'] = datetime.now().isoformat()
        
        # Create a signed URL for the final video that expires in 1 hour
        try:
            client = storage.Client()
            bucket = client.bucket(GCS_JOBS_BUCKET)
            blob = bucket.blob(output_path)
            
            # Generate signed URL that expires in 1 hour
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(hours=1),
                method="GET"
            )
            
            socketio.emit('job_update', {
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'current_step': 'Video generation completed!',
                'output_path': output_path,
                'signed_url': signed_url
            })
        except Exception as e:
            print(f"Warning: Could not generate signed URL: {e}")
            # Fall back to regular output path
            socketio.emit('job_update', {
                'job_id': job_id,
                'status': 'completed',
                'progress': 100,
                'current_step': 'Video generation completed!',
                'output_path': output_path
            })
        
    except Exception as e:
        # Update job status
        if job_id in active_jobs:
            active_jobs[job_id]['status'] = 'failed'
            active_jobs[job_id]['current_step'] = f'Error: {str(e)}'
            active_jobs[job_id]['error'] = str(e)
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': 'failed',
            'current_step': f'Error: {str(e)}',
            'error': str(e)
        })
        
        # Log the error for debugging
        print(f"Error in continue_video_generation for job {job_id}: {e}")
        import traceback
        traceback.print_exc()

def save_trivia_to_gcs(dataset_uri: str, job_path: str):
    """Save trivia data to GCS"""
    if dataset_uri.startswith("gs://"):
        parts = dataset_uri.split("/")
        source_bucket = parts[2]
        source_path = "/".join(parts[3:])
        csv_source_path = f"{source_path}/questions.csv"
        
        client = storage.Client()
        source_bucket_obj = client.bucket(source_bucket)
        source_blob = source_bucket_obj.blob(csv_source_path)
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_content = source_blob.download_as_text()
            f.write(csv_content)
            temp_csv_path = f.name
        
        # Upload to our job location
        target_bucket = client.bucket(GCS_JOBS_BUCKET)
        csv_blob_path = f"{job_path}/questions.csv"
        
        csv_blob = target_bucket.blob(csv_blob_path)
        csv_blob.upload_from_filename(temp_csv_path)
        
        # Clean up temp file
        os.unlink(temp_csv_path)
        
        return f"gs://{GCS_JOBS_BUCKET}/{csv_blob_path}"
    else:
        raise ValueError(f"Invalid dataset URI: {dataset_uri}")

def create_job_manifest(job_path: str, csv_path: str, dataset_type: str, channel_id: str):
    """Create job manifest"""
    job_id = job_path.split("/")[-1]
    
    manifest = {
        "job_id": job_id,
        "channel": channel_id,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
        "dataset_type": dataset_type,
        "gcs_csv_path": csv_path,
        "output_bucket": GCS_JOBS_BUCKET,
        "output_path": f"final_videos/{channel_id}/{job_id}/final_video.mp4"
    }
    
    # Save manifest to GCS
    client = storage.Client()
    bucket = client.bucket(GCS_JOBS_BUCKET)
    
    manifest_blob = bucket.blob(f"{job_path}/_MANIFEST.json")
    manifest_blob.upload_from_string(
        json.dumps(manifest, indent=2),
        content_type="application/json"
    )
    
    return manifest

@app.route('/channels', methods=['POST'])
def create_channel():
    """Create a new channel in GCS"""
    try:
        data = request.get_json()
        channel_name = data.get('channel_name')
        channel_id = data.get('channel_id')
        
        if not channel_name or not channel_id:
            return jsonify({'error': 'Missing channel name or ID'}), 400
        
        # Get path resolver for channel
        resolver = get_path_resolver_for_channel(channel_id)
        storage = CloudStorage("trivia-automations-2")  # Use hardcoded bucket
        
        # Create channel directory structure
        storage.ensure_directory(resolver.assets_root_uri())
        storage.ensure_directory(resolver.feeds_csv_input_uri())
        storage.ensure_directory(resolver.feeds_gemini_input_uri())
        
        # Create default channel config
        config = ChannelConfig(
            name=channel_name,
            channel_type="trivia",
            assets={},
            feed_settings={"input_mode": "csv", "tts_voice": "en-US-Neural2-F"},
            run_defaults={"fps": 30, "resolution": "1920x1080", "pause_duration": 2}
        )
        
        # Save channel config
        save_channel_config("trivia-automations-2", channel_id, config)
        
        return jsonify({
            'status': 'success',
            'message': f'Channel {channel_name} created successfully',
            'channel_id': channel_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to create channel: {str(e)}'}), 500

@app.route('/upload_asset', methods=['POST'])
def upload_asset():
    """Upload an asset file for a channel"""
    try:
        if 'file' not in request.files:
            return 'No file provided', 400
        
        file = request.files['file']
        channel_id = request.form.get('channel_id')
        asset_name = request.form.get('asset_name')
        
        if not file.filename or not channel_id or not asset_name:
            return 'Missing required fields', 400
        
        # Get path resolver for channel
        resolver = get_path_resolver_for_channel(channel_id)
        storage = CloudStorage("trivia-automations-2")  # Use hardcoded bucket
        
        # Ensure channel assets directory exists
        assets_dir = resolver.assets_root_uri()
        storage.ensure_directory(assets_dir)
        
        # Determine file extension and create asset path
        file_ext = os.path.splitext(file.filename)[1]
        asset_filename = f"{asset_name.lower()}{file_ext}"
        asset_path = f"{assets_dir}/{asset_filename}"
        
        # Upload file to GCS
        storage.upload_file(file, asset_path)
        
        # Update channel config with asset mapping
        config = load_channel_config("trivia-automations-2", channel_id)
        if not config:
            # Create new config if none exists
            config = ChannelConfig(
                name=channel_id,
                channel_type="trivia",
                assets={},
                feed_settings={"input_mode": "csv", "tts_voice": "en-US-Neural2-F"},
                run_defaults={"fps": 30, "resolution": "1920x1080", "pause_duration": 2}
            )
        
        # Add/update asset mapping
        config.assets[asset_name] = asset_path
        save_channel_config("trivia-automations-2", channel_id, config)
        
        return jsonify({
            'status': 'success',
            'message': f'Asset {asset_name} uploaded successfully',
            'asset_path': asset_path,
            'channel_id': channel_id
        })
        
    except Exception as e:
        return f'Upload failed: {str(e)}', 500

@app.route('/jobs/<job_id>')
def get_job_status(job_id):
    """Get status of a specific job"""
    if job_id in active_jobs:
        return jsonify(active_jobs[job_id])
    else:
        return jsonify({'error': 'Job not found'}), 404

@app.route('/jobs')
def list_jobs():
    """List all active jobs"""
    return jsonify(active_jobs)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'gemini_api_key': 'configured' if GEMINI_API_KEY else 'missing',
        'google_credentials': 'configured' if GOOGLE_APPLICATION_CREDENTIALS else 'missing',
        'timestamp': datetime.now().isoformat()
    })

# Socket.IO event handlers
@socketio.on('approve_questions')
def handle_approve_questions(data):
    """Handle question approval and continue with video generation"""
    job_id = data.get('job_id')
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'approved'
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 40,
            'current_step': 'Questions approved. Continuing with video generation...'
        })
        
        # Continue with the pipeline by starting a new thread
        job_info = active_jobs[job_id]
        
        # Get the dataset URI from the job info
        dataset_uri = active_jobs[job_id].get('dataset_uri', '')
        if not dataset_uri:
            socketio.emit('job_update', {
                'job_id': job_id,
                'status': 'failed',
                'current_step': 'Error: No dataset URI found for video generation'
            })
            return
        
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 41,
            'current_step': f'Starting video generation with dataset: {dataset_uri}'
        })
        
        thread = threading.Thread(
            target=continue_video_generation,
            args=(job_id, job_info['channel_id'], job_info['input_mode'], dataset_uri)
        )
        thread.daemon = True
        thread.start()

@socketio.on('regenerate_questions')
def handle_regenerate_questions(data):
    """Handle question regeneration request"""
    job_id = data.get('job_id')
    if job_id in active_jobs:
        socketio.emit('job_update', {
            'job_id': job_id,
            'progress': 20,
            'current_step': 'Regenerating questions with Gemini...'
        })
        # Would regenerate questions here...

@socketio.on('cancel_job')
def handle_cancel_job(data):
    """Handle job cancellation request"""
    job_id = data.get('job_id')
    if job_id in active_jobs:
        active_jobs[job_id]['status'] = 'cancelled'
        socketio.emit('job_update', {
            'job_id': job_id,
            'status': 'cancelled',
            'current_step': 'Job cancelled by user'
        })

if __name__ == '__main__':
    # Check environment
    if not GOOGLE_APPLICATION_CREDENTIALS:
        print("⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
    
    print("🚀 Starting GCS Video Automation Web Interface...")
    print("🌐 Access at: http://localhost:5050")
    print("📱 You can access this from any computer on your network!")
    
    # Run the app
    socketio.run(app, host='0.0.0.0', port=5050, debug=True, allow_unsafe_werkzeug=True)
