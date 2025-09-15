import React from 'react';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import { Toaster } from '@/components/ui/toaster';

export function ConnectionStatusDemo() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="amazon-dsp-theme">
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-8">
        {/* Theme Toggle */}
        <div className="fixed top-4 right-4 z-50">
          <ThemeToggle />
        </div>

        {/* Header */}
        <div className="max-w-4xl mx-auto mb-8">
          <h1 className="text-4xl font-bold mb-2">neverMEH Connection Status</h1>
          <p className="text-muted-foreground">
            Real-time monitoring and management of your OAuth token connection
          </p>
        </div>

        {/* Connection Status Component */}
        <div className="max-w-4xl mx-auto">
          <ConnectionStatus />
        </div>

        {/* Additional Information */}
        <div className="max-w-4xl mx-auto mt-8 p-6 bg-white/50 dark:bg-gray-800/50 rounded-lg backdrop-blur">
          <h2 className="text-lg font-semibold mb-4">Component Features</h2>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Real-time connection status with visual indicators</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Automatic token refresh with countdown timer</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Manual refresh capability with loading states</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Token expiration tracking with progress bars</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Auto-refresh toggle for flexible control</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Connection timeline for activity history</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Dark mode support with beautiful animations</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-green-500">✓</span>
              <span>Fully accessible with ARIA labels and keyboard navigation</span>
            </li>
          </ul>
        </div>

        {/* Toast Notifications */}
        <Toaster />
      </div>
    </ThemeProvider>
  );
}