# Frontend Specification

This is the frontend UI specification for the spec detailed in @.agent-os/specs/2025-09-12-oauth-foundation-infrastructure/spec.md

## UI Overview

A clean, minimalist dashboard built with Next.js 14 and shadcn/ui components to test and monitor the OAuth authentication system with Amazon DSP Campaign Insights API.

## Page Structure

### Main Dashboard (/)

The single-page application displays all authentication information at a glance with real-time updates.

```tsx
// Layout Structure
<main className="container mx-auto p-6 max-w-7xl">
  <Header />              // App title and branding
  <ConnectionStatus />    // Main status card
  <TokenDetails />        // Token information grid
  <AuditLog />           // Recent events table
</main>
```

## Component Specifications

### Header Component
```tsx
interface HeaderProps {
  title: "Amazon DSP OAuth Testing Dashboard"
  subtitle: "Monitor and test your Amazon Advertising API connection"
}
```

**Visual Design:**
- Title: Text-4xl font-bold with purple-700 color
- Subtitle: Text-muted-foreground
- Bottom border with purple-200

### ConnectionStatus Component

**Purpose:** Primary connection status display with action button

**States:**
1. **Disconnected**
   - Background: Neutral gray (bg-gray-50)
   - Icon: X circle in red
   - Button: "Connect to Amazon" (purple-600 primary)
   
2. **Connected**
   - Background: Purple gradient (bg-gradient-to-r from-purple-50 to-purple-100)
   - Icon: Check circle in green
   - Button: Disabled state showing "Connected"

3. **Refreshing**
   - Background: Purple-50 with pulse animation
   - Icon: Spinner with animation
   - Button: Loading state

**Implementation:**
```tsx
<Card className="p-8">
  <CardHeader className="flex flex-row items-center justify-between">
    <div className="flex items-center gap-3">
      <StatusIcon />
      <div>
        <CardTitle>Connection Status</CardTitle>
        <CardDescription>{statusMessage}</CardDescription>
      </div>
    </div>
    <ConnectButton />
  </CardHeader>
</Card>
```

### TokenDetails Component

**Purpose:** Display token information in a grid layout

**Grid Layout:** 2x2 responsive grid with these cards:

1. **Token Status Card**
   - Badge showing "Valid" (green) or "Expired" (red)
   - Token type (Bearer)
   - Scope display

2. **Expiration Timer Card**
   - Countdown timer showing time until expiration
   - Format: "23h 45m 12s" or "Expired"
   - Color transitions: Green > Yellow (< 30min) > Red (< 5min)

3. **Refresh History Card**
   - Last refresh timestamp
   - Total refresh count
   - Next scheduled refresh

4. **Actions Card**
   - Manual refresh button (outlined purple)
   - View full token button (opens modal)
   - Revoke access button (destructive variant)

**Implementation:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
  <Card>
    <CardHeader>
      <CardTitle className="text-sm font-medium">Token Status</CardTitle>
    </CardHeader>
    <CardContent>
      <Badge variant={isValid ? "success" : "destructive"}>
        {isValid ? "Valid" : "Expired"}
      </Badge>
    </CardContent>
  </Card>
  // ... other cards
