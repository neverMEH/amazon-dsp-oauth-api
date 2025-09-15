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
  ToggleRight
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
      <DialogContent className="max-w-3xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            {account.accountName || 'Unknown Account'}
          </DialogTitle>
          <DialogDescription className="space-y-1">
            <div>Account ID: {account.accountId || 'N/A'}</div>
            <div>Type: {account.accountType || 'advertising'}</div>
          </DialogDescription>
        </DialogHeader>

        <div className="mt-4">
          {/* Status Alert */}
          {account.status === 'error' && (
            <Alert variant="destructive" className="mb-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Needs Attention</AlertTitle>
              <AlertDescription>
                Auto-refresh has failed for this account. Please re-authorize to restore automatic token management.
              </AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="overview" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="history">Refresh History</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                {/* Account Status */}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground">Status</div>
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
                  <div className="text-sm font-medium text-muted-foreground">Default Account</div>
                  <Badge variant={account.isDefault ? "default" : "outline"}>
                    {account.isDefault ? "Yes" : "No"}
                  </Badge>
                </div>


                {/* Region */}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <MapPin className="h-3 w-3" />
                    Region
                  </div>
                  <span className="text-sm">{account.marketplace?.region || account.metadata?.region || 'Unknown'}</span>
                </div>

                {/* Last Refresh */}
                {account.lastRefreshTime && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                      <RefreshCw className="h-3 w-3" />
                      Last Refresh
                    </div>
                    <span className="text-sm">
                      {new Date(account.lastRefreshTime).toLocaleString()}
                    </span>
                  </div>
                )}

                {/* Token Expires */}
                {account.tokenExpiresAt && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Token Expires
                    </div>
                    <span className="text-sm">
                      {new Date(account.tokenExpiresAt).toLocaleString()}
                    </span>
                  </div>
                )}

                {/* Created At */}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Connected Since
                  </div>
                  <span className="text-sm">
                    {new Date(account.createdAt).toLocaleDateString()}
                  </span>
                </div>

                {/* Updated At */}
                <div className="space-y-2">
                  <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Last Updated
                  </div>
                  <span className="text-sm">
                    {new Date(account.updatedAt).toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Marketplace Management Table in Overview - Always Show */}
              <div className="mt-6 space-y-3">
                  <Separator />
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold">Marketplace Details</h4>
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="right" className="max-w-xs">
                          <p className="text-xs">
                            Each marketplace has unique IDs. Use the appropriate Profile ID when making API calls to a specific marketplace.
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>

                  <div className="border rounded-lg">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="w-[100px]">Marketplace</TableHead>
                          <TableHead>Profile ID</TableHead>
                          <TableHead>Entity ID</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {account.metadata?.alternate_ids?.length > 0 ? (
                          account.metadata.alternate_ids.map((altId: any) => (
                            <TableRow key={altId.countryCode}>
                              <TableCell>
                                <Badge variant="outline" className="font-semibold">
                                  {altId.countryCode}
                                </Badge>
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {altId.profileId || 'N/A'}
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {altId.entityId || 'N/A'}
                              </TableCell>
                            </TableRow>
                          ))
                        ) : account.metadata?.country_codes?.length > 0 ? (
                          account.metadata.country_codes.map((code: string) => (
                            <TableRow key={code}>
                              <TableCell>
                                <Badge variant="outline" className="font-semibold">
                                  {code}
                                </Badge>
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {account.profileDetails?.profileId || 'N/A'}
                              </TableCell>
                              <TableCell className="font-mono text-sm">
                                {account.accountId || 'N/A'}
                              </TableCell>
                            </TableRow>
                          ))
                        ) : (
                          <TableRow>
                            <TableCell>
                              <Badge variant="outline" className="font-semibold">
                                {account.marketplace?.countryCode || 'N/A'}
                              </Badge>
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {account.profileDetails?.profileId || 'N/A'}
                            </TableCell>
                            <TableCell className="font-mono text-sm">
                              {account.accountId || 'N/A'}
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </div>
              </div>
            </TabsContent>

            <TabsContent value="profile" className="space-y-4 mt-4">
              {account.profileDetails ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                        <Hash className="h-3 w-3" />
                        Profile ID
                      </div>
                      <span className="text-sm font-mono">{account.profileDetails.profileId}</span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground">Profile Name</div>
                      <span className="text-sm">{account.profileDetails.profileName}</span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                        <Building className="h-3 w-3" />
                        Profile Type
                      </div>
                      <Badge variant="outline" className="capitalize">
                        {account.profileDetails.profileType}
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        Currency
                      </div>
                      <span className="text-sm">{account.profileDetails.currency}</span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                        <MapPin className="h-3 w-3" />
                        Country
                      </div>
                      <span className="text-sm">{account.profileDetails.country}</span>
                    </div>

                    <div className="space-y-2">
                      <div className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Timezone
                      </div>
                      <span className="text-sm">{account.profileDetails.timezone}</span>
                    </div>
                  </div>

                  {/* Marketplace Management Table */}
                  {(account.metadata?.alternate_ids?.length > 0 || account.metadata?.country_codes?.length > 0) && (
                    <>
                      <Separator />
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-semibold">Marketplace Management</h4>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <HelpCircle className="h-3 w-3 text-muted-foreground cursor-help" />
                                </TooltipTrigger>
                                <TooltipContent side="right" className="max-w-xs">
                                  <p className="text-xs">
                                    Manage each marketplace individually. Toggle sync to enable/disable data collection
                                    for specific marketplaces.
                                  </p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        </div>

                        <div className="border rounded-lg">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="w-[100px]">Marketplace</TableHead>
                                <TableHead>Profile ID</TableHead>
                                <TableHead>Entity ID</TableHead>
                                <TableHead className="text-center">Sync</TableHead>
                                <TableHead className="text-center">Actions</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {account.metadata?.alternate_ids?.length > 0 ? (
                                account.metadata.alternate_ids.map((altId: any) => (
                                  <TableRow key={altId.countryCode}>
                                    <TableCell>
                                      <Badge variant="outline" className="font-semibold">
                                        {altId.countryCode}
                                      </Badge>
                                    </TableCell>
                                    <TableCell className="font-mono text-sm">
                                      {altId.profileId || 'N/A'}
                                    </TableCell>
                                    <TableCell className="font-mono text-sm">
                                      {altId.entityId || 'N/A'}
                                    </TableCell>
                                    <TableCell className="text-center">
                                      <Switch
                                        defaultChecked={true}
                                        disabled
                                        aria-label={`Sync ${altId.countryCode} marketplace`}
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
                    </>
                  )}

                  {account.profileDetails.accountInfo && (
                    <>
                      <Separator />
                      <div className="space-y-2">
                        <h4 className="text-sm font-semibold">Account Information</h4>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">Account Name</div>
                            <span className="text-sm">{account.profileDetails.accountInfo.name}</span>
                          </div>
                          <div className="space-y-1">
                            <div className="text-xs text-muted-foreground">Account Type</div>
                            <Badge variant="outline" className="text-xs">
                              {account.profileDetails.accountInfo.type}
                            </Badge>
                          </div>
                          {account.profileDetails.accountInfo.subType && (
                            <div className="space-y-1">
                              <div className="text-xs text-muted-foreground">Sub Type</div>
                              <span className="text-sm">{account.profileDetails.accountInfo.subType}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Info className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No profile details available</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="history" className="mt-4">
              <ScrollArea className="h-[300px] w-full pr-4">
                {isLoading ? (
                  <div className="space-y-2">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="p-3 border rounded-lg">
                        <Skeleton className="h-4 w-32 mb-2" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                    ))}
                  </div>
                ) : refreshHistory.length > 0 ? (
                  <div className="space-y-2">
                    {refreshHistory.map((history) => (
                      <div
                        key={history.id}
                        className={cn(
                          "p-3 border rounded-lg flex items-center justify-between",
                          history.success
                            ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
                            : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
                        )}
                      >
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {history.success ? (
                              <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                            )}
                            <span className="text-sm font-medium">
                              {history.success ? "Success" : "Failed"}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {history.triggeredBy}
                            </Badge>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {new Date(history.timestamp).toLocaleString()}
                          </div>
                          {history.error && (
                            <div className="text-xs text-red-600 dark:text-red-400">
                              {history.error}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>No refresh history available</p>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          </Tabs>
        </div>

        <DialogFooter>
          {showDisconnectConfirm ? (
            <div className="flex items-center gap-2 w-full">
              <Alert className="flex-1">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  Are you sure you want to disconnect this account?
                </AlertDescription>
              </Alert>
              <Button
                variant="outline"
                onClick={() => setShowDisconnectConfirm(false)}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDisconnect}
              >
                Confirm
              </Button>
            </div>
          ) : (
            <>
              {onDisconnect && (
                <Button
                  variant="destructive"
                  onClick={() => setShowDisconnectConfirm(true)}
                >
                  <Unlink className="h-4 w-4 mr-2" />
                  Disconnect Account
                </Button>
              )}
              
              {onRefresh && account.status !== 'disconnected' && (
                <Button
                  variant="outline"
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                >
                  <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshing && "animate-spin")} />
                  Refresh Token
                </Button>
              )}
              
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};