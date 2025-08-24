import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CardMedia,
  Button,
  Chip,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Add,
  Upload,
  Delete,
  Edit,
  PlayArrow,
  Download,
  CloudUpload,
} from '@mui/icons-material';

interface Asset {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'font' | 'image';
  url: string;
  size: string;
  uploaded_at: string;
  status: 'active' | 'processing' | 'error';
}

const AssetManager: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchAssets();
  }, []);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      // Mock data for now - replace with actual API call
      const mockAssets: Asset[] = [
        {
          id: '1',
          name: 'video_template_1.mp4',
          type: 'video',
          url: 'gs://trivia-factory-prod/assets/video_template_1.mp4',
          size: '15.2 MB',
          uploaded_at: '2024-01-15T10:30:00Z',
          status: 'active',
        },
        {
          id: '2',
          name: 'video_template_2.mp4',
          type: 'video',
          url: 'gs://trivia-factory-prod/assets/video_template_2.mp4',
          size: '18.7 MB',
          uploaded_at: '2024-01-15T10:35:00Z',
          status: 'active',
        },
        {
          id: '3',
          name: 'background_music.mp3',
          type: 'audio',
          url: 'gs://trivia-factory-prod/assets/background_music.mp3',
          size: '8.5 MB',
          uploaded_at: '2024-01-15T10:40:00Z',
          status: 'active',
        },
        {
          id: '4',
          name: 'Roboto-Bold.ttf',
          type: 'font',
          url: 'gs://trivia-factory-prod/assets/Roboto-Bold.ttf',
          size: '1.2 MB',
          uploaded_at: '2024-01-15T10:45:00Z',
          status: 'active',
        },
      ];
      setAssets(mockAssets);
    } catch (error) {
      console.error('Failed to fetch assets:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      // Mock upload - replace with actual API call
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const newAsset: Asset = {
        id: Date.now().toString(),
        name: selectedFile.name,
        type: getFileType(selectedFile.name),
        url: `gs://trivia-factory-prod/assets/${selectedFile.name}`,
        size: formatFileSize(selectedFile.size),
        uploaded_at: new Date().toISOString(),
        status: 'active',
      };

      setAssets(prev => [newAsset, ...prev]);
      setUploadDialogOpen(false);
      setSelectedFile(null);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  const getFileType = (filename: string): Asset['type'] => {
    const ext = filename.toLowerCase().split('.').pop();
    if (['mp4', 'avi', 'mov', 'mkv'].includes(ext || '')) return 'video';
    if (['mp3', 'wav', 'aac'].includes(ext || '')) return 'audio';
    if (['ttf', 'otf', 'woff'].includes(ext || '')) return 'font';
    return 'image';
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const deleteAsset = async (assetId: string) => {
    try {
      // Mock delete - replace with actual API call
      setAssets(prev => prev.filter(asset => asset.id !== assetId));
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  const getStatusColor = (status: Asset['status']) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'processing':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  const getTypeIcon = (type: Asset['type']) => {
    switch (type) {
      case 'video':
        return <PlayArrow />;
      case 'audio':
        return <PlayArrow />;
      case 'font':
        return <Typography variant="h6">T</Typography>;
      case 'image':
        return <Typography variant="h6">🖼️</Typography>;
      default:
        return <Typography variant="h6">📄</Typography>;
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" gutterBottom>
          Asset Manager
        </Typography>
        <Typography>Loading assets...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Asset Manager
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => setUploadDialogOpen(true)}
        >
          Upload Asset
        </Button>
      </Box>

      <Grid container spacing={3}>
        {assets.map((asset) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={asset.id}>
            <Card>
              <CardMedia
                component="div"
                sx={{
                  height: 140,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: 'grey.100',
                }}
              >
                {getTypeIcon(asset.type)}
              </CardMedia>
              <CardContent>
                <Typography variant="h6" noWrap gutterBottom>
                  {asset.name}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Chip
                    label={asset.type}
                    size="small"
                    variant="outlined"
                  />
                  <Chip
                    label={asset.status}
                    color={getStatusColor(asset.status) as any}
                    size="small"
                  />
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Size: {asset.size}
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Uploaded: {new Date(asset.uploaded_at).toLocaleDateString()}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Tooltip title="Download">
                    <IconButton size="small">
                      <Download />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Edit">
                    <IconButton size="small">
                      <Edit />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => deleteAsset(asset.id)}
                    >
                      <Delete />
                    </IconButton>
                  </Tooltip>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Upload Dialog */}
      <Dialog open={uploadDialogOpen} onClose={() => setUploadDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Upload New Asset</DialogTitle>
        <DialogContent>
          <Box sx={{ p: 2 }}>
            <input
              accept="video/*,audio/*,font/*,image/*,.ttf,.otf,.woff"
              style={{ display: 'none' }}
              id="asset-file-input"
              type="file"
              onChange={handleFileSelect}
            />
            <label htmlFor="asset-file-input">
              <Button
                variant="outlined"
                component="span"
                startIcon={<CloudUpload />}
                fullWidth
                sx={{ mb: 2 }}
              >
                Select File
              </Button>
            </label>
            {selectedFile && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Selected: {selectedFile.name} ({formatFileSize(selectedFile.size)})
              </Alert>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUploadDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleUpload}
            variant="contained"
            disabled={!selectedFile || uploading}
            startIcon={uploading ? undefined : <Upload />}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AssetManager;
