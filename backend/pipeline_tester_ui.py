#!/usr/bin/env python3
"""
Trivia Factory Pipeline Tester UI

Streamlit-based interface for testing the complete pipeline.
Runs on the same VM as the API and worker for the first test.
"""

import streamlit as st
import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any

# Page configuration
st.set_page_config(
    page_title="Trivia Factory Pipeline Tester",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CHANNEL_ID = os.getenv("CHANNEL_ID", "default")

# Initialize session state
if "jobs" not in st.session_state:
    st.session_state.jobs = {}
if "current_job" not in st.session_state:
    st.session_state.current_job = None

def check_api_health():
    """Check if the API is accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/test/health", timeout=5)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {"error": str(e)}

def create_job(topic: str, difficulty: str, question_count: int, category: str, video_style: str, quality: str):
    """Create a new pipeline job"""
    try:
        payload = {
            "topic": topic,
            "difficulty": difficulty,
            "question_count": question_count,
            "category": category,
            "video_style": video_style,
            "quality": quality
        }
        
        response = requests.post(f"{API_BASE_URL}/api/jobs", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to create job: {response.text}")
            return None
    except Exception as e:
        st.error(f"Error creating job: {e}")
        return None

def get_job_status(job_id: str):
    """Get the current status of a job"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error getting job status: {e}")
        return None

def list_jobs():
    """List all jobs"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/jobs", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        st.error(f"Error listing jobs: {e}")
        return []

def get_job_output(job_id: str):
    """Get output files for a completed job"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/jobs/{job_id}/output", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except Exception as e:
        st.error(f"Error getting job output: {e}")
        return None

def main():
    """Main Streamlit application"""
    
    # Header
    st.title("🎬 Trivia Factory Pipeline Tester")
    st.markdown("**First Test Topology**: API + Worker + UI on the same VM")
    
    # Sidebar configuration
    st.sidebar.header("🔧 Configuration")
    st.sidebar.markdown(f"**API Base URL**: `{API_BASE_URL}`")
    st.sidebar.markdown(f"**Channel ID**: `{CHANNEL_ID}`")
    
    # Health check
    st.sidebar.header("🏥 System Health")
    health_status, health_data = check_api_health()
    
    if health_status:
        st.sidebar.success("✅ API Healthy")
        st.sidebar.json(health_data)
    else:
        st.sidebar.error("❌ API Unhealthy")
        st.sidebar.error(f"Error: {health_data.get('error', 'Unknown')}")
        st.warning("⚠️ Make sure the API is running on the VM")
        return
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Create Job", "📊 Job Monitor", "📁 Job Outputs"])
    
    with tab1:
        st.header("Create New Pipeline Job")
        
        # Job creation form
        with st.form("job_creation"):
            col1, col2 = st.columns(2)
            
            with col1:
                topic = st.text_input("Topic", placeholder="e.g., World History, Science, Movies")
                difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
                question_count = st.slider("Number of Questions", 1, 20, 5)
            
            with col2:
                category = st.selectbox("Category", ["General", "Science", "History", "Geography", "Entertainment", "Sports"])
                video_style = st.selectbox("Video Style", ["modern", "classic", "minimal", "colorful"])
                quality = st.selectbox("Quality", ["low", "medium", "high"])
            
            submitted = st.form_submit_button("🚀 Create Job", type="primary")
            
            if submitted:
                if topic.strip():
                    with st.spinner("Creating job..."):
                        job_data = create_job(topic, difficulty, question_count, category, video_style, quality)
                        
                        if job_data:
                            st.success(f"✅ Job created successfully!")
                            st.json(job_data)
                            
                            # Store job in session state
                            job_id = job_data.get("job_id")
                            if job_id:
                                st.session_state.current_job = job_id
                                st.session_state.jobs[job_id] = {
                                    "topic": topic,
                                    "difficulty": difficulty,
                                    "question_count": question_count,
                                    "category": category,
                                    "video_style": video_style,
                                    "quality": quality,
                                    "created_at": datetime.now().isoformat()
                                }
                        else:
                            st.error("❌ Failed to create job")
                else:
                    st.error("Please enter a topic for the job")
    
    with tab2:
        st.header("Job Monitoring")
        
        # Refresh button
        if st.button("🔄 Refresh Jobs"):
            st.rerun()
        
        # Get current jobs
        jobs = list_jobs()
        
        if not jobs:
            st.info("No jobs found. Create a job in the first tab!")
        else:
            st.subheader(f"Active Jobs ({len(jobs)})")
            
            for job in jobs:
                with st.expander(f"Job {job.get('job_id', 'Unknown')} - {job.get('status', 'Unknown')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Status**: {job.get('status', 'Unknown')}")
                        st.markdown(f"**Created**: {job.get('created_at', 'Unknown')}")
                        st.markdown(f"**Updated**: {job.get('updated_at', 'Unknown')}")
                    
                    with col2:
                        if job.get('progress'):
                            st.markdown("**Progress:**")
                            progress_data = job.get('progress', {})
                            
                            # Display milestone progress
                            milestones = ["Health", "Questions", "Segments", "Concat", "Finalize"]
                            for milestone in milestones:
                                status = progress_data.get(milestone.lower(), "pending")
                                if status == "completed":
                                    st.success(f"✅ {milestone}")
                                elif status == "running":
                                    st.info(f"🔄 {milestone}")
                                elif status == "failed":
                                    st.error(f"❌ {milestone}")
                                else:
                                    st.info(f"⏳ {milestone}")
                    
                    # Show error if any
                    if job.get('error_message'):
                        st.error(f"**Error**: {job.get('error_message')}")
    
    with tab3:
        st.header("Job Outputs")
        
        if st.session_state.current_job:
            st.info(f"Current job: {st.session_state.current_job}")
            
            # Get job output
            output = get_job_output(st.session_state.current_job)
            
            if output:
                st.success("✅ Job completed! Output files:")
                st.json(output)
                
                # Display download links (these would be GCS URLs)
                if output.get('final_video'):
                    st.markdown(f"**Final Video**: {output['final_video']}")
                
                if output.get('individual_clips'):
                    st.markdown(f"**Individual Clips**: {output['individual_clips']}")
                
                if output.get('questions'):
                    st.markdown("**Generated Questions:**")
                    for i, question in enumerate(output['questions'], 1):
                        st.markdown(f"{i}. {question}")
            else:
                st.info("Job output not available yet. Check the Job Monitor tab for status.")
        else:
            st.info("No job selected. Create a job in the first tab!")
    
    # Footer
    st.markdown("---")
    st.markdown("**Pipeline Flow**: Health → Questions → Segments → Concat → Finalize")
    st.markdown("**Expected Output**: Artifacts in GCS bucket with `_MANIFEST.json` in `final/`")

if __name__ == "__main__":
    main()
