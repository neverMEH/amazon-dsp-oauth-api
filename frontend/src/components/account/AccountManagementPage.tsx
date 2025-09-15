import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  Settings,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  CircleOff,
  ExternalLink,
  Download,
  Shield
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { AccountTypeTabs } from './AccountTypeTabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { ResponsiveBreadcrumbNav } from '@/components/ui/breadcrumb';
import { AccountDetailsModal } from './AccountDetailsModal';
import { ReauthorizationFlow } from './ReauthorizationFlow';
import { Account, AccountStatus } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

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
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  
  // Modal states
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showReauthModal, setShowReauthModal] = useState(false);
  const [reauthAccount, setReauthAccount] = useState<Account | null>(null);

  // Load accounts and settings on mount
  useEffect(() => {
    loadData();
  }, []);



  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load accounts and settings in parallel
      const accountsResponse = await accountService.getAccounts();

      // Update account status based on token expiry
      const updatedAccounts = accountsResponse.accounts.map((account: Account) => ({
        ...account,
        status: accountService.getAccountStatus(account),
      }));

      setAccounts(updatedAccounts);
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
            Manage your neverMEH accounts and connection settings
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
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-green-50 to-green-100/50 dark:from-green-950/20 dark:to-green-900/10 p-4 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-green-500/10 dark:bg-green-500/20 rounded-xl">
              <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-green-700 dark:text-green-400 uppercase tracking-wide">Active</p>
              <p className="text-3xl font-bold text-green-900 dark:text-green-100">{statusCounts.active}</p>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 h-24 w-24 rounded-full bg-green-200/20 dark:bg-green-400/10" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
          className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-red-50 to-red-100/50 dark:from-red-950/20 dark:to-red-900/10 p-4 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-500/10 dark:bg-red-500/20 rounded-xl">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-red-700 dark:text-red-400 uppercase tracking-wide">Needs Attention</p>
              <p className="text-3xl font-bold text-red-900 dark:text-red-100">{statusCounts.error}</p>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 h-24 w-24 rounded-full bg-red-200/20 dark:bg-red-400/10" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.3 }}
          className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-gray-50 to-gray-100/50 dark:from-gray-950/20 dark:to-gray-900/10 p-4 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gray-500/10 dark:bg-gray-500/20 rounded-xl">
              <CircleOff className="h-5 w-5 text-gray-600 dark:text-gray-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-gray-700 dark:text-gray-400 uppercase tracking-wide">Disconnected</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-gray-100">{statusCounts.disconnected}</p>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 h-24 w-24 rounded-full bg-gray-200/20 dark:bg-gray-400/10" />
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.4 }}
          className="relative overflow-hidden rounded-xl border bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-950/20 dark:to-blue-900/10 p-4 shadow-sm hover:shadow-md transition-shadow"
        >
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-500/10 dark:bg-blue-500/20 rounded-xl">
              <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <p className="text-xs font-medium text-blue-700 dark:text-blue-400 uppercase tracking-wide">Total Accounts</p>
              <p className="text-3xl font-bold text-blue-900 dark:text-blue-100">{accounts.length}</p>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 h-24 w-24 rounded-full bg-blue-200/20 dark:bg-blue-400/10" />
        </motion.div>
      </div>

      {/* Account Type Tabs */}
      <AccountTypeTabs
        className="w-full"
        onAccountSelect={handleViewDetails}
        onAccountAction={(action, account) => {
          if (action === 'reauthorize') {
            handleReauthorize(account.id);
          }
        }}
      />

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