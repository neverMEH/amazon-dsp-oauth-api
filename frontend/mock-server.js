import express from 'express';
import cors from 'cors';
const app = express();
const port = 8000;

app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true
}));
app.use(express.json());

// Mock token status
let mockTokenStatus = {
  isConnected: true,
  lastRefreshTime: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
  nextRefreshTime: new Date(Date.now() + 30 * 60 * 1000).toISOString(), // 30 minutes from now
  expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(), // 1 hour from now
  autoRefreshEnabled: true,
  refreshToken: 'mock_refresh_token_xyz123',
  accessToken: 'mock_access_token_abc456',
};

// GET /api/v1/auth/status
app.get('/api/v1/auth/status', (req, res) => {
  const status = mockTokenStatus.isConnected ? 'connected' : 'disconnected';
  
  res.json({
    status,
    tokenStatus: mockTokenStatus,
    message: `Connection is ${status}`,
  });
});

// POST /api/v1/auth/refresh
app.post('/api/v1/auth/refresh', (req, res) => {
  // Simulate refresh delay
  setTimeout(() => {
    // Update mock data
    mockTokenStatus = {
      ...mockTokenStatus,
      lastRefreshTime: new Date().toISOString(),
      nextRefreshTime: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
      expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      accessToken: `mock_access_token_${Date.now()}`,
    };

    res.json({
      success: true,
      message: 'Tokens refreshed successfully',
      tokenStatus: mockTokenStatus,
    });
  }, 1000);
});

// POST /api/v1/auth/auto-refresh
app.post('/api/v1/auth/auto-refresh', (req, res) => {
  const { enabled } = req.body;
  
  mockTokenStatus.autoRefreshEnabled = enabled;
  
  res.json({
    success: true,
    enabled: mockTokenStatus.autoRefreshEnabled,
    message: `Auto-refresh ${enabled ? 'enabled' : 'disabled'}`,
  });
});

// POST /api/v1/auth/disconnect
app.post('/api/v1/auth/disconnect', (req, res) => {
  mockTokenStatus = {
    ...mockTokenStatus,
    isConnected: false,
    accessToken: null,
    refreshToken: null,
    expiresAt: null,
    nextRefreshTime: null,
  };
  
  res.json({
    success: true,
    message: 'Disconnected successfully',
  });
});

// POST /api/v1/auth/connect
app.post('/api/v1/auth/connect', (req, res) => {
  mockTokenStatus = {
    isConnected: true,
    lastRefreshTime: new Date().toISOString(),
    nextRefreshTime: new Date(Date.now() + 30 * 60 * 1000).toISOString(),
    expiresAt: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
    autoRefreshEnabled: true,
    refreshToken: `mock_refresh_token_${Date.now()}`,
    accessToken: `mock_access_token_${Date.now()}`,
  };
  
  res.json({
    success: true,
    message: 'Connected successfully',
    tokenStatus: mockTokenStatus,
  });
});

app.listen(port, () => {
  console.log(`Mock API server running at http://localhost:${port}`);
  console.log('Available endpoints:');
  console.log('  GET  /api/v1/auth/status');
  console.log('  POST /api/v1/auth/refresh');
  console.log('  POST /api/v1/auth/auto-refresh');
  console.log('  POST /api/v1/auth/disconnect');
  console.log('  POST /api/v1/auth/connect');
});