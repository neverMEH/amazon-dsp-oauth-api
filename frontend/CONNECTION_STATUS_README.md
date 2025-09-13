# ConnectionStatus Component

A comprehensive connection status UI component for the Amazon DSP OAuth dashboard with real-time monitoring and token management capabilities.

## Features

### Core Functionality
- **Real-time Connection Status**: Visual indicators showing connected/disconnected state with color-coded badges
- **Token Expiration Tracking**: Live countdown showing time until token expiry with progress bar
- **Auto-Refresh Management**: Toggle automatic token refresh with visual countdown to next refresh
- **Manual Refresh**: Force refresh tokens with a single click
- **Connection Timeline**: Visual timeline showing connection history and upcoming events
- **Error Handling**: Graceful error states with clear messaging

### Visual Features
- **Dark Mode Support**: Fully integrated with the theme system
- **Responsive Design**: Works seamlessly on all screen sizes
- **Beautiful Animations**: Smooth transitions, pulsing indicators, and loading states
- **Accessibility**: ARIA labels, keyboard navigation, and screen reader support

## Installation

The component is already integrated into the project. All required dependencies are installed:
- shadcn/ui components (Card, Badge, Button, Switch, Progress, Alert, Label, Skeleton)
- date-fns for time formatting
- Lucide React for icons

## Usage

### Basic Implementation

```tsx
import { ConnectionStatus } from '@/components/ConnectionStatus';

function Dashboard() {
  return (
    <div>
      <ConnectionStatus />
    </div>
  );
}
```

### With Custom Styling

```tsx
<ConnectionStatus className="mb-6 shadow-lg" />
```

## Demo

To view the component in isolation:

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Start the mock API server:
   ```bash
   node mock-server.js
   ```

3. Navigate to: http://localhost:3000/status-demo

## API Endpoints

The component expects the following API endpoints:

### GET /api/v1/auth/status
Returns the current connection and token status.

**Response:**
```json
{
  "status": "connected",
  "tokenStatus": {
    "isConnected": true,
    "lastRefreshTime": "2024-01-13T10:30:00Z",
    "nextRefreshTime": "2024-01-13T11:00:00Z",
    "expiresAt": "2024-01-13T11:30:00Z",
    "autoRefreshEnabled": true,
    "refreshToken": "token_string",
    "accessToken": "token_string"
  }
}
```

### POST /api/v1/auth/refresh
Refreshes the authentication tokens.

**Response:**
```json
{
  "success": true,
  "message": "Tokens refreshed successfully",
  "tokenStatus": { /* updated token status */ }
}
```

### POST /api/v1/auth/auto-refresh
Toggles automatic token refresh.

**Request Body:**
```json
{
  "enabled": true
}
```

**Response:**
```json
{
  "success": true,
  "enabled": true,
  "message": "Auto-refresh enabled"
}
```

## Component Architecture

### Custom Hook: useTokenStatus
The component uses a custom hook that manages:
- Polling for status updates every second
- Calculating time remaining for token expiry
- Managing refresh operations
- Handling auto-refresh scheduling
- Toast notifications for user feedback

### State Management
- Real-time countdown updates using React hooks
- Automatic cleanup of timers and intervals
- Optimistic UI updates for better UX

### Error Boundaries
The component includes proper error handling:
- Network failures show clear error messages
- Loading states during operations
- Fallback UI for critical errors

## Customization

### Theme Variables
The component respects the application's theme variables defined in CSS:
```css
--background
--foreground
--card
--primary
--secondary
--muted
--destructive
--border
```

### Custom Animations
Additional animations are defined in `index.css`:
- `animate-pulse-slow`: Slow pulsing effect for active states
- `animate-in`: Fade in animation for alerts
- `slide-in-from-top-1`: Slide animation for notifications

## Testing

### Manual Testing
1. **Connection States**: Use the mock server endpoints to test different states
   - `/api/v1/auth/connect` - Simulate connection
   - `/api/v1/auth/disconnect` - Simulate disconnection

2. **Token Refresh**: Click "Refresh Now" to test manual refresh

3. **Auto-Refresh**: Toggle the switch to enable/disable automatic refresh

4. **Error States**: Stop the mock server to test error handling

### Mock Server Commands
```bash
# Connect (simulate successful connection)
curl -X POST http://localhost:8000/api/v1/auth/connect

# Disconnect (simulate disconnection)
curl -X POST http://localhost:8000/api/v1/auth/disconnect

# Check status
curl http://localhost:8000/api/v1/auth/status
```

## Performance Considerations

- **Polling Interval**: Set to 1 second for real-time updates
- **Status Fetch**: Every 30 seconds to sync with backend
- **Memoization**: Time calculations are optimized with useCallback
- **Cleanup**: Proper cleanup of intervals and timeouts

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- All modern mobile browsers

## Troubleshooting

### Component Not Updating
- Check if the API server is running
- Verify CORS settings allow frontend origin
- Check browser console for errors

### Auto-Refresh Not Working
- Ensure `autoRefreshEnabled` is true in API response
- Check if tokens are valid
- Verify browser allows background timers

### Visual Issues
- Clear browser cache
- Check if Tailwind CSS is properly configured
- Verify all required CSS animations are defined

## Future Enhancements

Potential improvements for future versions:
- WebSocket support for real-time updates
- Token refresh history graph
- Multi-account support
- Export token status logs
- Configurable refresh intervals
- Push notifications for token expiry