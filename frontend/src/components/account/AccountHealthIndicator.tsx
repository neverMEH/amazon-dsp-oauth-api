import React from 'react';
import { 
  CheckCircle2, 
  AlertCircle, 
  XCircle, 
  CircleOff,
  RefreshCw,
  Clock
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AccountStatus } from '@/types/account';
import { cn } from '@/lib/utils';

interface AccountHealthIndicatorProps {
  status: AccountStatus;
  expiresAt?: string | null;
  showLabel?: boolean;
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  isRefreshing?: boolean;
}

const statusConfig = {
  healthy: {
    icon: CheckCircle2,
    label: 'Healthy',
    color: 'text-green-600 dark:text-green-400',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    borderColor: 'border-green-200 dark:border-green-800',
    description: 'Token is valid and will not expire soon',
    badgeVariant: 'default' as const,
  },
  warning: {
    icon: AlertCircle,
    label: 'Expiring Soon',
    color: 'text-yellow-600 dark:text-yellow-400',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
    borderColor: 'border-yellow-200 dark:border-yellow-800',
    description: 'Token will expire within 24 hours',
    badgeVariant: 'secondary' as const,
  },
  expired: {
    icon: XCircle,
    label: 'Expired',
    color: 'text-red-600 dark:text-red-400',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    borderColor: 'border-red-200 dark:border-red-800',
    description: 'Token has expired and needs re-authorization',
    badgeVariant: 'destructive' as const,
  },
  disconnected: {
    icon: CircleOff,
    label: 'Disconnected',
    color: 'text-gray-500 dark:text-gray-400',
    bgColor: 'bg-gray-100 dark:bg-gray-900/30',
    borderColor: 'border-gray-200 dark:border-gray-800',
    description: 'Account is not connected',
    badgeVariant: 'outline' as const,
  },
};

const sizeConfig = {
  sm: {
    iconSize: 'h-4 w-4',
    fontSize: 'text-xs',
    padding: 'p-1',
  },
  md: {
    iconSize: 'h-5 w-5',
    fontSize: 'text-sm',
    padding: 'p-1.5',
  },
  lg: {
    iconSize: 'h-6 w-6',
    fontSize: 'text-base',
    padding: 'p-2',
  },
};

export const AccountHealthIndicator: React.FC<AccountHealthIndicatorProps> = ({
  status,
  expiresAt,
  showLabel = false,
  showTooltip = true,
  size = 'md',
  className,
  isRefreshing = false,
}) => {
  const config = statusConfig[status];
  const sizeClasses = sizeConfig[size];
  const Icon = isRefreshing ? RefreshCw : config.icon;

  const getTimeRemaining = () => {
    if (!expiresAt || status === 'disconnected') return null;
    
    const expiryDate = new Date(expiresAt);
    const now = new Date();
    const diff = expiryDate.getTime() - now.getTime();
    
    if (diff <= 0) return 'Expired';
    
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    if (days > 0) return `Expires in ${days}d ${hours}h`;
    if (hours > 0) return `Expires in ${hours}h ${minutes}m`;
    return `Expires in ${minutes}m`;
  };

  const timeRemaining = getTimeRemaining();

  const indicator = (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn(
          'inline-flex items-center justify-center rounded-full border',
          sizeClasses.padding,
          config.bgColor,
          config.borderColor,
          isRefreshing && 'animate-pulse'
        )}
      >
        <Icon
          className={cn(
            sizeClasses.iconSize,
            config.color,
            isRefreshing && 'animate-spin'
          )}
        />
      </div>
      
      {showLabel && (
        <div className="flex flex-col">
          <Badge
            variant={config.badgeVariant}
            className={cn(sizeClasses.fontSize)}
          >
            {isRefreshing ? 'Refreshing...' : config.label}
          </Badge>
          {timeRemaining && status !== 'expired' && (
            <div className={cn('flex items-center gap-1 mt-1', sizeClasses.fontSize, 'text-muted-foreground')}>
              <Clock className="h-3 w-3" />
              <span>{timeRemaining}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );

  if (!showTooltip) {
    return indicator;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {indicator}
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs">
          <div className="space-y-1">
            <p className="font-semibold">{config.label}</p>
            <p className="text-xs text-muted-foreground">{config.description}</p>
            {timeRemaining && (
              <p className="text-xs font-medium">{timeRemaining}</p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};