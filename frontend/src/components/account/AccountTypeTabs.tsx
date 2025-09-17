import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle, Shield, Database, BarChart3, ChevronLeft, Plus } from 'lucide-react';
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

interface TabActionButtonProps {
  accountType: AccountType;
  onClick: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  className?: string;
}

// Tab-specific action button component
const TabActionButton: React.FC<TabActionButtonProps> = ({
  accountType,
  onClick,
  isLoading = false,
  disabled = false,
  className,
}) => {
  const getButtonLabel = () => {
    switch (accountType) {
      case 'sponsored-ads':
        return 'Add Sponsored Ads';
      case 'dsp':
        return 'Add DSP Advertiser';
      case 'amc':
        return 'Add AMC Instance';
      default:
        return 'Add Account';
    }
  };

  const getLoadingLabel = () => {
    switch (accountType) {
      case 'sponsored-ads':
        return 'Adding Sponsored Ads...';
      case 'dsp':
        return 'Adding DSP Advertiser...';
      case 'amc':
        return 'Adding AMC Instance...';
      default:
        return 'Adding...';
    }
  };

  return (
    <Button
      variant="default"
      size="default"
      onClick={onClick}
      disabled={disabled || isLoading}
      className={cn(
        "gap-2 transition-all duration-200",
        isLoading && "opacity-70 cursor-wait",
        className
      )}
      aria-label={getButtonLabel()}
      aria-busy={isLoading}
      aria-disabled={disabled || isLoading}
    >
      <Plus
        className={cn(
          "h-4 w-4",
          isLoading && "animate-pulse"
        )}
        aria-hidden="true"
      />
      <span className="hidden sm:inline-block">
        {isLoading ? getLoadingLabel() : getButtonLabel()}
      </span>
      <span className="sm:hidden">
        Add
      </span>
    </Button>
  );
};

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
  const [isAddingSponsoredAds, setIsAddingSponsoredAds] = useState(false);
  const [isAddingDSP, setIsAddingDSP] = useState(false);
  const [isAddingAMC, setIsAddingAMC] = useState(false);
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
      await accountService.deleteAccount(accountId);
      toast({
        title: "Account deleted",
        description: "The account has been successfully deleted.",
      });
      // Refetch the current tab's data
      if (activeTab === 'sponsored-ads') sponsoredAdsQuery.refetch();
      else if (activeTab === 'dsp') dspQuery.refetch();
      else if (activeTab === 'amc') amcQuery.refetch();
    } catch (error) {
      toast({
        title: "Failed to delete",
        description: "Could not delete the account. Please try again.",
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

  const handleAddSponsoredAds = async () => {
    setIsAddingSponsoredAds(true);
    try {
      const result = await accountService.addSponsoredAdsAccounts();

      // Check if OAuth is required
      if (result.requires_auth && result.auth_url) {
        // Handle OAuth redirect
        accountService.handleOAuthRedirect(result.auth_url, async (authResult) => {
          if (authResult.success) {
            // OAuth successful, retry adding accounts
            try {
              const retryResult = await accountService.addSponsoredAdsAccounts();
              if (!retryResult.requires_auth) {
                toast({
                  title: "Success",
                  description: `Successfully added ${retryResult.accounts_added || 0} Sponsored Ads accounts`,
                });
                // Refetch data to update the display
                await sponsoredAdsQuery.refetch();
              }
            } catch (error) {
              toast({
                title: "Error",
                description: "Failed to add accounts after authorization. Please try again.",
                variant: "destructive",
              });
            }
          } else {
            toast({
              title: "Authorization Cancelled",
              description: "OAuth authorization was cancelled or failed.",
              variant: "destructive",
            });
          }
          setIsAddingSponsoredAds(false);
        });
      } else {
        // Accounts added successfully without OAuth
        toast({
          title: "Success",
          description: `Successfully added ${result.accounts_added || 0} Sponsored Ads accounts`,
        });
        // Refetch data to update the display
        await sponsoredAdsQuery.refetch();
        setIsAddingSponsoredAds(false);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add Sponsored Ads accounts. Please try again.",
        variant: "destructive",
      });
      setIsAddingSponsoredAds(false);
    }
  };

  const handleAddDSP = async () => {
    setIsAddingDSP(true);
    try {
      const result = await accountService.addDSPAdvertisers();

      // Check if OAuth is required
      if (result.requires_auth && result.auth_url) {
        // Handle OAuth redirect
        accountService.handleOAuthRedirect(result.auth_url, async (authResult) => {
          if (authResult.success) {
            // OAuth successful, retry adding advertisers
            try {
              const retryResult = await accountService.addDSPAdvertisers();
              if (!retryResult.requires_auth) {
                toast({
                  title: "Success",
                  description: `Successfully added ${retryResult.advertisers_added || 0} DSP advertisers`,
                });
                // Refetch data to update the display
                await dspQuery.refetch();
              }
            } catch (error) {
              toast({
                title: "Error",
                description: "Failed to add DSP advertisers after authorization. Please try again.",
                variant: "destructive",
              });
            }
          } else {
            toast({
              title: "Authorization Cancelled",
              description: "OAuth authorization was cancelled or failed.",
              variant: "destructive",
            });
          }
          setIsAddingDSP(false);
        });
      } else {
        // Advertisers added successfully without OAuth
        toast({
          title: "Success",
          description: `Successfully added ${result.advertisers_added || 0} DSP advertisers`,
        });
        // Refetch data to update the display
        await dspQuery.refetch();
        setIsAddingDSP(false);
      }
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message || "Failed to add DSP advertisers. Please try again.",
        variant: "destructive",
      });
      setIsAddingDSP(false);
    }
  };

  const handleAddAMC = async () => {
    setIsAddingAMC(true);
    try {
      // Note: AMC add functionality not yet implemented per spec
      toast({
        title: "Coming Soon",
        description: "AMC instance connection will be available in a future update.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to add AMC instances.",
        variant: "destructive",
      });
    } finally {
      setIsAddingAMC(false);
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
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium">Sponsored Ads Accounts</h3>
                <p className="text-sm text-muted-foreground">
                  Manage your Sponsored Products, Brands, and Display campaigns
                </p>
              </div>
              <TabActionButton
                accountType="sponsored-ads"
                onClick={handleAddSponsoredAds}
                isLoading={isAddingSponsoredAds || sponsoredAdsQuery.isRefetching}
                disabled={sponsoredAdsQuery.isLoading}
              />
            </div>
            {renderTabContent('sponsored-ads')}
          </div>
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
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-medium">DSP Advertisers</h3>
                  <p className="text-sm text-muted-foreground">
                    Manage your demand-side platform advertisers and campaigns
                  </p>
                </div>
                <TabActionButton
                  accountType="dsp"
                  onClick={handleAddDSP}
                  isLoading={isAddingDSP || dspQuery.isRefetching}
                  disabled={dspQuery.isLoading}
                />
              </div>
              {renderTabContent('dsp')}
            </div>
          )}
        </TabsContent>

        <TabsContent
          value="amc"
          className="mt-4 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          data-testid="amc-content"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-medium">AMC Instances</h3>
                <p className="text-sm text-muted-foreground">
                  Manage your Amazon Marketing Cloud instances and data analytics
                </p>
              </div>
              <TabActionButton
                accountType="amc"
                onClick={handleAddAMC}
                isLoading={isAddingAMC || amcQuery.isRefetching}
                disabled={amcQuery.isLoading}
              />
            </div>
            {renderTabContent('amc')}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
};