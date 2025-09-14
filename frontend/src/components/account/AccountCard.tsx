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
  StarOff
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
import { AccountHealthIndicator } from './AccountHealthIndicator';
import { Account } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

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

  const timeUntilExpiry = accountService.getTimeUntilExpiry(account.tokenExpiresAt);
  const isRefreshingState = isRefreshing || isLocalRefreshing;

  return (
    <Card className={cn('relative hover:shadow-lg transition-shadow', className)}>
      {account.isDefault && (
        <Badge 
          className="absolute -top-2 -right-2 z-10"
          variant="default"
        >
          <Star className="h-3 w-3 mr-1 fill-current" />
          Default
        </Badge>
      )}

      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <User className="h-4 w-4" />
              {account.accountName}
            </CardTitle>
            <CardDescription className="text-xs">
              ID: {account.accountId}
            </CardDescription>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
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
              
              {account.status === 'expired' && (
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
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Marketplace Info */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Globe className="h-4 w-4" />
            <span>Marketplace</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">
              {account.marketplace.countryCode}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {account.marketplace.name}
            </span>
          </div>
        </div>

        {/* Last Refresh Time */}
        {account.lastRefreshTime && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Calendar className="h-4 w-4" />
              <span>Last Refresh</span>
            </div>
            <span className="text-xs">
              {new Date(account.lastRefreshTime).toLocaleString()}
            </span>
          </div>
        )}

        {/* Status Indicator */}
        <div className="pt-2 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Status</span>
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

      <CardFooter className="pt-3">
        <div className="flex gap-2 w-full">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onViewDetails(account)}
          >
            <Eye className="h-4 w-4 mr-2" />
            Details
          </Button>
          
          {account.status === 'expired' || account.status === 'warning' ? (
            <Button
              variant={account.status === 'expired' ? 'destructive' : 'default'}
              size="sm"
              className="flex-1"
              onClick={() => onReauthorize(account.id)}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Re-authorize
            </Button>
          ) : onRefresh && account.status !== 'disconnected' ? (
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={handleRefresh}
              disabled={isRefreshingState}
            >
              <RefreshCw className={cn("h-4 w-4 mr-2", isRefreshingState && "animate-spin")} />
              Refresh
            </Button>
          ) : null}
        </div>
      </CardFooter>
    </Card>
  );
};

// Loading skeleton for AccountCard
export const AccountCardSkeleton: React.FC = () => {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-3 w-24" />
          </div>
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-5 w-16" />
        </div>
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="pt-2 border-t">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-12" />
            <Skeleton className="h-6 w-20" />
          </div>
        </div>
      </CardContent>
      <CardFooter className="pt-3">
        <div className="flex gap-2 w-full">
          <Skeleton className="h-9 flex-1" />
          <Skeleton className="h-9 flex-1" />
        </div>
      </CardFooter>
    </Card>
  );
};