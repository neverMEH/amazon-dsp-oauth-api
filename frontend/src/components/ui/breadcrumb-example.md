# Breadcrumb Navigation Usage Guide

The breadcrumb navigation component has been successfully integrated into your application. Here's how to use it:

## Basic Usage

The breadcrumb component automatically generates breadcrumbs based on the current route:

```tsx
import { ResponsiveBreadcrumbNav } from '@/components/ui/breadcrumb';

// In your component
<ResponsiveBreadcrumbNav />
```

## Custom Breadcrumbs

You can also provide custom breadcrumb items:

```tsx
import { ResponsiveBreadcrumbNav, BreadcrumbItem } from '@/components/ui/breadcrumb';
import { Home, Settings, User } from 'lucide-react';

const customBreadcrumbs: BreadcrumbItem[] = [
  { label: 'Home', href: '/dashboard', icon: Home },
  { label: 'Settings', href: '/settings', icon: Settings },
  { label: 'Profile' } // Current page, no href
];

<ResponsiveBreadcrumbNav items={customBreadcrumbs} />
```

## Custom Separator

You can customize the separator between breadcrumb items:

```tsx
<ResponsiveBreadcrumbNav
  separator={<span className="mx-2">/</span>}
/>
```

## Responsive Behavior

The component automatically adapts to different screen sizes:
- **Desktop**: Shows full breadcrumb trail
- **Mobile**: Shows only the first and last breadcrumb to save space

## Integration Status

✅ **Integrated in:**
- Account Management Page (`/accounts`)
- Settings Page (`/settings`)

The breadcrumbs will not appear on the Dashboard page since it's the root navigation level.

## Route Mapping

The component automatically maps routes to friendly names:
- `/dashboard` → "Dashboard"
- `/accounts` → "Accounts"
- `/settings` → "Settings"
- `/connection-status` → "Connection Status"

Additional routes can be added by updating the `routeMap` object in `/frontend/src/components/ui/breadcrumb.tsx`.