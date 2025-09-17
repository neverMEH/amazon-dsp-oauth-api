import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock import.meta.env
vi.stubGlobal('import', {
  meta: {
    env: {
      VITE_API_URL: ''
    }
  }
});

// Mock fetch globally
global.fetch = vi.fn();

// Mock Clerk
global.window = {
  ...global.window,
  Clerk: {
    session: {
      getToken: vi.fn(),
    },
  },
} as any;

// Import after mocking
import { accountService } from './accountService';

describe('AccountService', () => {
  const mockApiUrl = '';
  const mockToken = 'mock-clerk-token';

  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default mock for Clerk token
    (window.Clerk.session.getToken as any).mockResolvedValue(mockToken);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('addSponsoredAdsAccounts', () => {
    it('should return OAuth URL when no tokens exist', async () => {
      const mockResponse = {
        requires_auth: true,
        auth_url: 'https://www.amazon.com/ap/oa?client_id=test',
        state: 'unique_state_token'
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await accountService.addSponsoredAdsAccounts();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/accounts/sponsored-ads/add',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.requires_auth).toBe(true);
      expect(result.auth_url).toBeDefined();
    });

    it('should return added accounts when tokens exist', async () => {
      const mockResponse = {
        requires_auth: false,
        accounts_added: 3,
        accounts: [
          {
            id: 'uuid-1',
            account_name: 'Test Account 1',
            amazon_account_id: 'ENTITY123',
            account_type: 'advertising',
            status: 'active',
            connected_at: '2025-01-17T10:00:00Z',
            metadata: {
              alternateIds: [
                {
                  countryCode: 'US',
                  entityId: 'ENTITY123',
                  profileId: 123456
                }
              ],
              countryCodes: ['US']
            }
          }
        ]
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await accountService.addSponsoredAdsAccounts();

      expect(result).toEqual(mockResponse);
      expect(result.requires_auth).toBe(false);
      expect(result.accounts_added).toBe(3);
      expect(result.accounts).toHaveLength(1);
    });

    it('should handle API errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      });

      await expect(accountService.addSponsoredAdsAccounts()).rejects.toThrow(
        'API request failed: Internal Server Error'
      );
    });

    it('should handle missing authentication token', async () => {
      (window.Clerk.session.getToken as any).mockResolvedValueOnce(null);

      await expect(accountService.addSponsoredAdsAccounts()).rejects.toThrow(
        'No authentication token available'
      );
    });
  });

  describe('addDSPAdvertisers', () => {
    it('should return OAuth URL when no tokens or missing DSP scope', async () => {
      const mockResponse = {
        requires_auth: true,
        auth_url: 'https://www.amazon.com/ap/oa?client_id=test',
        state: 'unique_state_token',
        reason: 'missing_dsp_scope'
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await accountService.addDSPAdvertisers();

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/accounts/dsp/add',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.requires_auth).toBe(true);
      expect(result.reason).toBe('missing_dsp_scope');
    });

    it('should return added DSP advertisers when tokens exist', async () => {
      const mockResponse = {
        requires_auth: false,
        advertisers_added: 2,
        advertisers: [
          {
            id: 'uuid-1',
            account_name: 'DSP Advertiser 1',
            amazon_account_id: 'AD123456',
            account_type: 'dsp',
            status: 'active',
            connected_at: '2025-01-17T10:00:00Z',
            metadata: {
              countryCode: 'US',
              currencyCode: 'USD',
              timeZone: 'America/Los_Angeles',
              type: 'AMAZON_ATTRIBUTION'
            }
          }
        ]
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await accountService.addDSPAdvertisers();

      expect(result).toEqual(mockResponse);
      expect(result.requires_auth).toBe(false);
      expect(result.advertisers_added).toBe(2);
      expect(result.advertisers).toHaveLength(1);
      expect(result.advertisers[0].account_type).toBe('dsp');
    });

    it('should handle token expired error', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      });

      await expect(accountService.addDSPAdvertisers()).rejects.toThrow(
        'API request failed: Forbidden'
      );
    });

    it('should handle server errors', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(accountService.addDSPAdvertisers()).rejects.toThrow(
        'API request failed: Internal Server Error'
      );
    });
  });

  describe('handleOAuthRedirect', () => {
    it('should handle OAuth redirect by opening new window', () => {
      const mockOpen = vi.fn();
      global.window.open = mockOpen;

      const authUrl = 'https://www.amazon.com/ap/oa?client_id=test';
      accountService.handleOAuthRedirect(authUrl);

      expect(mockOpen).toHaveBeenCalledWith(
        authUrl,
        '_blank',
        'width=500,height=600'
      );
    });

    it('should handle OAuth redirect with callback', async () => {
      const mockCallback = vi.fn();
      const authUrl = 'https://www.amazon.com/ap/oa?client_id=test';

      // Mock window.open and message event
      const mockWindow = {
        closed: false,
        close: vi.fn(),
      };
      global.window.open = vi.fn().mockReturnValue(mockWindow);

      // Start OAuth redirect
      accountService.handleOAuthRedirect(authUrl, mockCallback);

      // Simulate successful OAuth callback
      const messageEvent = new MessageEvent('message', {
        data: { type: 'oauth-success', code: 'auth-code-123' },
        origin: window.location.origin,
      });
      window.dispatchEvent(messageEvent);

      // Wait for callback to be called
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockCallback).toHaveBeenCalledWith({
        success: true,
        code: 'auth-code-123'
      });
      expect(mockWindow.close).toHaveBeenCalled();
    });

    it('should handle OAuth redirect error', async () => {
      const mockCallback = vi.fn();
      const authUrl = 'https://www.amazon.com/ap/oa?client_id=test';

      const mockWindow = {
        closed: false,
        close: vi.fn(),
      };
      global.window.open = vi.fn().mockReturnValue(mockWindow);

      accountService.handleOAuthRedirect(authUrl, mockCallback);

      // Simulate OAuth error
      const messageEvent = new MessageEvent('message', {
        data: { type: 'oauth-error', error: 'access_denied' },
        origin: window.location.origin,
      });
      window.dispatchEvent(messageEvent);

      await new Promise(resolve => setTimeout(resolve, 100));

      expect(mockCallback).toHaveBeenCalledWith({
        success: false,
        error: 'access_denied'
      });
      expect(mockWindow.close).toHaveBeenCalled();
    });
  });

  describe('deleteAccount', () => {
    it('should successfully delete an account', async () => {
      const accountId = 'test-account-id';
      const mockResponse = {
        success: true,
        message: 'Account successfully deleted'
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await accountService.deleteAccount(accountId);

      expect(global.fetch).toHaveBeenCalledWith(
        `/api/v1/accounts/${accountId}`,
        expect.objectContaining({
          method: 'DELETE',
          headers: expect.objectContaining({
            'Authorization': `Bearer ${mockToken}`,
            'Content-Type': 'application/json',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
      expect(result.success).toBe(true);
    });

    it('should handle account not found error', async () => {
      const accountId = 'non-existent-id';

      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      await expect(accountService.deleteAccount(accountId)).rejects.toThrow(
        'API request failed: Not Found'
      );
    });

    it('should handle forbidden error when deleting other users account', async () => {
      const accountId = 'other-user-account';

      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
      });

      await expect(accountService.deleteAccount(accountId)).rejects.toThrow(
        'API request failed: Forbidden'
      );
    });
  });
});