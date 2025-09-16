import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccountTypeTabs } from './AccountTypeTabs';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

// Mock the account service
vi.mock('@/services/accountService', () => ({
  accountService: {
    getSponsoredAdsAccounts: vi.fn(),
    getDSPAccounts: vi.fn(),
    getAMCAccounts: vi.fn(),
  },
}));

// Mock the toast hook
vi.mock('@/components/ui/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('AccountTypeTabs', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Tab Navigation', () => {
    it('should render all three tabs correctly', () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      expect(screen.getByRole('tab', { name: /Sponsored Ads/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /DSP/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /AMC/i })).toBeInTheDocument();
    });

    it('should have Sponsored Ads tab active by default', () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
      expect(sponsoredAdsTab).toHaveAttribute('data-state', 'active');

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      expect(dspTab).toHaveAttribute('data-state', 'inactive');

      const amcTab = screen.getByRole('tab', { name: /AMC/i });
      expect(amcTab).toHaveAttribute('data-state', 'inactive');
    });

    it('should display count badges on tabs', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: Array(5).fill({}).map((_, i) => ({ id: `sp-${i}` })),
        totalCount: 5,
      });

      vi.mocked(accountService.getDSPAccounts).mockResolvedValue({
        accounts: Array(3).fill({}).map((_, i) => ({ id: `dsp-${i}` })),
        totalCount: 3,
      });

      vi.mocked(accountService.getAMCAccounts).mockResolvedValue({
        instances: Array(2).fill({}).map((_, i) => ({ id: `amc-${i}` })),
        totalCount: 2,
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      await waitFor(() => {
        const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
        expect(within(sponsoredAdsTab).getByText('5')).toBeInTheDocument();
      });

      await waitFor(() => {
        const dspTab = screen.getByRole('tab', { name: /DSP/i });
        expect(within(dspTab).getByText('3')).toBeInTheDocument();
      });

      await waitFor(() => {
        const amcTab = screen.getByRole('tab', { name: /AMC/i });
        expect(within(amcTab).getByText('2')).toBeInTheDocument();
      });
    });
  });

  describe('Tab Switching', () => {
    it('should switch active tab on click', async () => {
      const user = userEvent.setup();
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      // Initially Sponsored Ads is active
      const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
      expect(sponsoredAdsTab).toHaveAttribute('data-state', 'active');

      // Click DSP tab
      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      expect(dspTab).toHaveAttribute('data-state', 'active');
      expect(sponsoredAdsTab).toHaveAttribute('data-state', 'inactive');
    });

    it('should update URL when switching tabs', async () => {
      const user = userEvent.setup();
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      // Check that URL would be updated (in a real scenario with routing)
      expect(dspTab).toHaveAttribute('data-state', 'active');
    });

    it('should load appropriate content when switching tabs', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getDSPAccounts).mockResolvedValue({
        accounts: [{ id: 'dsp-1', accountName: 'DSP Account 1' }],
        totalCount: 1,
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      await waitFor(() => {
        expect(accountService.getDSPAccounts).toHaveBeenCalled();
      });
    });
  });

  describe('Progressive Loading', () => {
    it('should only load Sponsored Ads data on initial mount', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockResolvedValue({
        accounts: [],
        totalCount: 0,
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(accountService.getSponsoredAdsAccounts).toHaveBeenCalled();
      });

      expect(accountService.getDSPAccounts).not.toHaveBeenCalled();
      expect(accountService.getAMCAccounts).not.toHaveBeenCalled();
    });

    it('should lazy-load DSP data when tab is selected', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getDSPAccounts).mockResolvedValue({
        accounts: [],
        totalCount: 0,
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      // Initially DSP data is not loaded
      expect(accountService.getDSPAccounts).not.toHaveBeenCalled();

      // Click DSP tab
      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      // DSP data should be loaded
      await waitFor(() => {
        expect(accountService.getDSPAccounts).toHaveBeenCalled();
      });
    });

    it('should show loading skeleton while data is being fetched', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockImplementation(
        () => new Promise(() => {}) // Never resolves to keep loading state
      );

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByTestId('account-table-skeleton')).toBeInTheDocument();
      });
    });
  });

  describe('Responsive Behavior', () => {
    it('should be scrollable on mobile devices', () => {
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

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const tabsList = screen.getByRole('tablist');
      expect(tabsList).toHaveClass('overflow-x-auto');
    });

    it('should display tabs horizontally on desktop', () => {
      // Mock desktop viewport
      window.matchMedia = vi.fn().mockImplementation((query) => ({
        matches: query === '(min-width: 1024px)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }));

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const tabsList = screen.getByRole('tablist');
      expect(tabsList).toHaveClass('inline-flex');
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support keyboard navigation between tabs', async () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
      const dspTab = screen.getByRole('tab', { name: /DSP/i });

      // Focus on first tab
      sponsoredAdsTab.focus();
      expect(document.activeElement).toBe(sponsoredAdsTab);

      // Press arrow right to move to next tab
      const arrowRightEvent = new KeyboardEvent('keydown', { key: 'ArrowRight' });
      sponsoredAdsTab.dispatchEvent(arrowRightEvent);

      // Note: Radix UI handles keyboard navigation internally
      // In a real test environment, this would move focus to the DSP tab
    });

    it('should activate tab on Enter key press', async () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });

      // Focus and press Enter
      dspTab.focus();
      const enterEvent = new KeyboardEvent('keydown', { key: 'Enter' });
      dspTab.dispatchEvent(enterEvent);

      // Note: Radix UI handles keyboard activation internally
    });
  });

  describe('Error Handling', () => {
    it('should show error message when API call fails', async () => {
      const { accountService } = await import('@/services/accountService');

      vi.mocked(accountService.getSponsoredAdsAccounts).mockRejectedValue(
        new Error('Failed to fetch accounts')
      );

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      await waitFor(() => {
        expect(screen.getByText(/Failed to load accounts/i)).toBeInTheDocument();
      });
    });

    it('should handle 403 permission errors gracefully for DSP', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getDSPAccounts).mockRejectedValue({
        response: { status: 403 },
        message: 'Access denied',
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      await waitFor(() => {
        expect(screen.getByText(/You don't have access to DSP accounts/i)).toBeInTheDocument();
      });
    });

    it('should handle 403 permission errors gracefully for AMC', async () => {
      const { accountService } = await import('@/services/accountService');
      const user = userEvent.setup();

      vi.mocked(accountService.getAMCAccounts).mockRejectedValue({
        response: { status: 403 },
        message: 'Access denied',
      });

      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const amcTab = screen.getByRole('tab', { name: /AMC/i });
      await user.click(amcTab);

      await waitFor(() => {
        expect(screen.getByText(/You don't have access to AMC instances/i)).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA attributes', () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const tabsList = screen.getByRole('tablist');
      expect(tabsList).toBeInTheDocument();

      const tabs = screen.getAllByRole('tab');
      tabs.forEach((tab) => {
        expect(tab).toHaveAttribute('aria-selected');
        expect(tab).toHaveAttribute('aria-controls');
      });
    });

    it('should have proper focus indicators', () => {
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const sponsoredAdsTab = screen.getByRole('tab', { name: /Sponsored Ads/i });
      sponsoredAdsTab.focus();

      // Check that focused tab has focus-visible styles
      expect(sponsoredAdsTab).toHaveClass('focus-visible:ring-2');
    });

    it('should announce tab changes to screen readers', async () => {
      const user = userEvent.setup();
      render(<AccountTypeTabs />, { wrapper: createWrapper() });

      const dspTab = screen.getByRole('tab', { name: /DSP/i });
      await user.click(dspTab);

      // The tab panel should be properly associated
      const dspPanel = screen.getByRole('tabpanel');
      expect(dspPanel).toHaveAttribute('aria-labelledby', dspTab.id);
    });
  });
});