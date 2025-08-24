import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Dashboard,
  VideoLibrary,
  Settings,
  GitHub,
  Help,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const navItems = [
    { label: 'Dashboard', path: '/', icon: <Dashboard /> },
    { label: 'Assets', path: '/assets', icon: <VideoLibrary /> },
    { label: 'Settings', path: '/settings', icon: <Settings /> },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <AppBar position="static" elevation={1}>
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 0, mr: 4, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          🧰 Trivia Factory
        </Typography>

        <Box sx={{ flexGrow: 1, display: 'flex', gap: 1 }}>
          {navItems.map((item) => (
            <Button
              key={item.path}
              color="inherit"
              startIcon={item.icon}
              onClick={() => navigate(item.path)}
              sx={{
                backgroundColor: isActive(item.path) ? 'rgba(255, 255, 255, 0.1)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                },
              }}
            >
              {item.label}
            </Button>
          ))}
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Documentation">
            <IconButton color="inherit" size="large">
              <Help />
            </IconButton>
          </Tooltip>
          <Tooltip title="GitHub Repository">
            <IconButton color="inherit" size="large">
              <GitHub />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
