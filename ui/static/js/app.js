// Trivia Factory Pipeline Tester - Frontend JavaScript

class TriviaFactoryUI {
    constructor() {
        this.jobs = [];
        this.refreshInterval = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadJobs();
        this.startAutoRefresh();
    }

    bindEvents() {
        // Job creation form
        document.getElementById('jobForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.createJob();
        });

        // Asset upload form
        document.getElementById('uploadForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadAssets();
        });
    }

    async createJob() {
        const form = document.getElementById('jobForm');
        const formData = new FormData(form);
        
        const jobData = {
            topic: formData.get('topic'),
            difficulty: formData.get('difficulty'),
            question_count: parseInt(formData.get('questionCount')),
            category: formData.get('category'),
            video_style: 'modern',
            quality: formData.get('quality')
        };

        try {
            this.showLoading('Creating job...');
            
            const response = await fetch('/api/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(jobData)
            });

            if (response.ok) {
                const result = await response.json();
                this.showSuccess(`Job created successfully! ID: ${result.job_id}`);
                form.reset();
                this.loadJobs();
            } else {
                const error = await response.json();
                this.showError(`Failed to create job: ${error.detail}`);
            }
        } catch (error) {
            this.showError(`Error creating job: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    async loadJobs() {
        try {
            const response = await fetch('/api/jobs');
            if (response.ok) {
                this.jobs = await response.json();
                this.renderJobs();
            }
        } catch (error) {
            console.error('Failed to load jobs:', error);
        }
    }

    renderJobs() {
        const jobsList = document.getElementById('jobsList');
        
        if (this.jobs.length === 0) {
            jobsList.innerHTML = `
                <div class="text-center text-gray-500 py-8">
                    <div class="text-4xl mb-2">📋</div>
                    <p>No active jobs</p>
                    <p class="text-sm">Create a job to get started</p>
                </div>
            `;
            return;
        }

        jobsList.innerHTML = this.jobs.map(job => this.renderJobCard(job)).join('');
    }

    renderJobCard(job) {
        const progress = this.calculateProgress(job.progress);
        const statusClass = `job-status ${job.status}`;
        
        return `
            <div class="job-card cursor-pointer" onclick="ui.showJobDetails('${job.job_id}')">
                <div class="flex justify-between items-start mb-3">
                    <div>
                        <h3 class="font-medium text-gray-800">${job.config.topic || 'Untitled'}</h3>
                        <p class="text-sm text-gray-600">ID: ${job.job_id}</p>
                    </div>
                    <span class="${statusClass}">${this.formatStatus(job.status)}</span>
                </div>
                
                <div class="mb-3">
                    <div class="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>${progress}%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                </div>
                
                <div class="flex justify-between items-center text-sm text-gray-500">
                    <span>Created: ${this.formatDate(job.created_at)}</span>
                    <button onclick="event.stopPropagation(); ui.cancelJob('${job.job_id}')" 
                            class="text-red-600 hover:text-red-800">
                        Cancel
                    </button>
                </div>
            </div>
        `;
    }

    calculateProgress(progress) {
        if (!progress) return 0;
        
        const steps = ['questions_generated', 'tts_generated', 'videos_generated', 'final_video_created'];
        const completed = steps.filter(step => progress[step]).length;
        return Math.round((completed / steps.length) * 100);
    }

    formatStatus(status) {
        return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    async showJobDetails(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}`);
            if (response.ok) {
                const job = await response.json();
                this.openJobModal(job);
            }
        } catch (error) {
            console.error('Failed to load job details:', error);
        }
    }

    openJobModal(job) {
        const modal = document.getElementById('jobModal');
        const details = document.getElementById('jobDetails');
        
        details.innerHTML = `
            <div class="space-y-4">
                <div>
                    <h4 class="font-medium text-gray-700">Configuration</h4>
                    <div class="bg-gray-50 p-3 rounded text-sm">
                        <p><strong>Topic:</strong> ${job.config.topic || 'N/A'}</p>
                        <p><strong>Difficulty:</strong> ${job.config.difficulty || 'N/A'}</p>
                        <p><strong>Category:</strong> ${job.config.category || 'N/A'}</p>
                        <p><strong>Question Count:</strong> ${job.config.question_count || 'N/A'}</p>
                    </div>
                </div>
                
                <div>
                    <h4 class="font-medium text-gray-700">Progress</h4>
                    <div class="bg-gray-50 p-3 rounded text-sm">
                        <p><strong>Status:</strong> <span class="${this.getStatusClass(job.status)}">${this.formatStatus(job.status)}</span></p>
                        <p><strong>Questions Generated:</strong> ${job.progress.questions_generated || 0}</p>
                        <p><strong>TTS Generated:</strong> ${job.progress.tts_generated || 0}</p>
                        <p><strong>Videos Generated:</strong> ${job.progress.videos_generated || 0}</p>
                        <p><strong>Final Video:</strong> ${job.progress.final_video_created ? 'Yes' : 'No'}</p>
                    </div>
                </div>
                
                ${job.error_message ? `
                    <div>
                        <h4 class="font-medium text-red-700">Error</h4>
                        <div class="bg-red-50 p-3 rounded text-sm text-red-700">
                            ${job.error_message}
                        </div>
                    </div>
                ` : ''}
                
                <div class="flex justify-end space-x-3">
                    <button onclick="ui.closeJobModal()" 
                            class="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50">
                        Close
                    </button>
                    ${job.status === 'completed' ? `
                        <button onclick="ui.downloadOutput('${job.job_id}')" 
                                class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                            Download Output
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.classList.add('modal-open');
    }

    closeJobModal() {
        const modal = document.getElementById('jobModal');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        document.body.classList.remove('modal-open');
    }

    getStatusClass(status) {
        return `job-status ${status}`;
    }

    async cancelJob(jobId) {
        if (!confirm('Are you sure you want to cancel this job?')) return;
        
        try {
            const response = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
            if (response.ok) {
                this.showSuccess('Job cancelled successfully');
                this.loadJobs();
            } else {
                this.showError('Failed to cancel job');
            }
        } catch (error) {
            this.showError(`Error cancelling job: ${error.message}`);
        }
    }

    async downloadOutput(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}/output`);
            if (response.ok) {
                const output = await response.json();
                this.showSuccess(`Output available at: ${output.final_video}`);
            }
        } catch (error) {
            this.showError(`Error downloading output: ${error.message}`);
        }
    }

    async uploadAssets() {
        const form = document.getElementById('uploadForm');
        const formData = new FormData(form);
        
        try {
            this.showLoading('Uploading assets...');
            
            // Handle multiple file uploads
            const files = formData.getAll('templates').concat(formData.getAll('fonts'));
            
            for (const file of files) {
                if (file.size > 0) {
                    const uploadData = new FormData();
                    uploadData.append('file', file);
                    
                    const response = await fetch('/api/upload/assets', {
                        method: 'POST',
                        body: uploadData
                    });
                    
                    if (!response.ok) {
                        throw new Error(`Failed to upload ${file.name}`);
                    }
                }
            }
            
            this.showSuccess('Assets uploaded successfully!');
            form.reset();
            
        } catch (error) {
            this.showError(`Error uploading assets: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            this.loadJobs();
        }, 10000); // Refresh every 10 seconds
    }

    showLoading(message) {
        // Simple loading indicator
        const button = document.querySelector('#jobForm button[type="submit"]');
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="loading"></span> ' + message;
        }
    }

    hideLoading() {
        const button = document.querySelector('#jobForm button[type="submit"]');
        if (button) {
            button.disabled = false;
            button.innerHTML = '🚀 Start Pipeline Job';
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg z-50 ${
            type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize UI when page loads
let ui;
document.addEventListener('DOMContentLoaded', () => {
    ui = new TriviaFactoryUI();
});

// Global functions for onclick handlers
window.ui = null;
document.addEventListener('DOMContentLoaded', () => {
    window.ui = ui;
});
