import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { DSPSeatsTab } from '../DSPSeatsTab';
import * as dspSeatsService from '@/services/dspSeatsService';

// Mock the DSP seats service
vi.mock('@/services/dspSeatsService');

const mockDspSeatsService = dspSeatsService as {
  fetchAdvertiserSeats: ReturnType<typeof vi.fn>;
  refreshAdvertiserSeats: ReturnType<typeof vi.fn>;
  fetchSyncHistory: ReturnType<typeof vi.fn>;
};

// Create a test query client
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <QueryClientProvider client={createTestQueryClient()}>
    {children}
  </QueryClientProvider>
);

describe('DSPSeatsTab', () => {
  const mockAdvertiserId = 'DSP123';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial Render', () => {
    it('should display loading state initially', () => {
      mockDspSeatsService.fetchAdvertiserSeats.mockImplementation(
        () => new Promise(() => {}) // Never resolves to keep loading state
      );

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      expect(screen.getByTestId('seats-loading')).toBeInTheDocument();
    });

    it('should display seats data when loaded', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [
              {
                exchangeId: '1',
                exchangeName: 'Google Ad Manager',
                dealCreationId: 'DEAL123',
                spendTrackingId: 'TRACK456',
              },
              {
                exchangeId: '2',
                exchangeName: 'Amazon Publisher Services',
                dealCreationId: null,
                spendTrackingId: 'APS789',
              },
            ],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Google Ad Manager')).toBeInTheDocument();
        expect(screen.getByText('Amazon Publisher Services')).toBeInTheDocument();
      });

      expect(screen.getByText('DEAL123')).toBeInTheDocument();
      expect(screen.getByText('TRACK456')).toBeInTheDocument();
      expect(screen.getByText('APS789')).toBeInTheDocument();
    });

    it('should display empty state when no seats', async () => {
      const mockEmptyData = {
        advertiserSeats: [],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockEmptyData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No advertiser seats found')).toBeInTheDocument();
      });
    });

    it('should display error state on fetch failure', async () => {
      mockDspSeatsService.fetchAdvertiserSeats.mockRejectedValue(
        new Error('Failed to fetch seats')
      );

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Failed to load advertiser seats/)).toBeInTheDocument();
        expect(screen.getByText('Try Again')).toBeInTheDocument();
      });
    });
  });

  describe('Exchange Filtering', () => {
    it('should filter seats by exchange when filter is applied', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [
              {
                exchangeId: '1',
                exchangeName: 'Google Ad Manager',
                dealCreationId: 'DEAL123',
                spendTrackingId: 'TRACK456',
              },
              {
                exchangeId: '2',
                exchangeName: 'Amazon Publisher Services',
                dealCreationId: null,
                spendTrackingId: 'APS789',
              },
            ],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Google Ad Manager')).toBeInTheDocument();
      });

      // Click filter dropdown
      const filterButton = screen.getByTestId('exchange-filter-button');
      fireEvent.click(filterButton);

      // Select Google Ad Manager from dropdown menu
      const googleOption = screen.getByText('Google Ad Manager');
      fireEvent.click(googleOption);

      // Verify filtered results
      await waitFor(() => {
        expect(screen.getByText('Google Ad Manager')).toBeInTheDocument();
        expect(screen.queryByText('Amazon Publisher Services')).not.toBeInTheDocument();
      });
    });

    it('should clear filters when clear button is clicked', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [
              {
                exchangeId: '1',
                exchangeName: 'Google Ad Manager',
                dealCreationId: 'DEAL123',
                spendTrackingId: 'TRACK456',
              },
            ],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Google Ad Manager')).toBeInTheDocument();
      });

      // Apply a filter first
      const filterButton = screen.getByTestId('exchange-filter-button');
      fireEvent.click(filterButton);

      const clearButton = screen.getByText('Clear All');
      fireEvent.click(clearButton);

      // Verify all seats are shown again
      await waitFor(() => {
        expect(screen.getByText('Showing all exchanges')).toBeInTheDocument();
      });
    });
  });

  describe('Pagination', () => {
    it('should handle pagination controls', async () => {
      const mockFirstPage = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: Array.from({ length: 10 }, (_, i) => ({
              exchangeId: String(i),
              exchangeName: `Exchange ${i}`,
              dealCreationId: `DEAL${i}`,
              spendTrackingId: `TRACK${i}`,
            })),
          },
        ],
        nextToken: 'token123',
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      const mockSecondPage = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: Array.from({ length: 5 }, (_, i) => ({
              exchangeId: String(i + 10),
              exchangeName: `Exchange ${i + 10}`,
              dealCreationId: `DEAL${i + 10}`,
              spendTrackingId: `TRACK${i + 10}`,
            })),
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats
        .mockResolvedValueOnce(mockFirstPage)
        .mockResolvedValueOnce(mockSecondPage);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Exchange 0')).toBeInTheDocument();
      });

      // Verify next button is enabled
      const nextButton = screen.getByTestId('next-page-button');
      expect(nextButton).not.toBeDisabled();

      // Click next page
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText('Exchange 10')).toBeInTheDocument();
        expect(screen.queryByText('Exchange 0')).not.toBeInTheDocument();
      });

      // Verify next button is now disabled (no more pages)
      expect(screen.getByTestId('next-page-button')).toBeDisabled();

      // Verify previous button is enabled
      const prevButton = screen.getByTestId('prev-page-button');
      expect(prevButton).not.toBeDisabled();
    });

    it('should change page size', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: Array.from({ length: 20 }, (_, i) => ({
              exchangeId: String(i),
              exchangeName: `Exchange ${i}`,
              dealCreationId: `DEAL${i}`,
              spendTrackingId: `TRACK${i}`,
            })),
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Exchange 0')).toBeInTheDocument();
      });

      // Change page size
      const pageSizeSelect = screen.getByTestId('page-size-select');
      fireEvent.change(pageSizeSelect, { target: { value: '25' } });

      // Verify API is called with new page size
      expect(mockDspSeatsService.fetchAdvertiserSeats).toHaveBeenCalledWith(
        mockAdvertiserId,
        expect.objectContaining({ maxResults: 25 })
      );
    });
  });

  describe('Manual Refresh', () => {
    it('should trigger refresh when refresh button is clicked', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [
              {
                exchangeId: '1',
                exchangeName: 'Google Ad Manager',
                dealCreationId: 'DEAL123',
                spendTrackingId: 'TRACK456',
              },
            ],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      const mockRefreshResponse = {
        success: true,
        seats_updated: 1,
        last_sync: '2025-09-16T10:05:00Z',
        sync_log_id: 'log123',
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);
      mockDspSeatsService.refreshAdvertiserSeats.mockResolvedValue(mockRefreshResponse);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Google Ad Manager')).toBeInTheDocument();
      });

      // Click refresh button
      const refreshButton = screen.getByTestId('refresh-button');
      fireEvent.click(refreshButton);

      // Verify loading state
      expect(screen.getByTestId('refresh-loading')).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText('Seats refreshed successfully')).toBeInTheDocument();
      });

      // Verify refresh was called
      expect(mockDspSeatsService.refreshAdvertiserSeats).toHaveBeenCalledWith(
        mockAdvertiserId,
        { force: true, include_sync_log: false }
      );

      // Verify data is refetched
      expect(mockDspSeatsService.fetchAdvertiserSeats).toHaveBeenCalledTimes(2);
    });

    it('should handle refresh error', async () => {
      const mockSeatsData = {
        advertiserSeats: [],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);
      mockDspSeatsService.refreshAdvertiserSeats.mockRejectedValue(
        new Error('Refresh failed')
      );

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('refresh-button')).toBeInTheDocument();
      });

      // Click refresh button
      const refreshButton = screen.getByTestId('refresh-button');
      fireEvent.click(refreshButton);

      await waitFor(() => {
        expect(screen.getByText('Failed to refresh seats')).toBeInTheDocument();
      });
    });
  });

  describe('Sync Status', () => {
    it('should display last sync timestamp', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
        expect(screen.getByText(/Sep 16, 2025/)).toBeInTheDocument();
      });
    });

    it('should indicate when data is cached', async () => {
      const mockCachedData = {
        advertiserSeats: [],
        nextToken: null,
        timestamp: '2025-09-16T09:55:00Z',
        cached: true,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockCachedData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('(Cached)')).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [
              {
                exchangeId: '1',
                exchangeName: 'Google Ad Manager',
                dealCreationId: 'DEAL123',
                spendTrackingId: 'TRACK456',
              },
            ],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByRole('table', { name: /advertiser seats/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /refresh seats/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /filter exchanges/i })).toBeInTheDocument();
      });
    });

    it('should be keyboard navigable', async () => {
      const mockSeatsData = {
        advertiserSeats: [
          {
            advertiserId: mockAdvertiserId,
            currentSeats: [],
          },
        ],
        nextToken: null,
        timestamp: '2025-09-16T10:00:00Z',
        cached: false,
      };

      mockDspSeatsService.fetchAdvertiserSeats.mockResolvedValue(mockSeatsData);

      render(
        <TestWrapper>
          <DSPSeatsTab advertiserId={mockAdvertiserId} />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId('refresh-button')).toBeInTheDocument();
      });

      // Tab to refresh button
      const refreshButton = screen.getByTestId('refresh-button');
      refreshButton.focus();
      expect(document.activeElement).toBe(refreshButton);

      // Verify filter button exists and can be focused
      const filterButton = screen.getByTestId('exchange-filter-button');
      filterButton.focus();
      expect(document.activeElement).toBe(filterButton);
    });
  });
});