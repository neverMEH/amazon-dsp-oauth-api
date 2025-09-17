import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle, Shield, Database, BarChart3, ChevronLeft } from 'lucide-react';
import { AccountTypeTable } from './AccountTypeTable';
import { DSPSeatsTab } from './DSPSeatsTab';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type AccountType = 'sponsored-ads' | 'dsp' | 'amc';

interface AccountTypeTabsProps {
  className?: string;
  onAccountSelect?: (account: any) => void;
  onAccountAction?: (action: string, account: any) => void;
}

export const AccountTypeTabs: React.FC<AccountTypeTabsProps> = ({
  className,
  onAccountSelect,
  onAccountAction,
}) => {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<AccountType>(() => {
    const typeParam = searchParams.get('type') as AccountType;
    return ['sponsored-ads', 'dsp', 'amc'].includes(typeParam) ? typeParam : 'sponsored-ads';
  });
  const [selectedDSPAccount, setSelectedDSPAccount] = useState<any>(null);
  const urlUpdateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Query for Sponsored Ads accounts
  const sponsoredAdsQuery = useQuery({
    queryKey: ['accounts', 'sponsored-ads'],
    queryFn: () => accountService.getSponsoredAdsAccounts(),
    enabled: activeTab === 'sponsored-ads',
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });

  // Query for DSP accounts
  const dspQuery = useQuery({
    queryKey: ['accounts', 'dsp'],
    queryFn: () => accountService.getDSPAccounts(),
    enabled: activeTab === 'dsp',
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on 403 permission errors
      if (error?.response?.status === 403) return false;
      return failureCount < 3;
    },
  });

  // Query for AMC accounts
  const amcQuery = useQuery({
    queryKey: ['accounts', 'amc'],
    queryFn: () => accountService.getAMCAccounts(),
    enabled: activeTab === 'amc',
    staleTime: 5 * 60 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on 403 permission errors
      if (error?.response?.status === 403) return false;
      return failureCount < 3;
    },
  });

  // Debounced URL update to prevent loops
  const updateUrl = useCallback((tabType: AccountType) => {
    if (urlUpdateTimeoutRef.current) {
      clearTimeout(urlUpdateTimeoutRef.current);
    }
    urlUpdateTimeoutRef.current = setTimeout(() => {
      setSearchParams({ type: tabType }, { replace: true });
    }, 100);
  }, [setSearchParams]);

  // Update URL when tab changes (debounced)
  useEffect(() => {
    const currentType = searchParams.get('type') as AccountType;
    if (currentType !== activeTab) {
      updateUrl(activeTab);
    }
  }, [activeTab, updateUrl, searchParams]);

  // Update active tab when URL changes (only if different)
  useEffect(() => {
    const typeParam = searchParams.get('type') as AccountType;
    if (['sponsored-ads', 'dsp', 'amc'].includes(typeParam) && typeParam !== activeTab) {
      setActiveTab(typeParam);
    }
  }, [searchParams]); // Removed activeTab dependency to prevent loop

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (urlUpdateTimeoutRef.current) {
        clearTimeout(urlUpdateTimeoutRef.current);
      }
    };
  }, []);

  // Get account counts for badges
  const sponsoredAdsCount = (sponsoredAdsQuery.data as any)?.totalCount || (sponsoredAdsQuery.data as any)?.accounts?.length || 0;
  const dspCount = (dspQuery.data as any)?.totalCount || (dspQuery.data as any)?.accounts?.length || 0;
  const amcCount = (amcQuery.data as any)?.totalCount || (amcQuery.data as any)?.instances?.length || 0;

  const handleTabChange = (value: string) => {
    setActiveTab(value as AccountType);
  };

  const handleViewDetails = (account: any) => {
    if (activeTab === 'dsp' && account.amazon_account_id) {
      // For DSP accounts, show the seats tab instead of details modal
      setSelectedDSPAccount(account);
    } else if (onAccountSelect) {
      onAccountSelect(account);
    }
  };

  const handleDisconnect = async (accountId: string) => {
    try {
      await accountService.disconnectAccount(accountId);
      toast({
        title: "Account disconnected",
        description: "The account has been successfully disconnected.",
      });
      // Refetch the current tab's data
      if (activeTab === 'sponsored-ads') sponsoredAdsQuery.refetch();
      else if (activeTab === 'dsp') dspQuery.refetch();
      else if (activeTab === 'amc') amcQuery.refetch();
    } catch (error) {
      toast({
        title: "Failed to disconnect",
        description: "Could not disconnect the account. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleRefresh = async (accountId: string) => {
    try {
      await accountService.refreshAccountToken(accountId);
      toast({
        title: "Token refreshed",
        description: "Account token has been successfully refreshed.",
      });
      // Refetch the current tab's data
      if (activeTab === 'sponsored-ads') sponsoredAdsQuery.refetch();
      else if (activeTab === 'dsp') dspQuery.refetch();
      else if (activeTab === 'amc') amcQuery.refetch();
    } catch (error) {
      toast({
        title: "Refresh failed",
        description: "Could not refresh the account token. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleReauthorize = (accountId: string) => {
    if (onAccountAction) {
      onAccountAction('reauthorize', { id: accountId });
    }
  };

  const renderTabContent = (type: AccountType) => {
    let query, accounts, error, isLoading;

    switch (type) {
      case 'sponsored-ads':
        query = sponsoredAdsQuery;
        accounts = (query.data as any)?.accounts || [];
        error = query.error;
        isLoading = query.isLoading;
        break;
      case 'dsp':
        query = dspQuery;
        accounts = (query.data as any)?.accounts || [];
        error = query.error;
        isLoading = query.isLoading;
        break;
      case 'amc':
        query = amcQuery;
        accounts = (query.data as any)?.instances || [];
        error = query.error;
        isLoading = query.isLoading;
        break;
    }

    // Handle 403 permission errors
    if ((error as any)?.response?.status === 403) {
      return (
        <Alert className="border-2 border-dashed">
          <Shield className="h-4 w-4" />
          <AlertTitle>Access Restricted</AlertTitle>
          <AlertDescription>
            {type === 'dsp' ? (
              <>You don't have access to DSP accounts. Contact your administrator to enable DSP access for your account.</>
            ) : (
              <>You don't have access to AMC instances. AMC requires additional permissions. Please contact support.</>
            )}
          </AlertDescription>
        </Alert>
      );
    }

    // Handle other errors
    if (error && !isLoading) {
      return (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Failed to load accounts</AlertTitle>
          <AlertDescription>
            There was an error loading your {type === 'sponsored-ads' ? 'Sponsored Ads' : type.toUpperCase()} accounts.
            Please try refreshing the page.
          </AlertDescription>
        </Alert>
      );
    }

    return (
      <AccountTypeTable
        accountType={type}
        accounts={accounts}
        isLoading={isLoading}
        onViewDetails={handleViewDetails}
        onDisconnect={handleDisconnect}
        onRefresh={handleRefresh}
        onReauthorize={handleReauthorize}
      />
    );
  };

  return (
    <div className={cn("space-y-4", className)}>
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="inline-flex h-10 items-center justify-center rounded-md bg-muted p-1 text-muted-foreground overflow-x-auto">
          <TabsTrigger
            value="sponsored-ads"
            className="inline-flex items-center gap-2 justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
          >
            <BarChart3 className="h-4 w-4" />
            Sponsored Ads
            {sponsoredAdsCount > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                {sponsoredAdsCount}
              </Badge>
            )}
          </TabsTrigger>

          <TabsTrigger
            value="dsp"
            className="inline-flex items-center gap-2 justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
          >
            <Database className="h-4 w-4" />
            DSP
            {dspCount > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                {dspCount}
              </Badge>
            )}
            {(dspQuery.error as any)?.response?.status === 403 && (
              <Badge variant="outline" className="ml-1 h-5 px-1.5">
                <Shield className="h-3 w-3" />
              </Badge>
            )}
          </TabsTrigger>

          <TabsTrigger
            value="amc"
            className="inline-flex items-center gap-2 justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm"
          >
            <Shield className="h-4 w-4" />
            AMC
            {amcCount > 0 && (
              <Badge variant="secondary" className="ml-1 h-5 px-1.5">
                {amcCount}
              </Badge>
            )}
            {(amcQuery.error as any)?.response?.status === 403 && (
              <Badge variant="outline" className="ml-1 h-5 px-1.5">
                <Shield className="h-3 w-3" />
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="sponsored-ads"
          className="mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          data-testid="sponsored-ads-content"
        >
          {renderTabContent('sponsored-ads')}
        </TabsContent>

        <TabsContent
          value="dsp"
          className="mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          data-testid="dsp-content"
        >
          {selectedDSPAccount ? (
            <div className="space-y-4">
              <div className="flex items-center gap-4 pb-4 border-b">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedDSPAccount(null)}
                  className="gap-2"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Back to DSP Accounts
                </Button>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">
                    {selectedDSPAccount.account_name || 'DSP Account'}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Advertiser ID: {selectedDSPAccount.amazon_account_id}
                  </p>
                </div>
              </div>
              <DSPSeatsTab advertiserId={selectedDSPAccount.amazon_account_id} />
            </div>
          ) : (
            renderTabContent('dsp')
          )}
        </TabsContent>

        <TabsContent
          value="amc"
          className="mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          data-testid="amc-content"
        >
          {renderTabContent('amc')}
        </TabsContent>
      </Tabs>
    </div>
  );
};