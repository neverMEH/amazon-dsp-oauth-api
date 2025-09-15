import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  User,
  Globe,
  Calendar,
  Clock,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Unlink,
  Info,
  Hash,
  MapPin,
  DollarSign,
  Building,
  HelpCircle,
  ExternalLink,
  BarChart,
  ToggleLeft,
  ToggleRight,
  Copy
} from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Account, RefreshHistory, AccountDetailsResponse } from '@/types/account';
import { AccountHealthIndicator } from './AccountHealthIndicator';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface AccountDetailsModalProps {
  account: Account | null;
  open: boolean;
  onClose: () => void;
  onDisconnect?: (accountId: string) => void;
  onRefresh?: (accountId: string) => Promise<void>;
}

export const AccountDetailsModal: React.FC<AccountDetailsModalProps> = ({
  account,
  open,
  onClose,
  onDisconnect,
  onRefresh,
}) => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [refreshHistory, setRefreshHistory] = useState<RefreshHistory[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);

  useEffect(() => {
    if (account && open) {
      loadAccountDetails();
    }
  }, [account, open]);

  const loadAccountDetails = async () => {
    if (!account) return;
    
    setIsLoading(true);
    try {
      const accountDetails = await accountService.getAccountDetails(account.id);
      // For now, we don't have refresh history endpoint, so just set empty array
      setRefreshHistory([]);
    } catch (error) {
      console.error('Failed to load account details:', error);
      toast({
        title: "Failed to load details",
        description: "Could not load account details. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (!account || !onRefresh) return;
    
    setIsRefreshing(true);
    try {
      await onRefresh(account.id);
      toast({
        title: "Token refreshed",
        description: "Account token has been successfully refreshed.",
      });
      // Reload details to get updated info
      await loadAccountDetails();
    } catch (error) {
      toast({
        title: "Refresh failed",
        description: "Failed to refresh token. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleDisconnect = () => {
    if (!account || !onDisconnect) return;
    
    onDisconnect(account.id);
    setShowDisconnectConfirm(false);
    onClose();
    
    toast({
      title: "Account disconnected",
      description: `${account.accountName} has been disconnected.`,
    });
  };

  if (!account) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl w-[90vw] max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="text-xl font-semibold flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <User className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1">
              <span>{account.accountName || 'Unknown Account'}</span>
              <Badge variant="outline" className="ml-3 font-normal">
                {account.accountType || 'advertising'}
              </Badge>
            </div>
          </DialogTitle>
          <DialogDescription className="flex items-center gap-4 text-sm mt-2">
            <span className="inline-flex items-center gap-1.5">
              <Hash className="h-3.5 w-3.5 text-muted-foreground" />
              <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                {account.accountId || 'N/A'}
              </code>
            </span>
            {account.metadata?.region && (
              <span className="inline-flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs">{account.metadata.region}</span>
              </span>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col">
          {/* Status Alert */}
          {account.status === 'error' && (
            <Alert variant="destructive" className="mb-4 flex-shrink-0">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Needs Attention</AlertTitle>
              <AlertDescription>
                Auto-refresh has failed for this account. Please re-authorize to restore automatic token management.
              </AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="overview" className="flex-1 flex flex-col overflow-hidden">
            <TabsList className="grid w-full grid-cols-3 flex-shrink-0">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="history">Refresh History</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="flex-1 overflow-auto mt-6 space-y-6">
              <ScrollArea className="h-full pr-4">
                <div className="space-y-6">
                  {/* Account Information Grid */}
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                    {/* Account Status */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-muted-foreground">Status</label>
                      <AccountHealthIndicator
                        status={account.status}
                        expiresAt={account.tokenExpiresAt}
                        showLabel={true}
                        size="md"
                        isRefreshing={isRefreshing}
                      />
                    </div>

                    {/* Default Account */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-muted-foreground">Default Account</label>
                      <div>
                        <Badge
                          variant={account.isDefault ? "default" : "secondary"}
                          className="font-medium"
                        >
                          {account.isDefault ? "Default" : "Secondary"}
                        </Badge>
                      </div>
                    </div>

                    {/* Region */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        <MapPin className="h-3.5 w-3.5" />
                        Region
                      </label>
                      <p className="text-sm font-medium">
                        {account.marketplace?.region || account.metadata?.region || 'Unknown'}
                      </p>
                    </div>

                    {/* Last Refresh */}
                    {account.lastRefreshTime && (
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                          <RefreshCw className="h-3.5 w-3.5" />
                          Last Refresh
                        </label>
                        <p className="text-sm font-medium">
                          {new Date(account.lastRefreshTime).toLocaleString()}
                        </p>
                      </div>
                    )}

                    {/* Token Expires */}
                    {account.tokenExpiresAt && (
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          Token Expires
                        </label>
                        <p className="text-sm font-medium">
                          {new Date(account.tokenExpiresAt).toLocaleString()}
                        </p>
                      </div>
                    )}

                    {/* Connected Since */}
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        Connected Since
                      </label>
                      <p className="text-sm font-medium">
                        {new Date(account.createdAt).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  {/* Marketplace Details Section */}
                  <div className="space-y-4">
                    <Separator />
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h3 className="text-base font-semibold">Marketplace Details</h3>
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-sm">
                                <p className="text-sm">
                                  Each marketplace has unique IDs. Use the appropriate Profile ID when making API calls to a specific marketplace.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        </div>
                        <Badge variant="secondary" className="text-xs">
                          {account.metadata?.alternate_ids?.length ||
                           account.metadata?.country_codes?.length || 1} Marketplace(s)
                        </Badge>
                      </div>

                      <div className="rounded-lg border bg-card">
                        <Table>
                          <TableHeader>
                            <TableRow className="hover:bg-transparent">
                              <TableHead className="w-[140px] font-semibold">Marketplace</TableHead>
                              <TableHead className="font-semibold">Profile ID</TableHead>
                              <TableHead className="font-semibold">Entity ID</TableHead>
                              <TableHead className="w-[120px] text-right font-semibold">Actions</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {account.metadata?.alternate_ids?.length > 0 ? (
                              account.metadata.alternate_ids.map((altId: any, index: number) => (
                                <TableRow key={altId.countryCode} className="group">
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <Badge className="font-medium">
                                        {altId.countryCode}
                                      </Badge>
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    <div className="flex items-center gap-2">
                                      <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                        {altId.profileId || 'N/A'}
                                      </code>
                                      {altId.profileId && (
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                                                onClick={() => {
                                                  navigator.clipboard.writeText(altId.profileId);
                                                  toast({
                                                    description: "Profile ID copied to clipboard",
                                                  });
                                                }}
                                              >
                                                <Copy className="h-3.5 w-3.5" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>Copy Profile ID</TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      )}
                                    </div>
                                  </TableCell>
                                  <TableCell>
                                    <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                      {altId.entityId || 'N/A'}
                                    </code>
                                  </TableCell>
                                  <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                      <TooltipProvider>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <Button
                                              variant="ghost"
                                              size="icon"
                                              className="h-8 w-8"
                                              disabled
                                            >
                                              <ExternalLink className="h-4 w-4" />
                                            </Button>
                                          </TooltipTrigger>
                                          <TooltipContent>View in Amazon Ads (Coming Soon)</TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    </div>
                                  </TableCell>
                                </TableRow>
                              ))
                            ) : account.metadata?.country_codes?.length > 0 ? (
                              // If we have country_codes but no alternate_ids, show them in a single row
                              <TableRow className="group">
                                <TableCell>
                                  <div className="flex flex-wrap gap-1">
                                    {account.metadata.country_codes.map((code: string) => (
                                      <Badge key={code} className="font-medium">
                                        {code}
                                      </Badge>
                                    ))}
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                      {account.profileDetails?.profileId || account.accountId || 'N/A'}
                                    </code>
                                    <span className="text-xs text-muted-foreground">(Shared)</span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                      {account.accountId || 'N/A'}
                                    </code>
                                    <span className="text-xs text-muted-foreground">(Shared)</span>
                                  </div>
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-1">
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8"
                                            disabled
                                          >
                                            <ExternalLink className="h-4 w-4" />
                                          </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>View in Amazon Ads (Coming Soon)</TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  </div>
                                </TableCell>
                              </TableRow>
                            ) : (
                              <TableRow className="group">
                                <TableCell>
                                  <Badge className="font-medium">
                                    {account.marketplace?.countryCode || 'Default'}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                    {account.profileDetails?.profileId || 'N/A'}
                                  </code>
                                </TableCell>
                                <TableCell>
                                  <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                    {account.accountId || 'N/A'}
                                  </code>
                                </TableCell>
                                <TableCell className="text-right">
                                  <div className="flex items-center justify-end gap-1">
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8"
                                            disabled
                                          >
                                            <ExternalLink className="h-4 w-4" />
                                          </Button>
                                        </TooltipTrigger>
                                        <TooltipContent>View in Amazon Ads (Coming Soon)</TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  </div>
                                </TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </div>
                  </div>
                </div>
              </ScrollArea>
            </TabsContent>

            <TabsContent value="profile" className="flex-1 overflow-auto mt-6">
              <ScrollArea className="h-full pr-4">
                {account.profileDetails ? (
                  <div className="space-y-6">
                    {/* Profile Information */}
                    <div>
                      <h3 className="text-base font-semibold mb-4">Profile Information</h3>
                      <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                            <Hash className="h-3.5 w-3.5" />
                            Profile ID
                          </label>
                          <div>
                            <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm font-medium">
                              {account.profileDetails.profileId}
                            </code>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground">Profile Name</label>
                          <p className="text-sm font-medium">{account.profileDetails.profileName}</p>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                            <Building className="h-3.5 w-3.5" />
                            Profile Type
                          </label>
                          <div>
                            <Badge variant="default" className="capitalize font-medium">
                              {account.profileDetails.profileType}
                            </Badge>
                          </div>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                            <DollarSign className="h-3.5 w-3.5" />
                            Currency
                          </label>
                          <p className="text-sm font-medium">{account.profileDetails.currency}</p>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                            <MapPin className="h-3.5 w-3.5" />
                            Country
                          </label>
                          <p className="text-sm font-medium">{account.profileDetails.country}</p>
                        </div>

                        <div className="space-y-2">
                          <label className="text-sm font-medium text-muted-foreground flex items-center gap-1.5">
                            <Clock className="h-3.5 w-3.5" />
                            Timezone
                          </label>
                          <p className="text-sm font-medium">{account.profileDetails.timezone}</p>
                        </div>
                      </div>
                    </div>

                    {/* Marketplace Management Table */}
                    {(account.metadata?.alternate_ids?.length > 0 || account.metadata?.country_codes?.length > 0) && (
                      <div className="space-y-4">
                        <Separator />
                        <div>
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                              <h3 className="text-base font-semibold">Marketplace Management</h3>
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent side="right" className="max-w-sm">
                                    <p className="text-sm">
                                      Manage each marketplace individually. Toggle sync to enable/disable data collection
                                      for specific marketplaces.
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                            <Badge variant="secondary" className="text-xs">
                              {account.metadata?.alternate_ids?.length ||
                               account.metadata?.country_codes?.length} Active
                            </Badge>
                          </div>

                          <div className="rounded-lg border bg-card">
                            <Table>
                              <TableHeader>
                                <TableRow className="hover:bg-transparent">
                                  <TableHead className="w-[140px] font-semibold">Marketplace</TableHead>
                                  <TableHead className="font-semibold">Profile ID</TableHead>
                                  <TableHead className="font-semibold">Entity ID</TableHead>
                                  <TableHead className="w-[100px] text-center font-semibold">Sync</TableHead>
                                  <TableHead className="w-[120px] text-right font-semibold">Actions</TableHead>
                                </TableRow>
                              </TableHeader>
                            <TableBody>
                              {account.metadata?.alternate_ids?.length > 0 ? (
                                account.metadata.alternate_ids.map((altId: any) => (
                                  <TableRow key={altId.countryCode} className="group">
                                    <TableCell>
                                      <Badge className="font-medium">
                                        {altId.countryCode}
                                      </Badge>
                                    </TableCell>
                                    <TableCell>
                                      <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                        {altId.profileId || 'N/A'}
                                      </code>
                                    </TableCell>
                                    <TableCell>
                                      <code className="relative rounded bg-muted px-2 py-1 font-mono text-sm">
                                        {altId.entityId || 'N/A'}
                                      </code>
                                    </TableCell>
                                    <TableCell className="text-center">
                                      <Switch
                                        defaultChecked={true}
                                        disabled
                                        aria-label={`Sync ${altId.countryCode} marketplace`}
                                      />
                                    </TableCell>
                                    <TableCell className="text-right">
                                      <div className="flex items-center justify-end gap-1">
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8"
                                                disabled
                                              >
                                                <BarChart className="h-4 w-4" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>View Dashboard (Coming Soon)</TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8"
                                                disabled
                                              >
                                                <ExternalLink className="h-4 w-4" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>View Campaigns (Coming Soon)</TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                ))
                              ) : (
                                account.metadata?.country_codes?.map((code: string) => (
                                  <TableRow key={code}>
                                    <TableCell>
                                      <Badge variant="outline" className="font-semibold">
                                        {code}
                                      </Badge>
                                    </TableCell>
                                    <TableCell className="font-mono text-sm">
                                      {account.marketplace?.countryCode === code ? account.profileDetails?.profileId : 'N/A'}
                                    </TableCell>
                                    <TableCell className="font-mono text-sm">N/A</TableCell>
                                    <TableCell className="text-center">
                                      <Switch
                                        defaultChecked={true}
                                        disabled
                                        aria-label={`Sync ${code} marketplace`}
                                      />
                                    </TableCell>
                                    <TableCell>
                                      <div className="flex items-center justify-center gap-1">
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8"
                                                disabled
                                              >
                                                <BarChart className="h-4 w-4" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p className="text-xs">View Dashboard (Coming Soon)</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                        <TooltipProvider>
                                          <Tooltip>
                                            <TooltipTrigger asChild>
                                              <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8"
                                                disabled
                                              >
                                                <ExternalLink className="h-4 w-4" />
                                              </Button>
                                            </TooltipTrigger>
                                            <TooltipContent>
                                              <p className="text-xs">View Campaigns (Coming Soon)</p>
                                            </TooltipContent>
                                          </Tooltip>
                                        </TooltipProvider>
                                      </div>
                                    </TableCell>
                                  </TableRow>
                                ))
                              )}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    </div>
                  )}

                    {account.profileDetails.accountInfo && (
                      <div className="space-y-4">
                        <Separator />
                        <div>
                          <h3 className="text-base font-semibold mb-4">Account Information</h3>
                          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                            <div className="space-y-2">
                              <label className="text-sm font-medium text-muted-foreground">Account Name</label>
                              <p className="text-sm font-medium">{account.profileDetails.accountInfo.name}</p>
                            </div>
                            <div className="space-y-2">
                              <label className="text-sm font-medium text-muted-foreground">Account Type</label>
                              <div>
                                <Badge variant="secondary" className="font-medium">
                                  {account.profileDetails.accountInfo.type}
                                </Badge>
                              </div>
                            </div>
                            {account.profileDetails.accountInfo.subType && (
                              <div className="space-y-2">
                                <label className="text-sm font-medium text-muted-foreground">Sub Type</label>
                                <p className="text-sm font-medium">{account.profileDetails.accountInfo.subType}</p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full py-12">
                    <div className="text-center space-y-3">
                      <div className="p-4 bg-muted/50 rounded-full inline-block">
                        <Info className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium">No profile details available</p>
                        <p className="text-xs text-muted-foreground">Profile information will appear here once loaded</p>
                      </div>
                    </div>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>

            <TabsContent value="history" className="flex-1 overflow-auto mt-6">
              <ScrollArea className="h-full pr-4">
                {isLoading ? (
                  <div className="space-y-3">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="p-4 rounded-lg border bg-card">
                        <Skeleton className="h-4 w-32 mb-2" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                    ))}
                  </div>
                ) : refreshHistory.length > 0 ? (
                  <div className="space-y-3">
                    {refreshHistory.map((history) => (
                      <div
                        key={history.id}
                        className={cn(
                          "p-4 rounded-lg border transition-colors",
                          history.success
                            ? "border-green-200 dark:border-green-800/50 bg-green-50/50 dark:bg-green-900/10"
                            : "border-red-200 dark:border-red-800/50 bg-red-50/50 dark:bg-red-900/10"
                        )}
                      >
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              {history.success ? (
                                <div className="p-1 bg-green-100 dark:bg-green-900/50 rounded">
                                  <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                                </div>
                              ) : (
                                <div className="p-1 bg-red-100 dark:bg-red-900/50 rounded">
                                  <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                                </div>
                              )}
                              <span className="text-sm font-semibold">
                                {history.success ? "Refresh Successful" : "Refresh Failed"}
                              </span>
                            </div>
                            <Badge
                              variant={history.triggeredBy === 'auto' ? 'secondary' : 'default'}
                              className="text-xs font-medium"
                            >
                              {history.triggeredBy === 'auto' ? 'Automatic' : history.triggeredBy === 'manual' ? 'Manual' : 'System'}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground pl-7">
                            {new Date(history.timestamp).toLocaleString()}
                          </div>
                          {history.error && (
                            <Alert variant="destructive" className="mt-2">
                              <AlertTriangle className="h-3 w-3" />
                              <AlertDescription className="text-xs">
                                {history.error}
                              </AlertDescription>
                            </Alert>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full py-12">
                    <div className="text-center space-y-3">
                      <div className="p-4 bg-muted/50 rounded-full inline-block">
                        <Clock className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div className="space-y-1">
                        <p className="text-sm font-medium">No refresh history available</p>
                        <p className="text-xs text-muted-foreground">Token refresh events will appear here</p>
                      </div>
                    </div>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter className="flex-shrink-0 border-t pt-4">
          {showDisconnectConfirm ? (
            <div className="flex items-center gap-3 w-full">
              <Alert className="flex-1" variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="font-medium">
                  Are you sure you want to disconnect this account? This action cannot be undone.
                </AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowDisconnectConfirm(false)}
                  className="min-w-[80px]"
                >
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDisconnect}
                  className="min-w-[80px]"
                >
                  Disconnect
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-between w-full">
              <div className="flex gap-2">
                {onDisconnect && (
                  <Button
                    variant="outline"
                    onClick={() => setShowDisconnectConfirm(true)}
                    className="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                  >
                    <Unlink className="h-4 w-4 mr-2" />
                    Disconnect
                  </Button>
                )}
              </div>
              <div className="flex gap-2">
                {onRefresh && account.status !== 'disconnected' && (
                  <Button
                    variant="outline"
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                  >
                    <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
                    {isRefreshing ? 'Refreshing...' : 'Refresh Token'}
                  </Button>
                )}

                <Button variant="default" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};