import {
  Account,
  AccountsListResponse,
  AccountDetailsResponse,
  AccountHealthResponse,
  DisconnectAccountResponse,
  ReauthorizeResponse,
  SettingsResponse,
  UpdateSettingsRequest,
} from '@/types/account';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to get Clerk session token
async function getClerkToken() {
  // @ts-ignore - Clerk is available globally
  const clerk = window.Clerk;
  if (!clerk) {
    console.warn('Clerk not initialized');
    return null;
  }
  
  try {
    const token = await clerk.session?.getToken();
    return token;
  } catch (error) {
    console.error('Failed to get Clerk token:', error);
    return null;
  }
}

class AccountService {
  private async fetchWithAuth(url: string, options?: RequestInit) {
    // Get auth token from Clerk
    const token = await getClerkToken();
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        ...options?.headers,
      },
      credentials: 'include',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // List all accounts
  async getAccounts(): Promise<AccountsListResponse> {
    return this.fetchWithAuth('/api/v1/accounts');
  }

  // Get account details
  async getAccountDetails(accountId: string): Promise<AccountDetailsResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}`);
  }

  // Disconnect account
  async disconnectAccount(accountId: string): Promise<DisconnectAccountResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/disconnect`, {
      method: 'DELETE',
    });
  }

  // Get health status for all accounts
  async getAccountsHealth(): Promise<AccountHealthResponse> {
    return this.fetchWithAuth('/api/v1/accounts/health');
  }

  // Re-authorize account
  async reauthorizeAccount(accountId: string): Promise<ReauthorizeResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/reauthorize`, {
      method: 'POST',
    });
  }

  // Get user settings
  async getSettings(): Promise<SettingsResponse> {
    return this.fetchWithAuth('/api/v1/settings');
  }

  // Update user settings
  async updateSettings(settings: UpdateSettingsRequest): Promise<SettingsResponse> {
    return this.fetchWithAuth('/api/v1/settings', {
      method: 'PATCH',
      body: JSON.stringify(settings),
    });
  }

  // Refresh account token
  async refreshAccountToken(accountId: string): Promise<Account> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/refresh`, {
      method: 'POST',
    });
  }

  // Check if token needs refresh (client-side calculation)
  isTokenExpiringSoon(expiresAt: string | null): boolean {
    if (!expiresAt) return true;
    
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const hoursUntilExpiry = (expiryDate.getTime() - now.getTime()) / (1000 * 60 * 60);
    
    return hoursUntilExpiry < 24; // Warning if less than 24 hours
  }

  // Check if token is expired
  isTokenExpired(expiresAt: string | null): boolean {
    if (!expiresAt) return true;
    
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    
    return expiryDate <= now;
  }

  // Get status based on token expiry
  getAccountStatus(expiresAt: string | null): 'healthy' | 'warning' | 'expired' | 'disconnected' {
    if (!expiresAt) return 'disconnected';
    if (this.isTokenExpired(expiresAt)) return 'expired';
    if (this.isTokenExpiringSoon(expiresAt)) return 'warning';
    return 'healthy';
  }

  // Format time remaining until expiry
  getTimeUntilExpiry(expiresAt: string | null): string {
    if (!expiresAt) return 'N/A';
    
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const diff = expiryDate.getTime() - now.getTime();
    
    if (diff <= 0) return 'Expired';
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  // Sync accounts from Amazon Ads API
  async syncAmazonAccounts(): Promise<any> {
    return this.fetchWithAuth('/api/v1/accounts/amazon-ads-accounts');
  }
}

export const accountService = new AccountService();