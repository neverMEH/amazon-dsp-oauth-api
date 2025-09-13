import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useTokenStatus } from '@/hooks/use-token-status';
import { formatDistanceToNow } from 'date-fns';
import {
  WifiIcon,
  WifiOffIcon,
  RefreshCwIcon,
  ClockIcon,
  ShieldCheckIcon,
  ShieldOffIcon,
  AlertCircleIcon,
  CheckCircleIcon,
  TimerIcon,
  ActivityIcon,
  ZapIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ConnectionStatusProps {
  className?: string;
}

export function ConnectionStatus({ className }: ConnectionStatusProps) {
  const {
    status,
    isLoading,
    error,
    isRefreshing,
    timeUntilExpiry,
    timeUntilNextRefresh,
    refreshProgress,
    connectionStatus,
    refreshTokens,
    toggleAutoRefresh,
  } = useTokenStatus(1000);

  // Format time remaining into readable format
  const formatTimeRemaining = (seconds: number): string => {
    if (seconds <= 0) return 'Expired';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };

  // Get status color and icon
  const getStatusConfig = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          color: 'text-green-500',
          bgColor: 'bg-green-500/10',
          borderColor: 'border-green-500/20',
          icon: <WifiIcon className="h-5 w-5" />,
          pulseClass: 'animate-pulse-slow',
          badgeVariant: 'default' as const,
          statusText: 'Connected',
        };
      case 'refreshing':
        return {
          color: 'text-blue-500',
          bgColor: 'bg-blue-500/10',
          borderColor: 'border-blue-500/20',
          icon: <RefreshCwIcon className="h-5 w-5 animate-spin" />,
          pulseClass: '',
          badgeVariant: 'secondary' as const,
          statusText: 'Refreshing',
        };
      case 'error':
        return {
          color: 'text-red-500',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/20',
          icon: <WifiOffIcon className="h-5 w-5" />,
          pulseClass: '',
          badgeVariant: 'destructive' as const,
          statusText: 'Error',
        };
      default:
        return {
          color: 'text-gray-500',
          bgColor: 'bg-gray-500/10',
          borderColor: 'border-gray-500/20',
          icon: <WifiOffIcon className="h-5 w-5" />,
          pulseClass: '',
          badgeVariant: 'outline' as const,
          statusText: 'Disconnected',
        };
    }
  };

  const statusConfig = getStatusConfig();

  // Loading state
  if (isLoading) {
    return (
      <Card className={cn('w-full', className)}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <Skeleton className="h-10 w-24" />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('w-full transition-all duration-300', className, statusConfig.borderColor, 'border-2')}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              <div className={cn('relative', statusConfig.pulseClass)}>
                <div className={cn('absolute inset-0 rounded-full', statusConfig.bgColor, 'blur-md')} />
                <div className={cn('relative', statusConfig.color)}>{statusConfig.icon}</div>
              </div>
              Amazon DSP Connection
            </CardTitle>
            <CardDescription className="flex items-center gap-2">
              <Badge variant={statusConfig.badgeVariant} className="gap-1">
                {connectionStatus === 'connected' && <CheckCircleIcon className="h-3 w-3" />}
                {connectionStatus === 'error' && <AlertCircleIcon className="h-3 w-3" />}
                {statusConfig.statusText}
              </Badge>
              {status?.lastRefreshTime && (
                <span className="text-xs text-muted-foreground">
                  Last refresh {formatDistanceToNow(new Date(status.lastRefreshTime), { addSuffix: true })}
                </span>
              )}
            </CardDescription>
          </div>
          <Button
            onClick={refreshTokens}
            disabled={isRefreshing || !status?.isConnected}
            size="sm"
            variant={connectionStatus === 'connected' ? 'outline' : 'default'}
            className="gap-2"
          >
            <RefreshCwIcon className={cn('h-4 w-4', isRefreshing && 'animate-spin')} />
            {isRefreshing ? 'Refreshing...' : 'Refresh Now'}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Error Alert */}
        {error && (
          <Alert variant="destructive" className="animate-in fade-in-50 slide-in-from-top-1">
            <AlertCircleIcon className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Token Expiration Status */}
        {status?.isConnected && (
          <div className="space-y-4">
            {/* Token Expiry */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <ShieldCheckIcon className="h-4 w-4" />
                  Token Expiration
                </span>
                <span className={cn(
                  'font-mono font-medium',
                  timeUntilExpiry < 300 ? 'text-red-500' : 
                  timeUntilExpiry < 1800 ? 'text-yellow-500' : 
                  'text-green-500'
                )}>
                  {formatTimeRemaining(timeUntilExpiry)}
                </span>
              </div>
              <Progress 
                value={Math.max(0, Math.min(100, (timeUntilExpiry / 3600) * 100))} 
                className={cn(
                  'h-2 transition-all duration-300',
                  timeUntilExpiry < 300 && 'animate-pulse'
                )}
              />
            </div>

            {/* Auto-Refresh Progress */}
            {status.autoRefreshEnabled && status.nextRefreshTime && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <TimerIcon className="h-4 w-4" />
                    Next Auto-Refresh
                  </span>
                  <span className="font-mono font-medium text-blue-500">
                    {formatTimeRemaining(timeUntilNextRefresh)}
                  </span>
                </div>
                <Progress 
                  value={refreshProgress} 
                  className="h-2"
                />
              </div>
            )}
          </div>
        )}

        {/* Connection Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Last Refresh Card */}
          <div className={cn(
            'rounded-lg border p-4 space-y-2 transition-all duration-300',
            statusConfig.bgColor,
            statusConfig.borderColor
          )}>
            <div className="flex items-center gap-2 text-sm font-medium">
              <ClockIcon className="h-4 w-4 text-muted-foreground" />
              Last Refresh
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.lastRefreshTime 
                ? new Date(status.lastRefreshTime).toLocaleString()
                : 'Never refreshed'}
            </p>
          </div>

          {/* Token Status Card */}
          <div className={cn(
            'rounded-lg border p-4 space-y-2 transition-all duration-300',
            status?.accessToken ? 'bg-green-500/10 border-green-500/20' : 'bg-gray-500/10 border-gray-500/20'
          )}>
            <div className="flex items-center gap-2 text-sm font-medium">
              {status?.accessToken ? (
                <>
                  <ShieldCheckIcon className="h-4 w-4 text-green-500" />
                  Token Active
                </>
              ) : (
                <>
                  <ShieldOffIcon className="h-4 w-4 text-gray-500" />
                  No Token
                </>
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {status?.accessToken 
                ? `Valid for ${formatTimeRemaining(timeUntilExpiry)}`
                : 'Authentication required'}
            </p>
          </div>
        </div>

        {/* Auto-Refresh Toggle */}
        <div className="flex items-center justify-between rounded-lg border p-4 bg-muted/50">
          <div className="space-y-0.5">
            <Label htmlFor="auto-refresh" className="flex items-center gap-2 cursor-pointer">
              <ZapIcon className="h-4 w-4 text-yellow-500" />
              Automatic Token Refresh
            </Label>
            <p className="text-xs text-muted-foreground">
              Automatically refresh tokens before they expire
            </p>
          </div>
          <Switch
            id="auto-refresh"
            checked={status?.autoRefreshEnabled ?? false}
            onCheckedChange={toggleAutoRefresh}
            disabled={!status?.isConnected}
            className="data-[state=checked]:bg-green-500"
          />
        </div>

        {/* Status Timeline */}
        {status?.isConnected && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <ActivityIcon className="h-4 w-4" />
              Connection Timeline
            </div>
            <div className="relative pl-6 space-y-2">
              <div className="absolute left-2 top-2 bottom-2 w-0.5 bg-border" />
              
              {/* Connected */}
              <div className="relative flex items-center gap-2">
                <div className="absolute -left-4 h-2 w-2 rounded-full bg-green-500" />
                <span className="text-xs text-muted-foreground">Connected</span>
                <Badge variant="outline" className="text-xs">Active</Badge>
              </div>

              {/* Last Refresh */}
              {status.lastRefreshTime && (
                <div className="relative flex items-center gap-2">
                  <div className="absolute -left-4 h-2 w-2 rounded-full bg-blue-500" />
                  <span className="text-xs text-muted-foreground">
                    Last refresh {formatDistanceToNow(new Date(status.lastRefreshTime), { addSuffix: true })}
                  </span>
                </div>
              )}

              {/* Next Refresh */}
              {status.autoRefreshEnabled && status.nextRefreshTime && (
                <div className="relative flex items-center gap-2">
                  <div className="absolute -left-4 h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
                  <span className="text-xs text-muted-foreground">
                    Next refresh in {formatTimeRemaining(timeUntilNextRefresh)}
                  </span>
                </div>
              )}

              {/* Token Expiry */}
              <div className="relative flex items-center gap-2">
                <div className="absolute -left-4 h-2 w-2 rounded-full bg-orange-500" />
                <span className="text-xs text-muted-foreground">
                  Token expires in {formatTimeRemaining(timeUntilExpiry)}
                </span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}