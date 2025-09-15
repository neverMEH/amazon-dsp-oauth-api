import React, { useState } from 'react';
import {
  MoreVertical,
  Eye,
  RefreshCw,
  Unlink,
  Settings,
  Globe,
  Calendar,
  User,
  Star,
  StarOff,
  Shield,
  Building2,
  Hash,
  Clock
} from 'lucide-react';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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
import { AccountHealthIndicator } from './AccountHealthIndicator';
import { Account } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';

interface AccountCardProps {
  account: Account;
  onViewDetails: (account: Account) => void;
  onDisconnect: (accountId: string) => void;
  onReauthorize: (accountId: string) => void;
  onRefresh?: (accountId: string) => Promise<void>;
  onSetDefault?: (accountId: string) => void;
  isRefreshing?: boolean;
  className?: string;
}

export const AccountCard: React.FC<AccountCardProps> = ({
  account,
  onViewDetails,
  onDisconnect,
  onReauthorize,
  onRefresh,
  onSetDefault,
  isRefreshing = false,
  className,
}) => {
  const { toast } = useToast();
  const [isLocalRefreshing, setIsLocalRefreshing] = useState(false);

  const handleRefresh = async () => {
    if (!onRefresh) return;
    
    setIsLocalRefreshing(true);
    try {
      await onRefresh(account.id);
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
      setIsLocalRefreshing(false);
    }
  };

  const timeUntilExpiry = account.tokenExpiresAt
    ? accountService.getTimeUntilExpiry(account.tokenExpiresAt)
    : 'N/A';
  const isRefreshingState = isRefreshing || isLocalRefreshing;

  return (
    <TooltipProvider>
      <Card className={cn(
        'relative overflow-hidden transition-all duration-200',
        'hover:shadow-xl hover:-translate-y-1',
        'border-border/50 bg-gradient-to-br from-card to-card/95',
        className
      )}>
        {/* Status Bar at Top */}
        <div className={cn(
          "absolute top-0 left-0 right-0 h-1",
          account.status === 'active' && "bg-gradient-to-r from-green-500 to-green-600",
          account.status === 'error' && "bg-gradient-to-r from-red-500 to-red-600",
          account.status === 'disconnected' && "bg-gradient-to-r from-gray-400 to-gray-500"
        )} />

        {/* Default Badge */}
        {account.isDefault && (
          <div className="absolute -top-2 -right-2 z-10">
            <Badge
              className="bg-gradient-to-r from-yellow-500 to-yellow-600 text-white border-0 shadow-lg"
            >
              <Star className="h-3 w-3 mr-1 fill-current" />
              Default
            </Badge>
          </div>
        )}

        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Building2 className="h-4 w-4 text-primary" />
                </div>
                <CardTitle className="text-base font-semibold line-clamp-1">
                  {account.accountName || 'Unknown Account'}
                </CardTitle>
              </div>

              <div className="space-y-1.5 pl-10">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Hash className="h-3 w-3" />
                  <span className="font-mono">{account.accountId || 'N/A'}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Badge
                    variant={account.profileDetails?.accountInfo?.subType === 'DSP' ||
                             account.metadata?.account_subtype === 'DSP' ? 'default' : 'secondary'}
                    className="text-xs px-2 py-0"
                  >
                    {account.profileDetails?.accountInfo?.subType === 'DSP' ||
                     account.metadata?.account_subtype === 'DSP'
                      ? 'DSP'
                      : 'Sponsored Ads'}
                  </Badge>
                </div>
              </div>
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 hover:bg-muted"
                >
                  <MoreVertical className="h-4 w-4" />
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

                {onRefresh && account.status !== 'disconnected' && (
                  <DropdownMenuItem
                    onClick={handleRefresh}
                    disabled={isRefreshingState}
                  >
                    <RefreshCw className={cn("mr-2 h-4 w-4", isRefreshingState && "animate-spin")} />
                    Refresh Token
                  </DropdownMenuItem>
                )}

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
                  className="text-red-600 dark:text-red-400 focus:text-red-600 dark:focus:text-red-400"
                >
                  <Unlink className="mr-2 h-4 w-4" />
                  Disconnect
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-2">
          {/* Quick Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            {/* Marketplaces */}
            <div className="bg-muted/50 rounded-lg p-2.5">
              <div className="flex items-center gap-2 mb-1">
                <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Markets</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="text-lg font-semibold">
                    {(() => {
                      if (account.metadata?.alternate_ids?.length > 0) {
                        const uniqueCountries = new Set(account.metadata.alternate_ids.map((altId: any) => altId.countryCode));
                        return uniqueCountries.size;
                      }
                      return account.metadata?.country_codes?.length || (account.marketplace?.countryCode ? 1 : 0);
                    })()}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="font-medium">Active Marketplaces</p>
                  <p className="text-xs">
                    {(() => {
                      if (account.metadata?.alternate_ids?.length > 0) {
                        const uniqueCountries = new Set(account.metadata.alternate_ids.map((altId: any) => altId.countryCode));
                        return Array.from(uniqueCountries).join(', ');
                      }
                      return account.metadata?.country_codes?.join(', ') ||
                             account.marketplace?.countryCode ||
                             'None';
                    })()}
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>

            {/* Token Expiry */}
            <div className="bg-muted/50 rounded-lg p-2.5">
              <div className="flex items-center gap-2 mb-1">
                <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground">Expires</span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className={cn(
                    "text-sm font-semibold",
                    account.tokenExpiresAt && new Date(account.tokenExpiresAt) < new Date(Date.now() + 24 * 60 * 60 * 1000)
                      ? "text-yellow-600 dark:text-yellow-400"
                      : ""
                  )}>
                    {timeUntilExpiry}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  {account.tokenExpiresAt ? (
                    <p>Token expires: {new Date(account.tokenExpiresAt).toLocaleString()}</p>
                  ) : (
                    <p>Token expiry not available</p>
                  )}
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Last Refresh */}
          {account.lastRefreshTime && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded-lg px-3 py-2">
              <Clock className="h-3.5 w-3.5" />
              <span>Last refresh:</span>
              <span className="font-medium">
                {formatDistanceToNow(new Date(account.lastRefreshTime), { addSuffix: true })}
              </span>
            </div>
          )}

          {/* Status Section */}
          <div className="pt-3 border-t border-border/50">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Connection Status
              </span>
              <AccountHealthIndicator
                status={account.status}
                expiresAt={account.tokenExpiresAt}
                showLabel={true}
                size="sm"
                isRefreshing={isRefreshingState}
              />
            </div>
          </div>
        </CardContent>

        <CardFooter className="pt-0 pb-4 px-4">
          <div className="flex gap-2 w-full">
            {account.status === 'error' ? (
              <>
                <Button
                  variant="destructive"
                  size="sm"
                  className="flex-1 shadow-sm"
                  onClick={() => onReauthorize(account.id)}
                >
                  <Settings className="h-3.5 w-3.5 mr-1.5" />
                  Fix Connection
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onViewDetails(account)}
                >
                  <Eye className="h-3.5 w-3.5" />
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  className="flex-1 shadow-sm"
                  onClick={() => onViewDetails(account)}
                >
                  <Eye className="h-3.5 w-3.5 mr-1.5" />
                  View Details
                </Button>
                {onRefresh && account.status !== 'disconnected' && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isRefreshingState}
                      >
                        <RefreshCw className={cn(
                          "h-3.5 w-3.5",
                          isRefreshingState && "animate-spin"
                        )} />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Refresh Token</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </>
            )}
          </div>
        </CardFooter>
      </Card>
    </TooltipProvider>
  );
};

// Loading skeleton for AccountCard
export const AccountCardSkeleton: React.FC = () => {
  return (
    <Card className="relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-1 bg-muted animate-pulse" />

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <div className="flex items-center gap-2">
              <Skeleton className="h-8 w-8 rounded-lg" />
              <Skeleton className="h-5 w-32" />
            </div>
            <div className="pl-10 space-y-1.5">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-5 w-16" />
            </div>
          </div>
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4 pt-2">
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-16 rounded-lg" />
          <Skeleton className="h-16 rounded-lg" />
        </div>
        <Skeleton className="h-8 rounded-lg" />
        <div className="pt-3 border-t border-border/50">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-6 w-20" />
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-0 pb-4 px-4">
        <div className="flex gap-2 w-full">
          <Skeleton className="h-9 flex-1" />
          <Skeleton className="h-9 w-9" />
        </div>
      </CardFooter>
    </Card>
  );
};