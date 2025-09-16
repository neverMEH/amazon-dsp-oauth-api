export interface DSPSeatInfo {
  exchangeId: string;
  exchangeName: string;
  dealCreationId?: string | null;
  spendTrackingId?: string | null;
}

export interface AdvertiserSeat {
  advertiserId: string;
  currentSeats: DSPSeatInfo[];
}

export interface DSPSeatsResponse {
  advertiserSeats: AdvertiserSeat[];
  nextToken: string | null;
  timestamp: string;
  cached: boolean;
}

export interface DSPSeatsQueryParams {
  maxResults?: number;
  nextToken?: string;
  exchangeIds?: string[];
}

export interface RefreshSeatsParams {
  force?: boolean;
  include_sync_log?: boolean;
}

export interface RefreshSeatsResponse {
  success: boolean;
  seats_updated: number;
  last_sync: string;
  sync_log_id?: string;
}

export interface SyncHistoryEntry {
  id: string;
  advertiser_id: string;
  sync_status: 'pending' | 'success' | 'failed' | 'partial';
  seats_found: number;
  seats_updated: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
  metadata?: Record<string, any>;
}

export interface SyncHistoryResponse {
  history: SyncHistoryEntry[];
  total: number;
}

class DSPSeatsService {
  private baseUrl = import.meta.env.VITE_API_URL || '';

  // Helper function to get auth token from Clerk
  private async getAuthToken(): Promise<string | null> {
    // @ts-ignore - Clerk is available globally
    const clerk = window.Clerk;
    if (!clerk || !clerk.session) {
      console.warn('Clerk not initialized or no active session');
      return null;
    }

    try {
      const token = await clerk.session.getToken();
      return token;
    } catch (error) {
      console.error('Failed to get Clerk token:', error);
      return null;
    }
  }

  // Helper for authenticated requests
  private async fetchWithAuth(url: string, options: RequestInit = {}): Promise<any> {
    const token = await this.getAuthToken();
    if (!token) {
      throw new Error('No authentication token available');
    }

    const fullUrl = `${this.baseUrl}${url}`;
    const response = await fetch(fullUrl, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Request failed: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Fetch advertiser seats for a given advertiser ID
   */
  async fetchAdvertiserSeats(
    advertiserId: string,
    params?: DSPSeatsQueryParams
  ): Promise<DSPSeatsResponse> {
    try {
      console.log('DSPSeatsService.fetchAdvertiserSeats called with:', { advertiserId, params });

      const queryParams = new URLSearchParams();

      if (params?.maxResults) {
        queryParams.append('max_results', params.maxResults.toString());
      }

      if (params?.nextToken) {
        queryParams.append('next_token', params.nextToken);
      }

      if (params?.exchangeIds && params.exchangeIds.length > 0) {
        params.exchangeIds.forEach(id => {
          queryParams.append('exchange_ids', id);
        });
      }

      const url = `/api/v1/accounts/dsp/${advertiserId}/seats${
        queryParams.toString() ? `?${queryParams.toString()}` : ''
      }`;

      console.log('DSPSeatsService making API call to:', url);

      const result = await this.fetchWithAuth(url);
      console.log('DSPSeatsService API response:', result);

      return result;
    } catch (error) {
      console.error('Error fetching advertiser seats:', error);
      throw error;
    }
  }

  /**
   * Refresh advertiser seats from Amazon DSP API
   */
  async refreshAdvertiserSeats(
    advertiserId: string,
    params?: RefreshSeatsParams
  ): Promise<RefreshSeatsResponse> {
    try {
      return await this.fetchWithAuth(
        `/api/v1/accounts/dsp/${advertiserId}/seats/refresh`,
        {
          method: 'POST',
          body: JSON.stringify(params || {}),
        }
      );
    } catch (error) {
      console.error('Error refreshing advertiser seats:', error);
      throw error;
    }
  }

  /**
   * Fetch sync history for advertiser seats
   */
  async fetchSyncHistory(
    advertiserId: string,
    limit: number = 10,
    offset: number = 0
  ): Promise<SyncHistoryResponse> {
    try {
      const queryParams = new URLSearchParams({
        limit: limit.toString(),
        offset: offset.toString(),
      });

      return await this.fetchWithAuth(
        `/api/v1/accounts/dsp/${advertiserId}/seats/sync-history?${queryParams.toString()}`
      );
    } catch (error) {
      console.error('Error fetching sync history:', error);
      throw error;
    }
  }
}

// Create and export a singleton instance
export const dspSeatsService = new DSPSeatsService();

// Cache management utilities
const seatsCache = new Map<string, { data: DSPSeatsResponse; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

/**
 * Get cached seats data if available and not expired
 */
export function getCachedSeats(advertiserId: string): DSPSeatsResponse | null {
  const cached = seatsCache.get(advertiserId);

  if (!cached) {
    return null;
  }

  const now = Date.now();
  if (now - cached.timestamp > CACHE_TTL) {
    seatsCache.delete(advertiserId);
    return null;
  }

  return cached.data;
}

/**
 * Cache seats data
 */
export function cacheSeats(advertiserId: string, data: DSPSeatsResponse): void {
  seatsCache.set(advertiserId, {
    data,
    timestamp: Date.now(),
  });
}

/**
 * Clear cached seats for a specific advertiser
 */
export function clearSeatsCache(advertiserId: string): void {
  seatsCache.delete(advertiserId);
}

/**
 * Clear all cached seats data
 */
export function clearAllSeatsCache(): void {
  seatsCache.clear();
}