import {
  Account,
  AccountsResponse,
  DisconnectAccountResponse,
  ReauthorizeResponse,
  AccountHealth,
  AccountHealthResponse,
  RefreshHistory,
  RefreshHistoryResponse,
  AccountSettings,
  SettingsResponse,
  UpdateSettingsRequest
} from '@/types/account';

class AccountService {
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
      console.log('Got Clerk token:', token ? 'Token present' : 'No token');
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

    const response = await fetch(`${this.baseUrl}${url}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  // Get all accounts
  async getAccounts(): Promise<AccountsResponse> {
    return this.fetchWithAuth('/api/v1/accounts');
  }

  // Get account health status
  async getAccountHealth(): Promise<AccountHealthResponse> {
    return this.fetchWithAuth('/api/v1/accounts/health');
  }

  // Get refresh history for an account
  async getRefreshHistory(accountId: string): Promise<RefreshHistoryResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/refresh-history`);
  }

  // Disconnect an account
  async disconnectAccount(accountId: string): Promise<DisconnectAccountResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/disconnect`, {
      method: 'POST',
    });
  }

  // Reauthorize an account
  async reauthorizeAccount(accountId: string): Promise<ReauthorizeResponse> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/reauthorize`, {
      method: 'POST',
    });
  }

  // Get user settings
  async getSettings(): Promise<SettingsResponse> {
    const response = await this.fetchWithAuth('/api/v1/settings');

    // Log the response for debugging
    console.log('Settings API response:', response);
    console.log('Type of preferences:', typeof response.preferences);

    // If preferences is a string, parse it
    let preferences = response.preferences;
    if (typeof preferences === 'string') {
      try {
        preferences = JSON.parse(preferences);
        console.log('Parsed preferences from string:', preferences);
      } catch (e) {
        console.error('Failed to parse preferences string:', e);
        preferences = {};
      }
    }

    // Handle case where response might not have preferences
    if (!response || !preferences) {
      console.warn('Invalid settings response, using defaults', response);
      return {
        settings: {
          autoRefreshTokens: true,
          defaultAccountId: null,
          notificationPreferences: {
            emailOnTokenExpiry: true,
            emailOnTokenRefresh: true,
            emailOnConnectionIssue: true,
          },
          dashboardLayout: 'grid',
        }
      };
    }

    // Transform backend response to match frontend expectations
    // Backend returns 'preferences' but frontend expects 'settings'
    return {
      settings: {
        autoRefreshTokens: preferences.auto_refresh_tokens ?? true,
        defaultAccountId: preferences.default_account_id ?? null,
        notificationPreferences: {
          emailOnTokenExpiry: preferences.email_notifications ?? true,
          emailOnTokenRefresh: preferences.email_notifications ?? true,
          emailOnConnectionIssue: preferences.email_notifications ?? true,
        },
        dashboardLayout: (preferences.dashboard_layout ?? 'grid') as 'grid' | 'list',
      }
    };
  }

  // Update user settings
  async updateSettings(settings: UpdateSettingsRequest): Promise<SettingsResponse> {
    // Transform frontend settings to backend preferences format
    // Use any email notification preference to set the general email_notifications flag
    const emailNotifications = settings.notificationPreferences?.emailOnTokenExpiry ??
                               settings.notificationPreferences?.emailOnTokenRefresh ??
                               settings.notificationPreferences?.emailOnConnectionIssue ?? true;

    const requestBody = {
      preferences: {
        auto_refresh_tokens: settings.autoRefreshTokens,
        default_account_id: settings.defaultAccountId,
        email_notifications: emailNotifications,
        notifications_enabled: true, // Always enabled for now
        dashboard_layout: settings.dashboardLayout,
      }
    };

    const response = await this.fetchWithAuth('/api/v1/settings', {
      method: 'PATCH',
      body: JSON.stringify(requestBody),
    });

    // Log the response for debugging
    console.log('Settings update response:', response);
    console.log('Type of preferences:', typeof response.preferences);

    // If preferences is a string, parse it
    let preferences = response.preferences;
    if (typeof preferences === 'string') {
      try {
        preferences = JSON.parse(preferences);
        console.log('Parsed preferences from string:', preferences);
      } catch (e) {
        console.error('Failed to parse preferences string:', e);
        preferences = {};
      }
    }

    // Handle case where response might not have preferences
    if (!response || !preferences) {
      console.warn('Invalid settings update response, using provided values', response);
      return {
        settings: {
          autoRefreshTokens: settings.autoRefreshTokens ?? true,
          defaultAccountId: settings.defaultAccountId ?? null,
          notificationPreferences: {
            emailOnTokenExpiry: emailNotifications,
            emailOnTokenRefresh: emailNotifications,
            emailOnConnectionIssue: emailNotifications,
          },
          dashboardLayout: settings.dashboardLayout ?? 'grid',
        }
      };
    }

    // Transform backend response to match frontend expectations
    return {
      settings: {
        autoRefreshTokens: preferences.auto_refresh_tokens ?? true,
        defaultAccountId: preferences.default_account_id ?? null,
        notificationPreferences: {
          emailOnTokenExpiry: preferences.email_notifications ?? true,
          emailOnTokenRefresh: preferences.email_notifications ?? true,
          emailOnConnectionIssue: preferences.email_notifications ?? true,
        },
        dashboardLayout: (preferences.dashboard_layout ?? 'grid') as 'grid' | 'list',
      }
    };
  }

  // Refresh account token
  async refreshAccountToken(accountId: string): Promise<Account> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}/refresh`, {
      method: 'POST',
    });
  }

  // Bulk refresh tokens
  async bulkRefreshTokens(accountIds: string[]): Promise<any> {
    return this.fetchWithAuth('/api/v1/accounts/bulk-refresh', {
      method: 'POST',
      body: JSON.stringify({ accountIds }),
    });
  }

  // Helper to calculate time until token expiry
  getTimeUntilExpiry(expiresAt: string): string {
    const expiry = new Date(expiresAt);
    const now = new Date();
    const diff = expiry.getTime() - now.getTime();

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