</div>
```

### CountdownTimer Component

**Purpose:** Real-time countdown to token expiration

**Features:**
- Updates every second
- Color-coded based on time remaining
- Formats: "2d 3h", "45m 30s", "30s"
- Auto-refreshes UI when token is renewed

**Implementation:**
```tsx
const useCountdown = (expiresAt: string) => {
  const [timeLeft, setTimeLeft] = useState(calculateTimeLeft());
  
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft(calculateTimeLeft());
    }, 1000);
    return () => clearInterval(timer);
  }, [expiresAt]);
  
  return timeLeft;
};
```

### AuditLog Component

**Purpose:** Display recent authentication events in a table

**Table Columns:**
- Timestamp (relative time using date-fns)
- Event Type (badge colored by type)
- Status (success/failure icons)
- Details (expandable row)

**Event Types & Colors:**
- `login` - Purple badge
- `refresh` - Blue badge
- `error` - Red badge
- `revoke` - Gray badge

**Implementation:**
```tsx
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Time</TableHead>
      <TableHead>Event</TableHead>
      <TableHead>Status</TableHead>
      <TableHead>Details</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {events.map((event) => (
      <TableRow key={event.id}>
        <TableCell>{formatRelative(event.timestamp)}</TableCell>
        <TableCell>
          <Badge variant={getEventVariant(event.type)}>
            {event.type}
          </Badge>
        </TableCell>
        <TableCell>{getStatusIcon(event.status)}</TableCell>
        <TableCell>
          <Button variant="ghost" size="sm">View</Button>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

## Purple Theme Configuration

### Tailwind Config
```js
theme: {
  extend: {
    colors: {
      purple: {
        50: '#faf5ff',
        100: '#f3e8ff',
        200: '#e9d5ff',
        300: '#d8b4fe',
        400: '#c084fc',
        500: '#a855f7',
        600: '#9333ea',
        700: '#7e22ce',
        800: '#6b21a8',
        900: '#581c87',
        950: '#3b0764',
      }
    }
  }
}
```

### CSS Variables (globals.css)
```css
@layer base {
  :root {
    --primary: 267 83% 58%;        /* purple-600 */
    --primary-foreground: 0 0% 98%;
    --secondary: 267 30% 95%;       /* purple-50 */
    --accent: 267 60% 95%;          /* purple-100 */
    --muted: 267 20% 95%;
    --border: 267 30% 90%;          /* purple-200 */
    --ring: 267 83% 58%;            /* purple-600 */
  }
}
```

## API Integration

### Polling Strategy
```typescript
// Auth status polling every 5 seconds
const { data: authStatus } = useQuery({
  queryKey: ['auth-status'],
  queryFn: fetchAuthStatus,
  refetchInterval: 5000,
  refetchIntervalInBackground: true,
});

// Audit log polling every 10 seconds
const { data: auditLog } = useQuery({
  queryKey: ['audit-log'],
  queryFn: fetchAuditLog,
  refetchInterval: 10000,
});
```

### API Client Functions
```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const authApi = {
  getLoginUrl: async () => {
    const res = await axios.get(`${API_BASE}/api/v1/auth/amazon/login`);
    return res.data;
  },
  
  getStatus: async () => {
    const res = await axios.get(`${API_BASE}/api/v1/auth/status`);
    return res.data;
  },
  
  refreshToken: async () => {
    const res = await axios.post(`${API_BASE}/api/v1/auth/refresh`);
    return res.data;
  },
  
  getAuditLog: async (limit = 10) => {
    const res = await axios.get(`${API_BASE}/api/v1/auth/audit`, {
      params: { limit }
    });
    return res.data;
  }
};
```

## User Interactions

### Connect Flow
1. User clicks "Connect to Amazon" button
2. Button shows loading state
3. Fetch auth URL from backend
4. Redirect to Amazon OAuth page
5. After callback, show success toast
6. Update UI to connected state

### Manual Refresh Flow
1. User clicks "Refresh Token" button
2. Button shows spinner
3. Call refresh endpoint
4. Show success/error toast
5. Update countdown timer
6. Add entry to audit log

### Error States
- Connection timeout: Show alert with retry button
- Invalid token: Show warning badge with re-connect option
- API errors: Display error toast with details
- Network issues: Show offline indicator

## Responsive Design

### Breakpoints
- Mobile: < 640px (single column)
- Tablet: 640px - 1024px (2 columns)
- Desktop: > 1024px (full layout)

### Mobile Adaptations
- Stack cards vertically
- Collapse audit log to summary
- Simplify countdown to minutes only
- Full-width buttons

## Accessibility

### ARIA Labels
- All interactive elements have proper labels
- Status changes announced to screen readers
- Keyboard navigation supported throughout

### Focus Management
- Clear focus indicators (purple ring)
- Logical tab order
- Skip links for navigation

### Color Contrast
- All text meets WCAG AA standards
- Status indicators have text alternatives
- Not solely reliant on color for information

## Performance Optimizations

### Code Splitting
```typescript
// Lazy load heavy components
const AuditLog = dynamic(() => import('./AuditLog'), {
  loading: () => <Skeleton className="h-[400px]" />,
});
```

### Caching Strategy
- React Query caches API responses
- Stale-while-revalidate for non-critical data
- Optimistic updates for user actions

### Bundle Size
- Tree-shake unused shadcn components
- Purge unused Tailwind classes
- Minimize third-party dependencies