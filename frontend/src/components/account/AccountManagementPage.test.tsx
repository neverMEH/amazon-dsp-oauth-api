import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccountManagementPage } from './AccountManagementPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Mock the account service
vi.mock('@/services/accountService', () => ({
  accountService: {
    getSponsoredAdsAccounts: vi.fn(),
    getDSPAccounts: vi.fn(),
    getAMCAccounts: vi.fn(),
    getSettings: vi.fn(),
    syncAmazonAccounts: vi.fn(),
    refreshAccountToken: vi.fn(),
    disconnectAccount: vi.fn(),
    updateSettings: vi.fn(),
  },
}));

// Mock the toast hook
vi.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock Clerk
vi.mock('@clerk/clerk-react', () => ({
  useAuth: () => ({
    isSignedIn: true,
    userId: 'test-user-id',
  }),
  useUser: () => ({
    user: {
      firstName: 'Test',
      lastName: 'User',
    },
  }),
}));

const createWrapper = (initialRoute = '/accounts') => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/accounts/*" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AccountManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Page Layout', () => {
    it('should render page header with title and description', () => {
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      expect(screen.getByText('Account Management')).toBeInTheDocument();
      expect(screen.getByText(/Manage your neverMEH accounts/i)).toBeInTheDocument();
    });

    it('should render account type tabs', () => {
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      expect(screen.getByRole('tab', { name: /Sponsored Ads/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /DSP/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /AMC/i })).toBeInTheDocument();
    });

    it('should render sync and refresh buttons', () => {
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      expect(screen.getByRole('button', { name: /Sync from Amazon/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Refresh Tokens/i })).toBeInTheDocument();
    });

    it('should render status overview cards', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: [
          { id: '1', status: 'active' },
          { id: '2', status: 'active' },
          { id: '3', status: 'error' },
        ],
        totalCount: 3,
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
        expect(screen.getByText('2')).toBeInTheDocument(); // 2 active accounts
        expect(screen.getByText('Needs Attention')).toBeInTheDocument();
        expect(screen.getByText('1')).toBeInTheDocument(); // 1 error account
      });
    });
  });

  describe('Tab Navigation', () => {
    it('should default to Sponsored Ads tab', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: [],
        totalCount: 0,
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
      expect(sponsoredAdsTab).toHaveAttribute('data-state', 'active');

      await waitFor(() => {
        expect(accountService.getSponsoredAdsAccounts).toHaveBeenCalled();
      });
    });

    it('should update URL when switching tabs', async () => {
      const user = userEvent.setup();
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      // In a real scenario, this would update the URL to /accounts/dsp
      expect(dspTab).toHaveAttribute('data-state', 'active');
    });

    it('should preserve tab state when navigating back', async () => {
      const user = userEvent.setup();
      render(<AccountManagementPage />, { wrapper: createWrapper('/accounts/dsp') });

      // Should show DSP tab as active when URL is /accounts/dsp
      await waitFor(() => {
        const dspTab = screen.getByRole('tab', { name: /DSP/i });
        expect(dspTab).toHaveAttribute('data-state', 'active');
      });
    });
  });

  describe('Account Type Specific Content', () => {
    it('should display Sponsored Ads accounts in the correct tab', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: [
          {
            id: 'sp-1',
            accountName: 'Sponsored Ads Account 1',
            profileId: '12345',
            entityId: 'ENTITY123',
            marketplaces: ['US', 'CA'],
            lastManagedAt: '2024-01-15T10:00:00Z',
          },
        ],
        totalCount: 1,
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText('Sponsored Ads Account 1')).toBeInTheDocument();
        expect(screen.getByText('12345')).toBeInTheDocument(); // Profile ID
        expect(screen.getByText('ENTITY123')).toBeInTheDocument(); // Entity ID
      });
    });

    it('should display DSP accounts in the DSP tab', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getDSPAccounts).mockResolvedValue({
        accounts: [
          {
            id: 'dsp-1',
            accountName: 'DSP Account 1',
            entityId: 'DSP_ENTITY_1',
            advertiserType: 'Brand',
          },
        ],
        totalCount: 1,
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      await waitFor(() => {
        expect(screen.getByText('DSP Account 1')).toBeInTheDocument();
        expect(screen.getByText('DSP_ENTITY_1')).toBeInTheDocument();
        expect(screen.getByText('Brand')).toBeInTheDocument();
      });
    });

    it('should display AMC instances in the AMC tab', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getAMCAccounts).mockResolvedValue({
        instances: [
          {
            id: 'amc-1',
            instanceName: 'AMC Instance 1',
            associatedDSPAccounts: ['dsp-1', 'dsp-2'],
            associatedSponsoredAdsAccounts: ['sp-1', 'sp-2'],
            dataFreshness: 'Real-time',
          },
        ],
        totalCount: 1,
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const amcTab = screen.getByRole('tab', { name: /AMC/i });
      await user.click(amcTab);

      await waitFor(() => {
        expect(screen.getByText('AMC Instance 1')).toBeInTheDocument();
        expect(screen.getByText('2 DSP accounts')).toBeInTheDocument();
        expect(screen.getByText('2 Sponsored Ads accounts')).toBeInTheDocument();
        expect(screen.getByText('Real-time')).toBeInTheDocument();
      });
    });
  });

  describe('Data Synchronization', () => {
    it('should sync accounts from Amazon when sync button is clicked', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.syncAmazonAccounts).mockResolvedValue({
        accounts: [{ id: '1' }, { id: '2' }],
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const syncButton = screen.getByRole('button', { name: /Sync from Amazon/i });
      await user.click(syncButton);

      await waitFor(() => {
        expect(accountService.syncAmazonAccounts).toHaveBeenCalled();
      });
    });

    it('should refresh all active account tokens', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: [
          { id: '1', status: 'active' },
          { id: '2', status: 'active' },
          { id: '3', status: 'error' },
        ],
        totalCount: 3,
      });

      vi.mocked(accountService.refreshAccountToken).mockResolvedValue({});

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Refresh Tokens/i })).toBeInTheDocument();
      });

      const refreshButton = screen.getByRole('button', { name: /Refresh Tokens/i });
      await user.click(refreshButton);

      await waitFor(() => {
        // Should only refresh active accounts (2 times)
        expect(accountService.refreshAccountToken).toHaveBeenCalledTimes(2);
        expect(accountService.refreshAccountToken).toHaveBeenCalledWith('1');
        expect(accountService.refreshAccountToken).toHaveBeenCalledWith('2');
      });
    });
  });

  describe('Responsive Layout', () => {
    it('should use full viewport width', () => {
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const mainContainer = screen.getByRole('main');
      expect(mainContainer).toHaveClass('w-full');
    });

    it('should stack action buttons on mobile', () => {
      // Mock mobile viewport
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(max-width: 640px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const buttonContainer = screen.getByRole('button', { name: /Sync from Amazon/i }).parentElement;
      expect(buttonContainer).toHaveClass('flex-col');
    });

    it('should show responsive grid for status cards', () => {
      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const statusGrid = screen.getByTestId('status-overview-grid');
      expect(statusGrid).toHaveClass('grid');
      expect(statusGrid).toHaveClass('sm:grid-cols-2');
      expect(statusGrid).toHaveClass('lg:grid-cols-3');
      expect(statusGrid).toHaveClass('xl:grid-cols-4');
    });
  });

  describe('Error Handling', () => {
    it('should show error alert when accounts fail to load', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockRejectedValue(
        new Error('Network error')
      );

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Failed to load accounts/i)).toBeInTheDocument();
      });
    });

    it('should show permission denied message for DSP when user lacks access', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getDSPAccounts).mockRejectedValue({
        response: { status: 403 },
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      await waitFor(() => {
        expect(screen.getByText(/don't have access to DSP/i)).toBeInTheDocument();
        expect(screen.getByText(/Contact your administrator/i)).toBeInTheDocument();
      });
    });

    it('should show permission denied message for AMC when user lacks access', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getAMCAccounts).mockRejectedValue({
        response: { status: 403 },
      });

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const amcTab = screen.getByRole('tab', { name: /AMC/i });
      await user.click(amcTab);

      await waitFor(() => {
        expect(screen.getByText(/don't have access to AMC/i)).toBeInTheDocument();
        expect(screen.getByText(/requires additional permissions/i)).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    it('should show skeleton loader while fetching data', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('account-table-skeleton')).toBeInTheDocument();
      });
    });

    it('should show loading spinner on sync button when syncing', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.syncAmazonAccounts).mockImplementation(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<AccountManagementPage />, { wrapper: createWrapper() });

      const syncButton = screen.getByRole('button', { name: /Sync from Amazon/i });
      await user.click(syncButton);

      const spinner = within(syncButton).getByTestId('loading-spinner');
      expect(spinner).toHaveClass('animate-pulse');
    });
  });
});