// Authentication and token status types
export interface TokenStatus {
  isConnected: boolean;
  lastRefreshTime: string | null;
  nextRefreshTime: string | null;
  expiresAt: string | null;
  autoRefreshEnabled: boolean;
  refreshToken: string | null;
  accessToken: string | null;
  error?: string;
}

export interface AuthStatusResponse {
  status: 'connected' | 'disconnected' | 'refreshing' | 'error';
  tokenStatus: TokenStatus;
  message?: string;
}

export interface RefreshResponse {
  success: boolean;
  message: string;
  tokenStatus?: TokenStatus;
}