import {
  Account,
  AccountStatus,
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
    try {
      // Try the new unified endpoint first
      const response = await this.fetchWithAuth('/api/v1/accounts/all-account-types');
      return this.mapAccountsResponse(response);
    } catch (error) {
      console.warn('New endpoint failed, falling back to legacy endpoint:', error);
      // Fall back to legacy endpoint
      const response = await this.fetchWithAuth('/api/v1/accounts');
      return this.mapAccountsResponse(response);
    }
  }

  // Get Sponsored Ads accounts
  async getSponsoredAdsAccounts(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/api/v1/accounts/sponsored-ads');
      return {
        accounts: response.accounts || [],
        totalCount: response.total_count || response.accounts?.length || 0,
      };
    } catch (error) {
      console.error('Failed to fetch Sponsored Ads accounts:', error);
      throw error;
    }
  }

  // Get DSP accounts
  async getDSPAccounts(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/api/v1/accounts/dsp');
      return {
        accounts: response.accounts || [],
        totalCount: response.total_count || response.accounts?.length || 0,
      };
    } catch (error: any) {
      // Pass through 403 errors with proper structure
      if (error.message?.includes('403') || error.response?.status === 403) {
        throw { response: { status: 403 }, message: 'Access denied' };
      }
      throw error;
    }
  }

  // Get AMC accounts
  async getAMCAccounts(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/api/v1/accounts/amc');
      return {
        instances: response.instances || [],
        totalCount: response.total_count || response.instances?.length || 0,
      };
    } catch (error: any) {
      // Pass through 403 errors with proper structure
      if (error.message?.includes('403') || error.response?.status === 403) {
        throw { response: { status: 403 }, message: 'Access denied' };
      }
      throw error;
    }
  }

  // Helper method to map backend response to frontend format
  private mapAccountsResponse(response: any): AccountsResponse {
    // Map backend response to frontend format
    const mappedAccounts = response.accounts?.map((acc: any) => ({
      id: acc.id,
      accountName: acc.account_name || acc.accountName || 'Unknown Account',
      accountId: acc.amazon_account_id || acc.accountId || acc.id,
      accountType: acc.account_type || acc.accountType || 'advertising',
      marketplaceId: acc.marketplace_id || acc.marketplaceId,
      marketplaceName: acc.marketplace_name || acc.marketplaceName,
      marketplace: acc.marketplace || (acc.marketplace_id ? {
        id: acc.marketplace_id,
        name: acc.marketplace_name || 'Unknown',
        countryCode: acc.metadata?.country_code || 'N/A',
        region: acc.metadata?.region || 'Unknown'
      } : undefined),
      status: acc.status || 'disconnected',
      tokenExpiresAt: acc.token_expires_at || acc.tokenExpiresAt || null,
      lastRefreshTime: acc.last_synced_at || acc.lastRefreshTime || null,
      createdAt: acc.connected_at || acc.createdAt || acc.created_at,
      updatedAt: acc.updated_at || acc.updatedAt || acc.last_synced_at,
      isDefault: acc.is_default || acc.isDefault || false,
      metadata: acc.metadata || {}
    })) || [];

    return {
      accounts: mappedAccounts,
      total: response.total || mappedAccounts.length
    };
  }

  // Get account details
  async getAccountDetails(accountId: string): Promise<Account> {
    return this.fetchWithAuth(`/api/v1/accounts/${accountId}`);
  }

  // Get account status (helper method)
  getAccountStatus(account: Account): AccountStatus {
    // Check if account already has a valid status
    if (account.status === 'active' || account.status === 'error' || account.status === 'disconnected') {
      return account.status;
    }

    // For accounts from database, assume active if they exist
    // The backend manages the actual token refresh
    if (account.id && (account.amazon_account_id || account.accountId)) {
      // If account has an explicit status field set, use it
      if (account.status === 'inactive' || account.status === 'suspended') {
        return 'disconnected';
      }
      // Default to active for connected accounts
      return 'active';
    }

    // Legacy logic for backwards compatibility
    // If no token, account is disconnected
    if (!account.tokenExpiresAt) return 'disconnected';

    // If account has refresh failures or is marked with error status
    if (account.status === 'error' || account.metadata?.refresh_failures > 2) {
      return 'error';
    }

    // If account has valid token (even if expiring soon), it's active
    // Auto-refresh will handle token renewal
    const now = new Date();
    const expiresAt = new Date(account.tokenExpiresAt);

    // Only mark as disconnected if token is already expired AND auto-refresh failed
    if (expiresAt < now && account.metadata?.last_refresh_error) {
      return 'error';
    }

    // Account is active and being managed
    return 'active';
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
      body: JSON.stringify({ force_refresh: false }),
    });
  }

  // Get user settings
  async getSettings(): Promise<SettingsResponse> {
    try {
      const response = await this.fetchWithAuth('/api/v1/settings');

      // Log the response for debugging
      console.log('Settings API response:', response);
      console.log('Type of preferences:', typeof response.preferences);
      console.log('Preferences content:', response.preferences);

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
      const transformedSettings = {
        settings: {
          autoRefreshTokens: preferences.auto_refresh_tokens !== undefined
            ? preferences.auto_refresh_tokens
            : true,
          defaultAccountId: preferences.default_account_id !== undefined
            ? preferences.default_account_id
            : null,
          notificationPreferences: {
            emailOnTokenExpiry: preferences.email_notifications !== undefined
              ? preferences.email_notifications
              : true,
            emailOnTokenRefresh: preferences.email_notifications !== undefined
              ? preferences.email_notifications
              : true,
            emailOnConnectionIssue: preferences.email_notifications !== undefined
              ? preferences.email_notifications
              : true,
          },
          dashboardLayout: (preferences.dashboard_layout || 'grid') as 'grid' | 'list',
        }
      };

      console.log('Transformed settings:', transformedSettings);
      console.log('Settings object:', transformedSettings.settings);

      return transformedSettings;
    } catch (error) {
      console.error('Error in getSettings:', error);
      // Return default settings on any error
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
    // Use reauthorize endpoint with non-force refresh
    const response = await this.fetchWithAuth(`/api/v1/accounts/${accountId}/reauthorize`, {
      method: 'POST',
      body: JSON.stringify({ force_refresh: true }),
    });

    // Return the account data after refresh
    return this.getAccountDetails(accountId);
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

  // NOTE: Sync methods have been removed per spec requirements.
  // Use addSponsoredAdsAccounts() and addDSPAdvertisers() instead.

  // Add Sponsored Ads accounts using existing tokens or initiate OAuth
  async addSponsoredAdsAccounts(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/api/v1/accounts/sponsored-ads/add', {
        method: 'POST',
      });

      // Check if OAuth is required
      if (response.requires_auth && response.auth_url) {
        // Return the response so the UI can handle OAuth redirect
        return response;
      }

      return response;
    } catch (error: any) {
      console.error('Failed to add Sponsored Ads accounts:', error);

      // Enhanced error handling for specific OAuth scenarios
      if (error.message?.includes('401')) {
        throw new Error('Authentication required. Please sign in again.');
      }
      if (error.message?.includes('403')) {
        throw new Error('Token expired. OAuth re-authorization required.');
      }
      if (error.message?.includes('500')) {
        throw new Error('Failed to fetch accounts from Amazon. Please try again.');
      }

      throw error;
    }
  }

  // Add DSP advertisers using existing tokens or initiate OAuth
  async addDSPAdvertisers(): Promise<any> {
    try {
      const response = await this.fetchWithAuth('/api/v1/accounts/dsp/add', {
        method: 'POST',
      });

      // Check if OAuth is required
      if (response.requires_auth && response.auth_url) {
        // Return the response so the UI can handle OAuth redirect
        // The reason field indicates why OAuth is needed (e.g., 'missing_dsp_scope')
        return response;
      }

      return response;
    } catch (error: any) {
      console.error('Failed to add DSP advertisers:', error);

      // Enhanced error handling for specific OAuth scenarios
      if (error.message?.includes('401')) {
        throw new Error('Authentication required. Please sign in again.');
      }
      if (error.message?.includes('403')) {
        // Check if it's specifically a missing DSP scope issue
        if (error.message?.includes('missing_dsp_scope') || error.message?.includes('scope')) {
          throw new Error('DSP scope missing. Please re-authorize with DSP permissions.');
        }
        throw new Error('Token expired or insufficient permissions. OAuth re-authorization required.');
      }
      if (error.message?.includes('500')) {
        throw new Error('Failed to fetch DSP advertisers from Amazon. Please try again.');
      }

      throw error;
    }
  }

  // Delete an account from local database
  async deleteAccount(accountId: string): Promise<any> {
    try {
      const response = await this.fetchWithAuth(`/api/v1/accounts/${accountId}`, {
        method: 'DELETE',
      });
      return response;
    } catch (error) {
      console.error('Failed to delete account:', error);
      throw error;
    }
  }

  // Handle OAuth redirect by opening auth URL in new window
  handleOAuthRedirect(authUrl: string, callback?: (result: any) => void): void {
    // Open OAuth URL in popup window
    const authWindow = window.open(
      authUrl,
      '_blank',
      'width=500,height=600'
    );

    if (callback && authWindow) {
      // Listen for OAuth callback message
      const messageListener = (event: MessageEvent) => {
        // Verify origin for security
        if (event.origin !== window.location.origin) return;

        if (event.data.type === 'oauth-success') {
          callback({ success: true, code: event.data.code });
          authWindow.close();
          window.removeEventListener('message', messageListener);
        } else if (event.data.type === 'oauth-error') {
          callback({ success: false, error: event.data.error });
          authWindow.close();
          window.removeEventListener('message', messageListener);
        }
      };

      window.addEventListener('message', messageListener);

      // Check if window was closed manually
      const checkClosed = setInterval(() => {
        if (authWindow.closed) {
          clearInterval(checkClosed);
          window.removeEventListener('message', messageListener);
          callback({ success: false, error: 'Window closed by user' });
        }
      }, 1000);
    }
  }
}

export const accountService = new AccountService();