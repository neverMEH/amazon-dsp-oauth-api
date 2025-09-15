import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AccountTypeTable } from './AccountTypeTable';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

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
      {children}
    </QueryClientProvider>
  );
};

describe('AccountTypeTable', () => {
  const mockSponsoredAdsAccounts = [
    {
      id: 'sp-1',
      accountName: 'Account 1',
      profileId: '12345',
      entityId: 'ENTITY123',
      marketplaces: ['US', 'CA'],
      status: 'active',
      lastManagedAt: '2024-01-15T10:00:00Z',
    },
    {
      id: 'sp-2',
      accountName: 'Account 2',
      profileId: '67890',
      entityId: 'ENTITY456',
      marketplaces: ['UK', 'DE'],
      status: 'error',
      lastManagedAt: '2024-01-14T09:00:00Z',
    },
  ];

  const mockDSPAccounts = [
    {
      id: 'dsp-1',
      accountName: 'DSP Account 1',
      entityId: 'DSP_ENTITY_1',
      profileId: 'DSP_12345',
      marketplace: 'US',
      status: 'active',
      advertiserType: 'Brand',
    },
    {
      id: 'dsp-2',
      accountName: 'DSP Account 2',
      entityId: 'DSP_ENTITY_2',
      profileId: 'DSP_67890',
      marketplace: 'UK',
      status: 'disconnected',
      advertiserType: 'Agency',
    },
  ];

  const mockAMCInstances = [
    {
      id: 'amc-1',
      instanceName: 'AMC Instance 1',
      associatedDSPAccounts: ['dsp-1', 'dsp-2'],
      associatedSponsoredAdsAccounts: ['sp-1', 'sp-2'],
      audienceCount: 15,
      workflowStatus: 'active',
      dataFreshness: 'Real-time',
    },
    {
      id: 'amc-2',
      instanceName: 'AMC Instance 2',
      associatedDSPAccounts: ['dsp-3'],
      associatedSponsoredAdsAccounts: ['sp-3', 'sp-4', 'sp-5'],
      audienceCount: 8,
      workflowStatus: 'paused',
      dataFreshness: 'Daily',
    },
  ];

  const defaultProps = {
    onViewDetails: vi.fn(),
    onDisconnect: vi.fn(),
    onRefresh: vi.fn(),
    onReauthorize: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Sponsored Ads Table', () => {
    it('should render correct columns for Sponsored Ads accounts', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check column headers
      expect(screen.getByText('Account Name')).toBeInTheDocument();
      expect(screen.getByText('Profile ID')).toBeInTheDocument();
      expect(screen.getByText('Entity ID')).toBeInTheDocument();
      expect(screen.getByText('Marketplaces')).toBeInTheDocument();
      expect(screen.getByText('Last Managed')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('should display Sponsored Ads account data correctly', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check first account data
      expect(screen.getByText('Account 1')).toBeInTheDocument();
      expect(screen.getByText('12345')).toBeInTheDocument();
      expect(screen.getByText('ENTITY123')).toBeInTheDocument();
      expect(screen.getByText('US, CA')).toBeInTheDocument();

      // Check second account data
      expect(screen.getByText('Account 2')).toBeInTheDocument();
      expect(screen.getByText('67890')).toBeInTheDocument();
      expect(screen.getByText('ENTITY456')).toBeInTheDocument();
      expect(screen.getByText('UK, DE')).toBeInTheDocument();
    });

    it('should show campaign metrics for Sponsored Ads', () => {
      const accountsWithMetrics = [
        {
          ...mockSponsoredAdsAccounts[0],
          campaignCount: 25,
          activeKeywords: 150,
          dailySpend: 1250.50,
        },
      ];

      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={accountsWithMetrics}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('25 campaigns')).toBeInTheDocument();
      expect(screen.getByText('150 keywords')).toBeInTheDocument();
      expect(screen.getByText('$1,250.50/day')).toBeInTheDocument();
    });
  });

  describe('DSP Table', () => {
    it('should render correct columns for DSP accounts', () => {
      render(
        <AccountTypeTable
          accountType="dsp"
          accounts={mockDSPAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check column headers
      expect(screen.getByText('Account Name')).toBeInTheDocument();
      expect(screen.getByText('Entity ID')).toBeInTheDocument();
      expect(screen.getByText('Profile ID')).toBeInTheDocument();
      expect(screen.getByText('Marketplace')).toBeInTheDocument();
      expect(screen.getByText('Advertiser Type')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('should display DSP account data correctly', () => {
      render(
        <AccountTypeTable
          accountType="dsp"
          accounts={mockDSPAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check first account
      expect(screen.getByText('DSP Account 1')).toBeInTheDocument();
      expect(screen.getByText('DSP_ENTITY_1')).toBeInTheDocument();
      expect(screen.getByText('DSP_12345')).toBeInTheDocument();
      expect(screen.getByText('Brand')).toBeInTheDocument();

      // Check second account
      expect(screen.getByText('DSP Account 2')).toBeInTheDocument();
      expect(screen.getByText('DSP_ENTITY_2')).toBeInTheDocument();
      expect(screen.getByText('DSP_67890')).toBeInTheDocument();
      expect(screen.getByText('Agency')).toBeInTheDocument();
    });

    it('should show DSP-specific metrics', () => {
      const accountsWithMetrics = [
        {
          ...mockDSPAccounts[0],
          orderCount: 12,
          activeLineItems: 45,
          dspSpend: 25000.00,
        },
      ];

      render(
        <AccountTypeTable
          accountType="dsp"
          accounts={accountsWithMetrics}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText('12 orders')).toBeInTheDocument();
      expect(screen.getByText('45 line items')).toBeInTheDocument();
      expect(screen.getByText('$25,000.00')).toBeInTheDocument();
    });
  });

  describe('AMC Table', () => {
    it('should render correct columns for AMC instances', () => {
      render(
        <AccountTypeTable
          accountType="amc"
          accounts={mockAMCInstances}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check column headers
      expect(screen.getByText('Instance Name')).toBeInTheDocument();
      expect(screen.getByText('Associated Accounts')).toBeInTheDocument();
      expect(screen.getByText('Audiences')).toBeInTheDocument();
      expect(screen.getByText('Workflow Status')).toBeInTheDocument();
      expect(screen.getByText('Data Freshness')).toBeInTheDocument();
    });

    it('should display AMC instance data correctly', () => {
      render(
        <AccountTypeTable
          accountType="amc"
          accounts={mockAMCInstances}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check first instance
      expect(screen.getByText('AMC Instance 1')).toBeInTheDocument();
      expect(screen.getByText('2 DSP, 2 SP')).toBeInTheDocument();
      expect(screen.getByText('15 audiences')).toBeInTheDocument();
      expect(screen.getByText('Real-time')).toBeInTheDocument();

      // Check second instance
      expect(screen.getByText('AMC Instance 2')).toBeInTheDocument();
      expect(screen.getByText('1 DSP, 3 SP')).toBeInTheDocument();
      expect(screen.getByText('8 audiences')).toBeInTheDocument();
      expect(screen.getByText('Daily')).toBeInTheDocument();
    });
  });

  describe('Sorting', () => {
    it('should sort by account name', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const nameHeader = screen.getByText('Account Name');
      await user.click(nameHeader);

      const rows = screen.getAllByRole('row');
      expect(within(rows[1]).getByText('Account 1')).toBeInTheDocument();
      expect(within(rows[2]).getByText('Account 2')).toBeInTheDocument();

      // Click again to reverse sort
      await user.click(nameHeader);
      const reversedRows = screen.getAllByRole('row');
      expect(within(reversedRows[1]).getByText('Account 2')).toBeInTheDocument();
      expect(within(reversedRows[2]).getByText('Account 1')).toBeInTheDocument();
    });

    it('should show sort indicators', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const nameHeader = screen.getByText('Account Name');

      // Check for sort indicator
      expect(within(nameHeader.parentElement!).getByTestId('sort-indicator')).toBeInTheDocument();

      await user.click(nameHeader);

      // Check for ascending indicator
      expect(within(nameHeader.parentElement!).getByTestId('sort-asc')).toBeInTheDocument();

      await user.click(nameHeader);

      // Check for descending indicator
      expect(within(nameHeader.parentElement!).getByTestId('sort-desc')).toBeInTheDocument();
    });
  });

  describe('Filtering', () => {
    it('should filter accounts by status', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Initially both accounts are visible
      expect(screen.getByText('Account 1')).toBeInTheDocument();
      expect(screen.getByText('Account 2')).toBeInTheDocument();

      // Apply filter for active accounts
      const filterButton = screen.getByRole('button', { name: /Filter/i });
      await user.click(filterButton);

      const activeFilter = screen.getByRole('option', { name: /Active/i });
      await user.click(activeFilter);

      // Only active account should be visible
      expect(screen.getByText('Account 1')).toBeInTheDocument();
      expect(screen.queryByText('Account 2')).not.toBeInTheDocument();
    });

    it('should filter by search query', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const searchInput = screen.getByPlaceholderText(/Search accounts/i);
      await user.type(searchInput, 'Account 1');

      await waitFor(() => {
        expect(screen.getByText('Account 1')).toBeInTheDocument();
        expect(screen.queryByText('Account 2')).not.toBeInTheDocument();
      });
    });
  });

  describe('Actions', () => {
    it('should show action buttons for each account', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const rows = screen.getAllByRole('row').slice(1); // Skip header row

      rows.forEach((row) => {
        expect(within(row).getByRole('button', { name: /View Details/i })).toBeInTheDocument();
        expect(within(row).getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
        expect(within(row).getByRole('button', { name: /More/i })).toBeInTheDocument();
      });
    });

    it('should call onViewDetails when view button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const viewButtons = screen.getAllByRole('button', { name: /View Details/i });
      await user.click(viewButtons[0]);

      expect(defaultProps.onViewDetails).toHaveBeenCalledWith(mockSponsoredAdsAccounts[0]);
    });

    it('should call onRefresh when refresh button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const refreshButtons = screen.getAllByRole('button', { name: /Refresh/i });
      await user.click(refreshButtons[0]);

      expect(defaultProps.onRefresh).toHaveBeenCalledWith('sp-1');
    });

    it('should show type-specific actions for Sponsored Ads', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const moreButtons = screen.getAllByRole('button', { name: /More/i });
      await user.click(moreButtons[0]);

      expect(screen.getByText('Create Campaign')).toBeInTheDocument();
      expect(screen.getByText('View Reports')).toBeInTheDocument();
      expect(screen.getByText('Manage Keywords')).toBeInTheDocument();
    });

    it('should show type-specific actions for DSP', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="dsp"
          accounts={mockDSPAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const moreButtons = screen.getAllByRole('button', { name: /More/i });
      await user.click(moreButtons[0]);

      expect(screen.getByText('Create Order')).toBeInTheDocument();
      expect(screen.getByText('View Audiences')).toBeInTheDocument();
      expect(screen.getByText('Manage Creatives')).toBeInTheDocument();
    });

    it('should show type-specific actions for AMC', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="amc"
          accounts={mockAMCInstances}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const moreButtons = screen.getAllByRole('button', { name: /More/i });
      await user.click(moreButtons[0]);

      expect(screen.getByText('Create Audience')).toBeInTheDocument();
      expect(screen.getByText('Run Workflow')).toBeInTheDocument();
      expect(screen.getByText('View Insights')).toBeInTheDocument();
    });
  });

  describe('Status Indicators', () => {
    it('should show correct status indicators', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      // Check active status
      const activeStatus = screen.getByTestId('status-active');
      expect(activeStatus).toHaveClass('bg-green-500');

      // Check error status
      const errorStatus = screen.getByTestId('status-error');
      expect(errorStatus).toHaveClass('bg-red-500');
    });

    it('should show tooltips for status indicators', async () => {
      const user = userEvent.setup();
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={mockSponsoredAdsAccounts}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      const activeStatus = screen.getByTestId('status-active');
      await user.hover(activeStatus);

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toHaveTextContent('Account is active and healthy');
      });
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no accounts', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={[]}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/No accounts found/i)).toBeInTheDocument();
      expect(screen.getByText(/Try adjusting your filters/i)).toBeInTheDocument();
    });
  });

  describe('Loading State', () => {
    it('should show skeleton loader when loading', () => {
      render(
        <AccountTypeTable
          accountType="sponsored-ads"
          accounts={[]}
          isLoading={true}
          {...defaultProps}
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByTestId('table-skeleton')).toBeInTheDocument();
      expect(screen.getAllByTestId('skeleton-row')).toHaveLength(5); // Default skeleton rows
    });
  });
});