import React, { useState } from 'react';
import {
  MoreHorizontal,
  Eye,
  RefreshCw,
  Unlink,
  Settings,
  Star,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Pause,
  Globe,
  Calendar,
  Shield,
  ExternalLink
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Account, AccountStatus } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { format, formatDistanceToNow } from 'date-fns';

interface AccountTableProps {
  accounts: Account[];
  onViewDetails: (account: Account) => void;
  onDisconnect: (accountId: string) => void;
  onReauthorize: (accountId: string) => void;
  onRefresh?: (accountId: string) => Promise<void>;
  onSetDefault?: (accountId: string) => void;
  isRefreshing?: boolean;
  className?: string;
}

type SortField = 'accountName' | 'status' | 'marketplaces' | 'lastRefresh' | 'tokenExpiry';
type SortDirection = 'asc' | 'desc';

export const AccountTable: React.FC<AccountTableProps> = ({
  accounts,
  onViewDetails,
  onDisconnect,
  onReauthorize,
  onRefresh,
  onSetDefault,
  isRefreshing = false,
  className,
}) => {
  const { toast } = useToast();
  const [sortField, setSortField] = useState<SortField | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [refreshingIds, setRefreshingIds] = useState<Set<string>>(new Set());

  const handleRefresh = async (accountId: string) => {
    if (!onRefresh) return;

    setRefreshingIds(prev => new Set(prev).add(accountId));
    try {
      await onRefresh(accountId);
      toast({
        title: "Token refreshed",
        description: "Account token has been successfully refreshed.",
      });
    } catch (error) {
      toast({
        title: "Refresh failed",
        description: "Failed to refresh token. Please try again.",
        variant: "destructive",
      });
    } finally {
      setRefreshingIds(prev => {
        const next = new Set(prev);
        next.delete(accountId);
        return next;
      });
    }
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedAccounts = React.useMemo(() => {
    if (!sortField) return accounts;

    return [...accounts].sort((a, b) => {
      let compareValue = 0;

      switch (sortField) {
        case 'accountName':
          compareValue = (a.accountName || '').localeCompare(b.accountName || '');
          break;
        case 'status':
          compareValue = (a.status || '').localeCompare(b.status || '');
          break;
        case 'marketplaces':
          const aCount = a.metadata?.alternate_ids?.length || a.metadata?.country_codes?.length || 0;
          const bCount = b.metadata?.alternate_ids?.length || b.metadata?.country_codes?.length || 0;
          compareValue = aCount - bCount;
          break;
        case 'lastRefresh':
          const aTime = a.lastRefreshTime ? new Date(a.lastRefreshTime).getTime() : 0;
          const bTime = b.lastRefreshTime ? new Date(b.lastRefreshTime).getTime() : 0;
          compareValue = aTime - bTime;
          break;
        case 'tokenExpiry':
          const aExpiry = a.tokenExpiresAt ? new Date(a.tokenExpiresAt).getTime() : 0;
          const bExpiry = b.tokenExpiresAt ? new Date(b.tokenExpiresAt).getTime() : 0;
          compareValue = aExpiry - bExpiry;
          break;
      }

      return sortDirection === 'asc' ? compareValue : -compareValue;
    });
  }, [accounts, sortField, sortDirection]);

  const getStatusIcon = (status: AccountStatus) => {
    switch (status) {
      case 'active':
        return <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />;
      case 'disconnected':
        return <Pause className="h-4 w-4 text-gray-600 dark:text-gray-400" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />;
    }
  };

  const getStatusBadge = (status: AccountStatus) => {
    const variants: Record<AccountStatus, 'default' | 'destructive' | 'secondary' | 'outline'> = {
      active: 'default',
      error: 'destructive',
      disconnected: 'secondary',
      pending: 'outline',
    };

    return (
      <Badge variant={variants[status] || 'outline'} className="font-medium">
        <span className="flex items-center gap-1.5">
          {getStatusIcon(status)}
          {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
      </Badge>
    );
  };

  const SortButton: React.FC<{
    field: SortField;
    children: React.ReactNode;
    className?: string;
  }> = ({ field, children, className }) => {
    const isActive = sortField === field;
    const Icon = isActive ? (sortDirection === 'asc' ? ArrowUp : ArrowDown) : ArrowUpDown;

    return (
      <Button
        variant="ghost"
        size="sm"
        className={cn("-ml-3 h-8 data-[state=open]:bg-accent", className)}
        onClick={() => handleSort(field)}
      >
        {children}
        <Icon className={cn(
          "ml-2 h-4 w-4",
          isActive ? "text-foreground" : "text-muted-foreground"
        )} />
      </Button>
    );
  };

  const getMarketplaceCount = (account: Account) => {
    if (account.metadata?.alternate_ids?.length > 0) {
      const uniqueCountries = new Set(account.metadata.alternate_ids.map((altId: any) => altId.countryCode));
      return uniqueCountries.size;
    }
    return account.metadata?.country_codes?.length || (account.marketplace?.countryCode ? 1 : 0);
  };

  const getMarketplaceCodes = (account: Account): string[] => {
    if (account.metadata?.alternate_ids?.length > 0) {
      const uniqueCountries = new Set(account.metadata.alternate_ids.map((altId: any) => altId.countryCode));
      return Array.from(uniqueCountries);
    }
    return account.metadata?.country_codes || (account.marketplace?.countryCode ? [account.marketplace.countryCode] : []);
  };

  return (
    <TooltipProvider>
      <div className={cn("rounded-lg border bg-card", className)}>
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-[30px]">
                <span className="sr-only">Default</span>
              </TableHead>
              <TableHead className="min-w-[200px]">
                <SortButton field="accountName">Account Name</SortButton>
              </TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-center">
                <SortButton field="status">Status</SortButton>
              </TableHead>
              <TableHead className="text-center">
                <SortButton field="marketplaces">Marketplaces</SortButton>
              </TableHead>
              <TableHead>
                <SortButton field="lastRefresh">Last Refresh</SortButton>
              </TableHead>
              <TableHead>
                <SortButton field="tokenExpiry">Token Expiry</SortButton>
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedAccounts.map((account) => {
              const isRefreshingAccount = refreshingIds.has(account.id) || isRefreshing;
              const marketplaceCount = getMarketplaceCount(account);
              const marketplaceCodes = getMarketplaceCodes(account);

              return (
                <TableRow
                  key={account.id}
                  className="group hover:bg-muted/50 transition-colors"
                >
                  <TableCell>
                    {account.isDefault && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Default Account</p>
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </TableCell>

                  <TableCell className="font-medium">
                    <div className="flex flex-col">
                      <span className="text-sm font-semibold">
                        {account.accountName || 'Unknown Account'}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        ID: {account.accountId || 'N/A'}
                      </span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <Badge variant="outline" className="font-normal">
                      {account.profileDetails?.accountInfo?.subType === 'DSP' ||
                       account.metadata?.account_subtype === 'DSP'
                        ? 'DSP'
                        : 'Sponsored'}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-center">
                    {getStatusBadge(account.status)}
                  </TableCell>

                  <TableCell className="text-center">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center justify-center gap-1.5">
                          <Globe className="h-4 w-4 text-muted-foreground" />
                          <Badge variant="secondary" className="px-2">
                            {marketplaceCount}
                          </Badge>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="font-medium">Active Marketplaces:</p>
                        <p className="text-xs">{marketplaceCodes.join(', ') || 'None'}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TableCell>

                  <TableCell>
                    {account.lastRefreshTime ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center gap-1.5 text-sm">
                            <Calendar className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-xs">
                              {formatDistanceToNow(new Date(account.lastRefreshTime), { addSuffix: true })}
                            </span>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{format(new Date(account.lastRefreshTime), 'PPpp')}</p>
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-xs text-muted-foreground">Never</span>
                    )}
                  </TableCell>

                  <TableCell>
                    {account.tokenExpiresAt ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex items-center gap-1.5 text-sm">
                            <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className={cn(
                              "text-xs",
                              new Date(account.tokenExpiresAt) < new Date(Date.now() + 24 * 60 * 60 * 1000)
                                ? "text-yellow-600 dark:text-yellow-400 font-medium"
                                : ""
                            )}>
                              {accountService.getTimeUntilExpiry(account.tokenExpiresAt)}
                            </span>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>Expires: {format(new Date(account.tokenExpiresAt), 'PPpp')}</p>
                        </TooltipContent>
                      </Tooltip>
                    ) : (
                      <span className="text-xs text-muted-foreground">N/A</span>
                    )}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => onViewDetails(account)}
                          >
                            <Eye className="h-4 w-4" />
                            <span className="sr-only">View details</span>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>View Details</TooltipContent>
                      </Tooltip>

                      {onRefresh && account.status !== 'disconnected' && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => handleRefresh(account.id)}
                              disabled={isRefreshingAccount}
                            >
                              <RefreshCw className={cn(
                                "h-4 w-4",
                                isRefreshingAccount && "animate-spin"
                              )} />
                              <span className="sr-only">Refresh token</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Refresh Token</TooltipContent>
                        </Tooltip>
                      )}

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                            <span className="sr-only">Open menu</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />

                          <DropdownMenuItem onClick={() => onViewDetails(account)}>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>

                          {account.status === 'error' && (
                            <DropdownMenuItem onClick={() => onReauthorize(account.id)}>
                              <Settings className="mr-2 h-4 w-4" />
                              Re-authorize
                            </DropdownMenuItem>
                          )}

                          {onSetDefault && !account.isDefault && (
                            <DropdownMenuItem onClick={() => onSetDefault(account.id)}>
                              <Star className="mr-2 h-4 w-4" />
                              Set as Default
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuSeparator />

                          <DropdownMenuItem
                            onClick={() => onDisconnect(account.id)}
                            className="text-red-600 dark:text-red-400"
                          >
                            <Unlink className="mr-2 h-4 w-4" />
                            Disconnect
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>

        {accounts.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">No accounts found</p>
          </div>
        )}
      </div>
    </TooltipProvider>
  );
};

// Loading skeleton for AccountTable
export const AccountTableSkeleton: React.FC = () => {
  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[30px]"></TableHead>
            <TableHead>Account Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Marketplaces</TableHead>
            <TableHead>Last Refresh</TableHead>
            <TableHead>Token Expiry</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {[1, 2, 3, 4, 5].map((i) => (
            <TableRow key={i}>
              <TableCell><Skeleton className="h-4 w-4" /></TableCell>
              <TableCell>
                <div className="flex flex-col gap-1">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </TableCell>
              <TableCell><Skeleton className="h-6 w-16" /></TableCell>
              <TableCell><Skeleton className="h-6 w-20" /></TableCell>
              <TableCell><Skeleton className="h-6 w-12" /></TableCell>
              <TableCell><Skeleton className="h-4 w-24" /></TableCell>
              <TableCell><Skeleton className="h-4 w-20" /></TableCell>
              <TableCell>
                <div className="flex gap-2 justify-end">
                  <Skeleton className="h-8 w-8" />
                  <Skeleton className="h-8 w-8" />
                  <Skeleton className="h-8 w-8" />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};