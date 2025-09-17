import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format } from 'date-fns';
import {
  RefreshCw,
  Filter,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Clock,
  Check,
  X
} from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
} from '@/components/ui/dropdown-menu';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useToast } from '@/components/ui/use-toast';
import { dspSeatsService } from '@/services/dspSeatsService';

interface DSPSeatsTabProps {
  advertiserId: string;
}

interface SeatInfo {
  exchangeId: string;
  exchangeName: string;
  dealCreationId?: string | null;
  spendTrackingId?: string | null;
}

export const DSPSeatsTab: React.FC<DSPSeatsTabProps> = ({ advertiserId }) => {
  const [pageSize, setPageSize] = useState(10);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedExchanges, setSelectedExchanges] = useState<string[]>([]);
  const [nextToken, setNextToken] = useState<string | null>(null);

  // Reset state when advertiserId changes
  useEffect(() => {
    setCurrentPage(1);
    setSelectedExchanges([]);
    setNextToken(null);
  }, [advertiserId]);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Stabilize query dependencies with useMemo
  const stableQueryParams = useMemo(() => ({
    maxResults: pageSize,
    nextToken: nextToken || undefined,
    exchangeIds: selectedExchanges.length > 0 ? selectedExchanges : undefined,
  }), [pageSize, nextToken, selectedExchanges]);

  const stableQueryKey = useMemo(() => [
    'dsp-seats',
    advertiserId,
    pageSize,
    nextToken,
    selectedExchanges.length > 0 ? selectedExchanges.join(',') : ''
  ], [advertiserId, pageSize, nextToken, selectedExchanges]);

  // Fetch advertiser seats with AbortController support
  const {
    data: seatsData,
    isLoading,
    error,
    refetch
  } = useQuery({
    queryKey: stableQueryKey,
    queryFn: async ({ signal }) => {
      return dspSeatsService.fetchAdvertiserSeats(advertiserId, {
        ...stableQueryParams,
        signal, // Pass AbortController signal for request cancellation
      });
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!advertiserId,
    // Cancel queries when component unmounts or key changes
    refetchOnWindowFocus: false,
  });

  // Refresh mutation
  const refreshMutation = useMutation({
    mutationFn: () => dspSeatsService.refreshAdvertiserSeats(advertiserId, {
      force: true,
      include_sync_log: false,
    }),
    onSuccess: (data) => {
      toast({
        title: 'Success',
        description: `Seats refreshed successfully. ${data.seats_updated} seats updated.`,
      });
      // Refetch the seats data
      refetch();
    },
    onError: (error: Error) => {
      toast({
        title: 'Error',
        description: 'Failed to refresh seats. Please try again.',
        variant: 'destructive',
      });
    },
  });

  // Process seats data
  const seats = useMemo(() => {
    if (!seatsData?.advertiserSeats) return [];

    const advertiserSeat = seatsData.advertiserSeats.find(
      (seat) => seat.advertiserId === advertiserId
    );

    if (!advertiserSeat?.currentSeats) return [];

    // Apply client-side filtering if needed
    let filteredSeats = advertiserSeat.currentSeats;
    if (selectedExchanges.length > 0) {
      filteredSeats = filteredSeats.filter(seat =>
        selectedExchanges.includes(seat.exchangeId)
      );
    }

    return filteredSeats;
  }, [seatsData, advertiserId, selectedExchanges]);

  // Get unique exchanges for filter
  const availableExchanges = useMemo(() => {
    if (!seatsData?.advertiserSeats) return [];

    const advertiserSeat = seatsData.advertiserSeats.find(
      (seat) => seat.advertiserId === advertiserId
    );

    if (!advertiserSeat?.currentSeats) return [];

    const uniqueExchanges = new Map<string, string>();
    advertiserSeat.currentSeats.forEach(seat => {
      uniqueExchanges.set(seat.exchangeId, seat.exchangeName);
    });

    return Array.from(uniqueExchanges.entries()).map(([id, name]) => ({
      id,
      name,
    }));
  }, [seatsData, advertiserId]);

  const handlePageSizeChange = useCallback((value: string) => {
    setPageSize(parseInt(value, 10));
    setCurrentPage(1);
    setNextToken(null);
  }, []);

  const handleNextPage = useCallback(() => {
    if (seatsData?.nextToken) {
      setNextToken(seatsData.nextToken);
      setCurrentPage(prev => prev + 1);
    }
  }, [seatsData?.nextToken]);

  const handlePrevPage = useCallback(() => {
    // Note: Real implementation would need to track previous tokens
    setCurrentPage(prev => Math.max(1, prev - 1));
    setNextToken(null);
  }, []);

  const handleClearFilter = useCallback(() => {
    setSelectedExchanges([]);
    setCurrentPage(1);
    setNextToken(null);
  }, []);

  const toggleExchange = useCallback((exchangeId: string) => {
    setSelectedExchanges(prev =>
      prev.includes(exchangeId)
        ? prev.filter(id => id !== exchangeId)
        : [...prev, exchangeId]
    );
    setCurrentPage(1);
    setNextToken(null);
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-4" data-testid="seats-loading">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Exchange</TableHead>
                <TableHead>Deal Creation ID</TableHead>
                <TableHead>Spend Tracking ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[...Array(3)].map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                  <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load advertiser seats.
          <Button
            variant="link"
            className="px-2"
            onClick={() => refetch()}
          >
            Try Again
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with sync status and actions */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold">Advertiser Seats</h3>
          {seatsData && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock className="h-3 w-3" />
              <span>Last updated: {format(new Date(seatsData.timestamp), 'PPp')}</span>
              {seatsData.cached && <Badge variant="secondary">(Cached)</Badge>}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refreshMutation.mutate()}
            disabled={refreshMutation.isPending}
            data-testid="refresh-button"
            aria-label="Refresh seats"
          >
            {refreshMutation.isPending ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                <span data-testid="refresh-loading">Refreshing...</span>
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </>
            )}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                data-testid="exchange-filter-button"
                aria-label="Filter exchanges"
              >
                <Filter className="h-4 w-4 mr-2" />
                Filter ({selectedExchanges.length})
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56">
              {availableExchanges.map(exchange => (
                <DropdownMenuCheckboxItem
                  key={exchange.id}
                  checked={selectedExchanges.includes(exchange.id)}
                  onCheckedChange={() => toggleExchange(exchange.id)}
                >
                  {exchange.name}
                </DropdownMenuCheckboxItem>
              ))}
              {availableExchanges.length > 0 && (
                <>
                  <DropdownMenuItem onClick={handleClearFilter}>
                    Clear All
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Filter status */}
      {selectedExchanges.length > 0 && (
        <div className="text-sm text-muted-foreground">
          Filtering by {selectedExchanges.length} exchange{selectedExchanges.length !== 1 ? 's' : ''}
        </div>
      )}

      {selectedExchanges.length === 0 && availableExchanges.length > 0 && (
        <div className="text-sm text-muted-foreground">
          Showing all exchanges
        </div>
      )}

      {/* Seats table */}
      <div className="border rounded-lg">
        <Table aria-label="Advertiser seats">
          <TableHeader>
            <TableRow>
              <TableHead className="w-[30%]">Exchange</TableHead>
              <TableHead className="w-[35%]">Deal Creation ID</TableHead>
              <TableHead className="w-[35%]">Spend Tracking ID</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {seats.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center py-8 text-muted-foreground">
                  No advertiser seats found
                </TableCell>
              </TableRow>
            ) : (
              seats.map((seat, index) => (
                <TableRow key={`${seat.exchangeId}-${index}`}>
                  <TableCell className="font-medium">
                    {seat.exchangeName}
                  </TableCell>
                  <TableCell>
                    {seat.dealCreationId ? (
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {seat.dealCreationId}
                      </code>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell>
                    {seat.spendTrackingId ? (
                      <code className="text-xs bg-muted px-2 py-1 rounded">
                        {seat.spendTrackingId}
                      </code>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination controls */}
      {seats.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Label htmlFor="page-size" className="text-sm">
              Rows per page:
            </Label>
            <Select
              value={pageSize.toString()}
              onValueChange={handlePageSizeChange}
            >
              <SelectTrigger
                id="page-size"
                className="w-20"
                data-testid="page-size-select"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
                <SelectItem value="200">200</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {currentPage}
            </span>
            <Button
              variant="outline"
              size="icon"
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              data-testid="prev-page-button"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={handleNextPage}
              disabled={!seatsData?.nextToken}
              data-testid="next-page-button"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Success/error messages */}
      {refreshMutation.isSuccess && (
        <Alert className="border-green-200 bg-green-50">
          <Check className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            Seats refreshed successfully
          </AlertDescription>
        </Alert>
      )}

      {refreshMutation.isError && (
        <Alert variant="destructive">
          <X className="h-4 w-4" />
          <AlertDescription>
            Failed to refresh seats
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};