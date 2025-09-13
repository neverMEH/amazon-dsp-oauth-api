import { useState, useEffect, useCallback, useRef } from 'react';
import { TokenStatus, AuthStatusResponse, RefreshResponse } from '@/types/auth';
import { toast } from '@/components/ui/use-toast';

export interface UseTokenStatusReturn {
  status: TokenStatus | null;
  isLoading: boolean;
  error: string | null;
  isRefreshing: boolean;
  timeUntilExpiry: number;
  timeUntilNextRefresh: number;
  refreshProgress: number;
  connectionStatus: 'connected' | 'disconnected' | 'refreshing' | 'error';
  refreshTokens: () => Promise<void>;
  toggleAutoRefresh: () => Promise<void>;
  refetch: () => Promise<void>;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

export function useTokenStatus(pollInterval: number = 1000): UseTokenStatusReturn {
  const [status, setStatus] = useState<TokenStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [timeUntilExpiry, setTimeUntilExpiry] = useState(0);
  const [timeUntilNextRefresh, setTimeUntilNextRefresh] = useState(0);
  const [refreshProgress, setRefreshProgress] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'refreshing' | 'error'>('disconnected');
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate time differences
  const calculateTimeRemaining = useCallback(() => {
    if (!status) return;

    const now = Date.now();

    // Calculate time until token expiry
    if (status.expiresAt) {
      const expiryTime = new Date(status.expiresAt).getTime();
      const remaining = Math.max(0, Math.floor((expiryTime - now) / 1000));
      setTimeUntilExpiry(remaining);
    }

    // Calculate time until next refresh
    if (status.nextRefreshTime) {
      const nextRefreshTime = new Date(status.nextRefreshTime).getTime();
      const refreshRemaining = Math.max(0, Math.floor((nextRefreshTime - now) / 1000));
      setTimeUntilNextRefresh(refreshRemaining);

      // Calculate refresh progress (for progress bar)
      if (status.lastRefreshTime && status.nextRefreshTime) {
        const lastRefresh = new Date(status.lastRefreshTime).getTime();
        const nextRefresh = new Date(status.nextRefreshTime).getTime();
        const totalDuration = nextRefresh - lastRefresh;
        const elapsed = now - lastRefresh;
        const progress = Math.min(100, Math.max(0, (elapsed / totalDuration) * 100));
        setRefreshProgress(progress);
      }
    }
  }, [status]);

  // Fetch token status from API
  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/status`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch status: ${response.statusText}`);
      }

      const data: AuthStatusResponse = await response.json();
      setStatus(data.tokenStatus);
      setConnectionStatus(data.status);
      setError(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch token status';
      setError(errorMessage);
      setConnectionStatus('error');
      console.error('Error fetching token status:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Refresh tokens manually
  const refreshTokens = useCallback(async () => {
    if (isRefreshing) return;

    setIsRefreshing(true);
    setConnectionStatus('refreshing');

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to refresh tokens: ${response.statusText}`);
      }

      const data: RefreshResponse = await response.json();

      if (data.success && data.tokenStatus) {
        setStatus(data.tokenStatus);
        setConnectionStatus('connected');
        toast({
          title: 'Tokens Refreshed',
          description: 'Your authentication tokens have been successfully refreshed.',
          variant: 'default',
        });
      } else {
        throw new Error(data.message || 'Failed to refresh tokens');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to refresh tokens';
      setError(errorMessage);
      setConnectionStatus('error');
      toast({
        title: 'Refresh Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsRefreshing(false);
      // Refetch status after refresh attempt
      await fetchStatus();
    }
  }, [isRefreshing, fetchStatus]);

  // Toggle auto-refresh setting
  const toggleAutoRefresh = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/auto-refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled: status ? !status.autoRefreshEnabled : true,
        }),
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`Failed to toggle auto-refresh: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.success) {
        await fetchStatus();
        toast({
          title: 'Auto-Refresh Updated',
          description: `Auto-refresh has been ${data.enabled ? 'enabled' : 'disabled'}.`,
          variant: 'default',
        });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to toggle auto-refresh';
      toast({
        title: 'Update Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    }
  }, [status, fetchStatus]);

  // Set up auto-refresh based on nextRefreshTime
  useEffect(() => {
    if (status?.autoRefreshEnabled && status.nextRefreshTime && !isRefreshing) {
      const nextRefreshTime = new Date(status.nextRefreshTime).getTime();
      const now = Date.now();
      const timeUntilRefresh = nextRefreshTime - now;

      if (timeUntilRefresh > 0) {
        // Clear existing timeout
        if (refreshTimeoutRef.current) {
          clearTimeout(refreshTimeoutRef.current);
        }

        // Set new timeout for auto-refresh
        refreshTimeoutRef.current = setTimeout(() => {
          refreshTokens();
        }, timeUntilRefresh);
      } else if (timeUntilRefresh <= 0 && status.isConnected) {
        // If we're past the refresh time, refresh immediately
        refreshTokens();
      }
    }

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [status?.nextRefreshTime, status?.autoRefreshEnabled, status?.isConnected, isRefreshing, refreshTokens]);

  // Initial fetch and polling setup
  useEffect(() => {
    fetchStatus();

    // Set up polling interval for real-time updates
    intervalRef.current = setInterval(() => {
      calculateTimeRemaining();
    }, pollInterval);

    // Fetch status every 30 seconds
    const fetchInterval = setInterval(() => {
      if (!isRefreshing) {
        fetchStatus();
      }
    }, 30000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      clearInterval(fetchInterval);
    };
  }, [fetchStatus, calculateTimeRemaining, pollInterval, isRefreshing]);

  return {
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
    refetch: fetchStatus,
  };
}