import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Button,
  Alert,
  Divider,
} from '@mui/material';
import { PlayArrow, Stop, Download, Refresh } from '@mui/icons-material';

interface JobStatus {
  job_id: string;
  status: string;
  progress: Record<string, any>;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

const JobDetails: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (jobId) {
      fetchJobDetails();
    }
  }, [jobId]);

  const fetchJobDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/jobs/${jobId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch job details');
      }
      const jobData = await response.json();
      setJob(jobData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const cancelJob = async () => {
    try {
      const response = await fetch(`/api/jobs/${jobId}/cancel`, {
        method: 'POST',
      });
      if (response.ok) {
        fetchJobDetails();
      }
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      default:
        return 'info';
    }
  };

  const getProgressValue = () => {
    if (!job?.progress) return 0;
    const stages = ['generating_questions', 'generating_tts', 'generating_videos', 'concatenating'];
    const completedStages = stages.filter(stage => job.progress[stage]?.completed);
    return (completedStages.length / stages.length) * 100;
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading job details...
        </Typography>
      </Box>
    );
  }

  if (error || !job) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error || 'Job not found'}
        </Alert>
        <Button variant="contained" onClick={() => window.history.back()}>
          Go Back
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Job Details
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchJobDetails}
            sx={{ mr: 1 }}
          >
            Refresh
          </Button>
          {job.status === 'pending' && (
            <Button
              variant="contained"
              color="error"
              startIcon={<Stop />}
              onClick={cancelJob}
            >
              Cancel Job
            </Button>
          )}
        </Box>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Job Information
            </Typography>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Job ID
                </Typography>
                <Typography variant="body1">{job.job_id}</Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  label={job.status}
                  color={getStatusColor(job.status) as any}
                  size="small"
                />
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Created
                </Typography>
                <Typography variant="body1">
                  {new Date(job.created_at).toLocaleString()}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="text.secondary">
                  Updated
                </Typography>
                <Typography variant="body1">
                  {new Date(job.updated_at).toLocaleString()}
                </Typography>
              </Grid>
            </Grid>
          </Paper>

          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Progress
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Overall Progress</Typography>
                <Typography variant="body2">{Math.round(getProgressValue())}%</Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={getProgressValue()}
                sx={{ height: 8, borderRadius: 4 }}
              />
            </Box>
            {job.progress && (
              <Grid container spacing={2}>
                {Object.entries(job.progress).map(([stage, data]) => (
                  <Grid item xs={12} sm={6} key={stage}>
                    <Card variant="outlined">
                      <CardContent sx={{ p: 2 }}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {stage.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </Typography>
                        <Chip
                          label={data.completed ? 'Completed' : 'Pending'}
                          color={data.completed ? 'success' : 'default'}
                          size="small"
                        />
                        {data.progress && (
                          <Box sx={{ mt: 1 }}>
                            <LinearProgress
                              variant="determinate"
                              value={data.progress}
                              sx={{ height: 4 }}
                            />
                          </Box>
                        )}
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" gutterBottom>
              Actions
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {job.status === 'completed' && (
                <>
                  <Button
                    variant="contained"
                    startIcon={<PlayArrow />}
                    fullWidth
                  >
                    Preview Video
                  </Button>
                  <Button
                    variant="outlined"
                    startIcon={<Download />}
                    fullWidth
                  >
                    Download Video
                  </Button>
                </>
              )}
              {job.status === 'failed' && (
                <Button
                  variant="contained"
                  color="primary"
                  fullWidth
                >
                  Retry Job
                </Button>
              )}
            </Box>
          </Paper>

          {job.error_message && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom color="error">
                Error Details
              </Typography>
              <Alert severity="error">
                {job.error_message}
              </Alert>
            </Paper>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default JobDetails;
