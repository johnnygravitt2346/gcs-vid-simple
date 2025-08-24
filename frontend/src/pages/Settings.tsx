import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  TextField,
  Button,
  Switch,
  FormControlLabel,
  Divider,
  Alert,
  Card,
  CardContent,
  CardHeader,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Slider,
  Chip,
} from '@mui/material';
import { Save, Refresh, Build } from '@mui/icons-material';

interface Settings {
  gcp: {
    project_id: string;
    region: string;
    zone: string;
  };
  storage: {
    bucket_name: string;
    assets_prefix: string;
    questions_prefix: string;
    videos_prefix: string;
    temp_prefix: string;
  };
  gemini: {
    model: string;
    max_tokens: number;
    temperature: number;
    max_questions_per_batch: number;
  };
  video: {
    resolution: string;
    fps: number;
    codec: string;
    quality: string;
    max_duration_per_question: number;
    pause_after_question: number;
  };
  tts: {
    voice: string;
    speed: number;
    sample_rate: number;
  };
  pipeline: {
    max_concurrent_jobs: number;
    preemptible_workers: boolean;
    cleanup_temp_files: boolean;
    max_retries: number;
  };
  ui: {
    host: string;
    port: number;
    debug: boolean;
    max_upload_size: string;
  };
}

const Settings: React.FC = () => {
  const [settings, setSettings] = useState<Settings>({
    gcp: {
      project_id: 'mythic-groove-469801-b7',
      region: 'us-central1',
      zone: 'us-central1-a',
    },
    storage: {
      bucket_name: 'trivia-factory-prod',
      assets_prefix: 'assets/',
      questions_prefix: 'questions/',
      videos_prefix: 'videos/',
      temp_prefix: 'temp/',
    },
    gemini: {
      model: 'gemini-1.5-flash',
      max_tokens: 1000,
      temperature: 0.7,
      max_questions_per_batch: 50,
    },
    video: {
      resolution: '1920x1080',
      fps: 30,
      codec: 'h264_nvenc',
      quality: 'medium',
      max_duration_per_question: 15,
      pause_after_question: 5.0,
    },
    tts: {
      voice: 'en-US-Neural2-F',
      speed: 1.0,
      sample_rate: 44100,
    },
    pipeline: {
      max_concurrent_jobs: 10,
      preemptible_workers: true,
      cleanup_temp_files: true,
      max_retries: 3,
    },
    ui: {
      host: '0.0.0.0',
      port: 8080,
      debug: false,
      max_upload_size: '100MB',
    },
  });

  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      // Mock loading - replace with actual API call
      // const response = await fetch('/api/settings');
      // const data = await response.json();
      // setSettings(data);
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      // Mock save - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings' });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setSaving(false);
    }
  };

  const handleTestConnection = async () => {
    try {
      setTesting(true);
      // Mock test - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      setMessage({ type: 'success', text: 'Connection test successful!' });
      setTimeout(() => setMessage(null), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: 'Connection test failed' });
      setTimeout(() => setMessage(null), 3000);
    } finally {
      setTesting(false);
    }
  };

  const updateSetting = (path: string, value: any) => {
    const keys = path.split('.');
    setSettings(prev => {
      const newSettings = { ...prev };
      let current: any = newSettings;
      for (let i = 0; i < keys.length - 1; i++) {
        current = current[keys[i]];
      }
      current[keys[keys.length - 1]] = value;
      return newSettings;
    });
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Settings
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Build />}
            onClick={handleTestConnection}
            disabled={testing}
            sx={{ mr: 1 }}
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </Button>
        </Box>
      </Box>

      {message && (
        <Alert severity={message.type} sx={{ mb: 3 }}>
          {message.text}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Google Cloud Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Google Cloud Configuration" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Project ID"
                    value={settings.gcp.project_id}
                    onChange={(e) => updateSetting('gcp.project_id', e.target.value)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Region"
                    value={settings.gcp.region}
                    onChange={(e) => updateSetting('gcp.region', e.target.value)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Zone"
                    value={settings.gcp.zone}
                    onChange={(e) => updateSetting('gcp.zone', e.target.value)}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Storage Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Storage Configuration" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Bucket Name"
                    value={settings.storage.bucket_name}
                    onChange={(e) => updateSetting('storage.bucket_name', e.target.value)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Assets Prefix"
                    value={settings.storage.assets_prefix}
                    onChange={(e) => updateSetting('storage.assets_prefix', e.target.value)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Videos Prefix"
                    value={settings.storage.videos_prefix}
                    onChange={(e) => updateSetting('storage.videos_prefix', e.target.value)}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Gemini AI Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Gemini AI Configuration" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControl fullWidth>
                    <InputLabel>Model</InputLabel>
                    <Select
                      value={settings.gemini.model}
                      label="Model"
                      onChange={(e) => updateSetting('gemini.model', e.target.value)}
                    >
                      <MenuItem value="gemini-1.5-flash">Gemini 1.5 Flash</MenuItem>
                      <MenuItem value="gemini-1.5-pro">Gemini 1.5 Pro</MenuItem>
                      <MenuItem value="gemini-2.0-flash">Gemini 2.0 Flash</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Tokens"
                    value={settings.gemini.max_tokens}
                    onChange={(e) => updateSetting('gemini.max_tokens', parseInt(e.target.value))}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Temperature"
                    value={settings.gemini.temperature}
                    onChange={(e) => updateSetting('gemini.temperature', parseFloat(e.target.value))}
                    inputProps={{ step: 0.1, min: 0, max: 1 }}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Video Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Video Generation" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <FormControl fullWidth>
                    <InputLabel>Resolution</InputLabel>
                    <Select
                      value={settings.video.resolution}
                      label="Resolution"
                      onChange={(e) => updateSetting('video.resolution', e.target.value)}
                    >
                      <MenuItem value="1920x1080">1920x1080 (Full HD)</MenuItem>
                      <MenuItem value="1280x720">1280x720 (HD)</MenuItem>
                      <MenuItem value="854x480">854x480 (SD)</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="FPS"
                    value={settings.video.fps}
                    onChange={(e) => updateSetting('video.fps', parseInt(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12}>
                  <Typography gutterBottom>Max Duration per Question: {settings.video.max_duration_per_question}s</Typography>
                  <Slider
                    value={settings.video.max_duration_per_question}
                    onChange={(_, value) => updateSetting('video.max_duration_per_question', value)}
                    min={5}
                    max={30}
                    step={1}
                    marks
                    valueLabelDisplay="auto"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Pipeline Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="Pipeline Configuration" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.pipeline.preemptible_workers}
                        onChange={(e) => updateSetting('pipeline.preemptible_workers', e.target.checked)}
                      />
                    }
                    label="Use Preemptible Workers"
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.pipeline.cleanup_temp_files}
                        onChange={(e) => updateSetting('pipeline.cleanup_temp_files', e.target.checked)}
                      />
                    }
                    label="Cleanup Temporary Files"
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Concurrent Jobs"
                    value={settings.pipeline.max_concurrent_jobs}
                    onChange={(e) => updateSetting('pipeline.max_concurrent_jobs', parseInt(e.target.value))}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Max Retries"
                    value={settings.pipeline.max_retries}
                    onChange={(e) => updateSetting('pipeline.max_retries', parseInt(e.target.value))}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* UI Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardHeader title="UI Configuration" />
            <CardContent>
              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Host"
                    value={settings.ui.host}
                    onChange={(e) => updateSetting('ui.host', e.target.value)}
                  />
                </Grid>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    type="number"
                    label="Port"
                    value={settings.ui.port}
                    onChange={(e) => updateSetting('ui.port', parseInt(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.ui.debug}
                        onChange={(e) => updateSetting('ui.debug', e.target.checked)}
                      />
                    }
                    label="Debug Mode"
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Max Upload Size"
                    value={settings.ui.max_upload_size}
                    onChange={(e) => updateSetting('ui.max_upload_size', e.target.value)}
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Settings;
