import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Settings,
  RefreshCw,
  Search,
  Filter,
  Grid3x3,
  List,
  AlertCircle,
  CheckCircle,
  XCircle,
  CircleOff,
  ExternalLink,
  Download
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ResponsiveBreadcrumbNav } from '@/components/ui/breadcrumb';
import { AccountCard, AccountCardSkeleton } from './AccountCard';
import { AccountDetailsModal } from './AccountDetailsModal';
import { ReauthorizationFlow } from './ReauthorizationFlow';
import { AccountSettingsPanel } from './AccountSettingsPanel';
import { Account, AccountStatus, AccountSettings } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface AccountManagementPageProps {
  onAddAccount?: () => void;
  className?: string;
}

export const AccountManagementPage: React.FC<AccountManagementPageProps> = ({
  onAddAccount,
  className,
}) => {
  const { toast } = useToast();
  
  // State management
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [filteredAccounts, setFilteredAccounts] = useState<Account[]>([]);
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<AccountStatus | 'all'>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [activeTab, setActiveTab] = useState('accounts');
  
  // Modal states
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showReauthModal, setShowReauthModal] = useState(false);
  const [reauthAccount, setReauthAccount] = useState<Account | null>(null);

  // Load accounts and settings on mount
  useEffect(() => {
    loadData();
  }, []);

  // Apply filters when search or status filter changes
  useEffect(() => {
    filterAccounts();
  }, [accounts, searchQuery, statusFilter]);

  // Update view mode based on settings
  useEffect(() => {
    if (settings) {
      setViewMode(settings.dashboardLayout);
    }
  }, [settings]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load accounts and settings in parallel
      const [accountsResponse, settingsResponse] = await Promise.all([
        accountService.getAccounts(),
        accountService.getSettings().catch(() => null),
      ]);

      // Update account status based on token expiry
      const updatedAccounts = accountsResponse.accounts.map((account: Account) => ({
        ...account,
        status: accountService.getAccountStatus(account),
      }));

      setAccounts(updatedAccounts);
      
      if (settingsResponse) {
        setSettings(settingsResponse.settings);
      }
    } catch (error) {
      console.error('Failed to load accounts:', error);
      toast({
        title: "Failed to load accounts",
        description: "Could not load your accounts. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const filterAccounts = () => {
    let filtered = [...accounts];

    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(account =>
        account.accountName?.toLowerCase().includes(query) ||
        account.accountId?.toLowerCase().includes(query) ||
        (account.marketplace?.name?.toLowerCase().includes(query) ?? false) ||
        (account.marketplace?.countryCode?.toLowerCase().includes(query) ?? false)
      );
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(account => account.status === statusFilter);
    }

    setFilteredAccounts(filtered);
  };

  const handleSyncFromAmazon = async () => {
    setIsRefreshing(true);
    try {
      const result = await accountService.syncAmazonAccounts();
      
      toast({
        title: "Accounts synced",
        description: `Successfully synced ${result.accounts?.length || 0} accounts from Amazon.`,
      });
      
      // Reload to display the newly synced accounts
      await loadData();
    } catch (error) {
      console.error('Failed to sync accounts from Amazon:', error);
      toast({
        title: "Sync failed",
        description: "Failed to sync accounts from Amazon. Please check your connection.",
        variant: "destructive",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    const activeAccounts = accounts.filter(acc =>
      acc.status === 'active'
    );

    let successCount = 0;
    let failCount = 0;

    for (const account of activeAccounts) {
      try {
        await accountService.refreshAccountToken(account.id);
        successCount++;
      } catch (error) {
        failCount++;
        console.error(`Failed to refresh account ${account.id}:`, error);
      }
    }

    if (successCount > 0) {
      toast({
        title: "Tokens refreshed",
        description: `Successfully refreshed ${successCount} account${successCount > 1 ? 's' : ''}.`,
      });
    }

    if (failCount > 0) {
      toast({
        title: "Some refreshes failed",
        description: `Failed to refresh ${failCount} account${failCount > 1 ? 's' : ''}.`,
        variant: "destructive",
      });
    }

    setIsRefreshing(false);
    await loadData(); // Reload to get updated data
  };

  const handleRefreshAccount = async (accountId: string) => {
    try {
      await accountService.refreshAccountToken(accountId);
      await loadData(); // Reload to get updated data
    } catch (error) {
      throw error; // Let the AccountCard handle the error
    }
  };

  const handleDisconnectAccount = async (accountId: string) => {
    try {
      await accountService.disconnectAccount(accountId);
      
      toast({
        title: "Account disconnected",
        description: "The account has been successfully disconnected.",
      });

      // Remove account from list
      setAccounts(prev => prev.filter(acc => acc.id !== accountId));
    } catch (error) {
      console.error('Failed to disconnect account:', error);
      toast({
        title: "Failed to disconnect",
        description: "Could not disconnect the account. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReauthorize = (accountId: string) => {
    const account = accounts.find(acc => acc.id === accountId);
    if (account) {
      setReauthAccount(account);
      setShowReauthModal(true);
    }
  };

  const handleSetDefaultAccount = async (accountId: string) => {
    if (!settings) return;

    try {
      await accountService.updateSettings({
        defaultAccountId: accountId,
      });

      // Update local state
      setAccounts(prev => prev.map(acc => ({
        ...acc,
        isDefault: acc.id === accountId,
      })));

      toast({
        title: "Default account updated",
        description: "Your default account has been changed.",
      });
    } catch (error) {
      console.error('Failed to set default account:', error);
      toast({
        title: "Failed to update",
        description: "Could not set default account. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleViewDetails = (account: Account) => {
    setSelectedAccount(account);
    setShowDetailsModal(true);
  };

  const getStatusCounts = () => {
    const counts = {
      active: 0,
      error: 0,
      disconnected: 0,
    };

    accounts.forEach(account => {
      const status = account.status as AccountStatus;
      if (status in counts) {
        counts[status]++;
      }
    });

    return counts;
  };

  const statusCounts = getStatusCounts();

  return (
    <div className={cn("space-y-6", className)}>
      {/* Breadcrumb Navigation */}
      <ResponsiveBreadcrumbNav />

      {/* Page Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Account Management</h1>
          <p className="text-muted-foreground">
            Manage your Amazon DSP accounts and connection settings
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button
            onClick={handleSyncFromAmazon}
            disabled={isRefreshing}
            variant="default"
          >
            <Download className={cn("h-4 w-4 mr-2", isRefreshing && "animate-pulse")} />
            Sync from Amazon
          </Button>
          
          <Button
            variant="outline"
            onClick={handleRefreshAll}
            disabled={isRefreshing || accounts.length === 0}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
            Refresh Tokens
          </Button>
          
          {onAddAccount && (
            <Button onClick={onAddAccount} variant="outline">
              <Plus className="h-4 w-4 mr-2" />
              Add Account
            </Button>
          )}
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <div className="flex items-center gap-3 p-4 border rounded-lg bg-card">
          <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-full">
            <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">Active</p>
            <p className="text-2xl font-bold">{statusCounts.active}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-4 border rounded-lg bg-card">
          <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-full">
            <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">Needs Attention</p>
            <p className="text-2xl font-bold">{statusCounts.error}</p>
          </div>
        </div>

        <div className="flex items-center gap-3 p-4 border rounded-lg bg-card">
          <div className="p-2 bg-gray-100 dark:bg-gray-900/30 rounded-full">
            <CircleOff className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm text-muted-foreground">Disconnected</p>
            <p className="text-2xl font-bold">{statusCounts.disconnected}</p>
          </div>
        </div>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-auto grid-cols-2">
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        {/* Accounts Tab */}
        <TabsContent value="accounts" className="space-y-4">
          {/* Filters and Controls */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-1 gap-2">
              <div className="relative flex-1 max-w-sm">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search accounts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              
              <Select value={statusFilter} onValueChange={(value: any) => setStatusFilter(value)}>
                <SelectTrigger className="w-[140px]">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="error">Needs Attention</SelectItem>
                  <SelectItem value="disconnected">Disconnected</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2">
              <Button
                variant={viewMode === 'grid' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('grid')}
              >
                <Grid3x3 className="h-4 w-4" />
              </Button>
              <Button
                variant={viewMode === 'list' ? 'default' : 'outline'}
                size="icon"
                onClick={() => setViewMode('list')}
              >
                <List className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Accounts Display */}
          {isLoading ? (
            <div className={cn(
              viewMode === 'grid'
                ? "grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6"
                : "space-y-4"
            )}>
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <AccountCardSkeleton key={i} />
              ))}
            </div>
          ) : filteredAccounts.length === 0 ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>No accounts found</AlertTitle>
              <AlertDescription>
                {searchQuery || statusFilter !== 'all' 
                  ? "No accounts match your current filters. Try adjusting your search or filters."
                  : "You haven't connected any Amazon DSP accounts yet. Click 'Add Account' to get started."}
              </AlertDescription>
            </Alert>
          ) : (
            <ScrollArea className="h-[600px] pr-4">
              <div className={cn(
                viewMode === 'grid'
                  ? "grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6"
                  : "space-y-4"
              )}>
                {filteredAccounts.map((account) => (
                  <AccountCard
                    key={account.id}
                    account={account}
                    onViewDetails={handleViewDetails}
                    onDisconnect={handleDisconnectAccount}
                    onReauthorize={handleReauthorize}
                    onRefresh={handleRefreshAccount}
                    onSetDefault={settings ? handleSetDefaultAccount : undefined}
                    isRefreshing={isRefreshing}
                  />
                ))}
              </div>
            </ScrollArea>
          )}

          {/* Quick Actions Alert */}
          {statusCounts.error > 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Action Required</AlertTitle>
              <AlertDescription>
                You have {statusCounts.error} account{statusCounts.error > 1 ? 's' : ''} that need attention.
                Auto-refresh has failed for these accounts. Please reauthorize to restore access.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <AccountSettingsPanel
            accounts={accounts}
            onSettingsUpdate={(updatedSettings) => {
              setSettings(updatedSettings);
              // Update view mode if dashboard layout changed
              if (updatedSettings.dashboardLayout !== viewMode) {
                setViewMode(updatedSettings.dashboardLayout);
              }
            }}
          />
        </TabsContent>
      </Tabs>

      {/* Modals */}
      <AccountDetailsModal
        account={selectedAccount}
        open={showDetailsModal}
        onClose={() => {
          setShowDetailsModal(false);
          setSelectedAccount(null);
        }}
        onDisconnect={handleDisconnectAccount}
        onRefresh={handleRefreshAccount}
      />

      <ReauthorizationFlow
        account={reauthAccount}
        open={showReauthModal}
        onClose={() => {
          setShowReauthModal(false);
          setReauthAccount(null);
        }}
        onSuccess={() => {
          loadData(); // Reload accounts after successful reauth
        }}
      />
    </div>
  );
};