import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  RefreshCw,
  Search,
  Filter,
  AlertCircle,
  CheckCircle,
  XCircle,
  Globe,
  ChevronDown,
  ChevronRight,
  Loader2,
  AlertTriangle,
  Info
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import {
  AmazonAdsAccount,
  StoredAmazonAccount,
  AccountDisplayData,
  AmazonAdsAccountsResponse
} from '@/types/amazonAdsAccount';

interface AmazonAccountsListProps {
  className?: string;
  onAccountSelect?: (account: StoredAmazonAccount) => void;
  onRefresh?: () => void;
}

export const AmazonAccountsList: React.FC<AmazonAccountsListProps> = ({
  className,
  onAccountSelect,
  onRefresh,
}) => {
  const { toast } = useToast();
  const [accounts, setAccounts] = useState<StoredAmazonAccount[]>([]);
  const [displayAccounts, setDisplayAccounts] = useState<AccountDisplayData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [countryFilter, setCountryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedAccounts, setExpandedAccounts] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);

  // Transform stored account to display data
  const transformToDisplayData = useCallback((account: StoredAmazonAccount): AccountDisplayData => {
    const statusMap: Record<string, 'active' | 'disabled' | 'partial' | 'pending'> = {
      'CREATED': 'active',
      'DISABLED': 'disabled',
      'PARTIALLY_CREATED': 'partial',
      'PENDING': 'pending'
    };

    const primaryProfile = account.metadata.alternateIds?.[0];
    const errorCountries = account.metadata.errors ? Object.keys(account.metadata.errors) : [];

    return {
      id: account.id,
      name: account.accountName,
      amazonId: account.adsAccountId,
      status: statusMap[account.status] || 'pending',
      countries: account.countryCodes || [],
      profileCount: account.alternateIds?.length || 0,
      hasErrors: errorCountries.length > 0,
      errorCountries: errorCountries.length > 0 ? errorCountries : undefined,
      primaryProfile: primaryProfile ? {
        profileId: primaryProfile.profileId,
        countryCode: primaryProfile.countryCode,
        entityId: primaryProfile.entityId
      } : undefined,
      lastSync: account.lastSyncedAt,
      syncStatus: account.syncStatus
    };
  }, []);

  // Fetch accounts from API
  const fetchAccounts = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/accounts/amazon-ads-accounts', {
        headers: {
          'Authorization': `Bearer ${await getAuthToken()}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch accounts: ${response.statusText}`);
      }

      const data: AmazonAdsAccountsResponse = await response.json();

      // Transform API response to stored format (simulating database storage)
      const storedAccounts: StoredAmazonAccount[] = data.accounts.map(account => ({
        ...account,
        id: `local-${account.adsAccountId}`,
        userId: 'current-user',
        accountType: 'advertiser',
        isDefault: false,
        connectedAt: new Date().toISOString(),
        lastSyncedAt: data.timestamp,
        metadata: {
          alternateIds: account.alternateIds,
          countryCodes: account.countryCodes,
          errors: account.errors,
          profileId: account.alternateIds?.[0]?.profileId,
          countryCode: account.alternateIds?.[0]?.countryCode,
          apiStatus: account.status
        },
        syncStatus: 'completed'
      }));

      setAccounts(storedAccounts);
      setDisplayAccounts(storedAccounts.map(transformToDisplayData));

      toast({
        title: "Accounts Loaded",
        description: `Successfully loaded ${storedAccounts.length} accounts`,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load accounts';
      setError(errorMessage);
      toast({
        title: "Error Loading Accounts",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [toast, transformToDisplayData]);

  // Sync accounts with Amazon
  const syncAccounts = useCallback(async () => {
    setIsSyncing(true);

    try {
      const response = await fetch('/api/v1/accounts/sync', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getAuthToken()}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.statusText}`);
      }

      toast({
        title: "Sync Complete",
        description: "Account data has been updated from Amazon",
      });

      // Refresh the account list
      await fetchAccounts();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Sync failed';
      toast({
        title: "Sync Failed",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setIsSyncing(false);
    }
  }, [fetchAccounts, toast]);

  // Filter accounts based on search and filters
  const filteredAccounts = useMemo(() => {
    return displayAccounts.filter(account => {
      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        if (!account.name.toLowerCase().includes(query) &&
            !account.amazonId.toLowerCase().includes(query)) {
          return false;
        }
      }

      // Country filter
      if (countryFilter !== 'all' && !account.countries.includes(countryFilter)) {
        return false;
      }

      // Status filter
      if (statusFilter !== 'all' && account.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [displayAccounts, searchQuery, countryFilter, statusFilter]);

  // Get unique countries for filter
  const availableCountries = useMemo(() => {
    const countries = new Set<string>();
    accounts.forEach(account => {
      account.countryCodes?.forEach(code => countries.add(code));
    });
    return Array.from(countries).sort();
  }, [accounts]);

  // Toggle account expansion
  const toggleAccountExpansion = (accountId: string) => {
    setExpandedAccounts(prev => {
      const newSet = new Set(prev);
      if (newSet.has(accountId)) {
        newSet.delete(accountId);
      } else {
        newSet.add(accountId);
      }
      return newSet;
    });
  };

  // Load accounts on mount
  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Get auth token (placeholder - implement based on your auth method)
  async function getAuthToken(): Promise<string> {
    // This should be implemented based on your authentication method
    // For example, getting a Clerk token or other auth token
    return 'your-auth-token';
  }

  // Render status badge
  const renderStatusBadge = (status: AccountDisplayData['status']) => {
    const config = {
      active: { icon: CheckCircle, className: 'bg-green-100 text-green-800', label: 'Active' },
      disabled: { icon: XCircle, className: 'bg-gray-100 text-gray-800', label: 'Disabled' },
      partial: { icon: AlertTriangle, className: 'bg-yellow-100 text-yellow-800', label: 'Partial' },
      pending: { icon: Loader2, className: 'bg-blue-100 text-blue-800', label: 'Pending' },
    };

    const { icon: Icon, className, label } = config[status];

    return (
      <Badge className={cn('gap-1', className)}>
        <Icon className="h-3 w-3" />
        {label}
      </Badge>
    );
  };

  // Render loading state
  if (isLoading) {
    return (
      <div className={cn('space-y-4', className)}>
        {[1, 2, 3].map(i => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-4 w-[250px]" />
              <Skeleton className="h-4 w-[200px]" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <Alert variant="destructive" className={className}>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error Loading Accounts</AlertTitle>
        <AlertDescription>
          {error}
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={fetchAccounts}
          >
            Try Again
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Filters and Actions */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search accounts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={countryFilter} onValueChange={setCountryFilter}>
            <SelectTrigger className="w-[140px]">
              <Globe className="h-4 w-4 mr-1" />
              <SelectValue placeholder="Country" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Countries</SelectItem>
              {availableCountries.map(country => (
                <SelectItem key={country} value={country}>
                  {country}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-[140px]">
              <Filter className="h-4 w-4 mr-1" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="disabled">Disabled</SelectItem>
              <SelectItem value="partial">Partial</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <Button
          onClick={syncAccounts}
          disabled={isSyncing}
          variant="outline"
        >
          {isSyncing ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-2" />
          )}
          {isSyncing ? 'Syncing...' : 'Sync Accounts'}
        </Button>
      </div>

      {/* Account Summary */}
      {filteredAccounts.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Total Accounts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{filteredAccounts.length}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">Active Accounts</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {filteredAccounts.filter(a => a.status === 'active').length}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">With Errors</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                {filteredAccounts.filter(a => a.hasErrors).length}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Accounts List */}
      {filteredAccounts.length === 0 ? (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>No Accounts Found</AlertTitle>
          <AlertDescription>
            {searchQuery || countryFilter !== 'all' || statusFilter !== 'all'
              ? 'Try adjusting your filters or search query.'
              : 'No Amazon Advertising accounts are connected yet.'}
          </AlertDescription>
        </Alert>
      ) : (
        <div className="space-y-3">
          {filteredAccounts.map(account => {
            const isExpanded = expandedAccounts.has(account.id);
            const originalAccount = accounts.find(a => a.id === account.id);

            return (
              <Card key={account.id} className="overflow-hidden">
                <Collapsible open={isExpanded}>
                  <CollapsibleTrigger asChild>
                    <CardHeader
                      className="cursor-pointer hover:bg-muted/50 transition-colors"
                      onClick={() => toggleAccountExpansion(account.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <CardTitle className="flex items-center gap-2">
                            {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            {account.name}
                          </CardTitle>
                          <CardDescription className="flex items-center gap-4">
                            <span>ID: {account.amazonId}</span>
                            <span>•</span>
                            <span>{account.profileCount} Profile{account.profileCount !== 1 ? 's' : ''}</span>
                            <span>•</span>
                            <span>{account.countries.join(', ')}</span>
                          </CardDescription>
                        </div>
                        <div className="flex items-center gap-2">
                          {renderStatusBadge(account.status)}
                          {account.hasErrors && (
                            <Badge variant="outline" className="gap-1 border-yellow-500 text-yellow-700">
                              <AlertTriangle className="h-3 w-3" />
                              Errors in {account.errorCountries?.join(', ')}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>

                  <CollapsibleContent>
                    <CardContent className="pt-0">
                      <div className="space-y-4">
                        {/* Profile Details */}
                        {originalAccount?.alternateIds && originalAccount.alternateIds.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold mb-2">Profiles by Country</h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                              {originalAccount.alternateIds.map((profile, idx) => (
                                <div
                                  key={idx}
                                  className="p-2 border rounded-md bg-muted/30"
                                >
                                  <div className="flex items-center gap-2">
                                    <Badge variant="secondary">{profile.countryCode}</Badge>
                                    <span className="text-sm">Profile #{profile.profileId}</span>
                                  </div>
                                  <div className="text-xs text-muted-foreground mt-1">
                                    Entity: {profile.entityId}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Errors */}
                        {originalAccount?.metadata.errors && Object.keys(originalAccount.metadata.errors).length > 0 && (
                          <Alert variant="destructive">
                            <AlertTriangle className="h-4 w-4" />
                            <AlertTitle>Account Errors</AlertTitle>
                            <AlertDescription>
                              <div className="mt-2 space-y-1">
                                {Object.entries(originalAccount.metadata.errors).map(([country, errors]) => (
                                  <div key={country}>
                                    <span className="font-semibold">{country}:</span>
                                    {errors.map((error, idx) => (
                                      <div key={idx} className="ml-4 text-xs">
                                        • {error.errorMessage} ({error.errorCode})
                                      </div>
                                    ))}
                                  </div>
                                ))}
                              </div>
                            </AlertDescription>
                          </Alert>
                        )}

                        {/* Sync Info */}
                        <div className="flex justify-between items-center text-sm text-muted-foreground">
                          <span>
                            Last synced: {account.lastSync
                              ? new Date(account.lastSync).toLocaleString()
                              : 'Never'}
                          </span>
                          {onAccountSelect && (
                            <Button
                              size="sm"
                              onClick={() => originalAccount && onAccountSelect(originalAccount)}
                            >
                              Select Account
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </CollapsibleContent>
                </Collapsible>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AmazonAccountsList;