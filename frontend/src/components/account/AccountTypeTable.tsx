import React, { useState, useMemo } from 'react';
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Eye,
  RefreshCw,
  MoreHorizontal,
  ChevronUp,
  ChevronDown,
  AlertCircle,
  Plus,
  FileText,
  Target,
  Palette,
  Users,
  PlayCircle,
  BarChart3,
  ExternalLink,
} from 'lucide-react';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { AccountType } from './AccountTypeTabs';

interface AccountTypeTableProps {
  accountType: AccountType;
  accounts: any[];
  isLoading?: boolean;
  onViewDetails: (account: any) => void;
  onDisconnect: (accountId: string) => void;
  onRefresh: (accountId: string) => void;
  onReauthorize: (accountId: string) => void;
}

type SortDirection = 'asc' | 'desc' | null;
type SortColumn = string | null;

export const AccountTypeTable: React.FC<AccountTypeTableProps> = ({
  accountType,
  accounts,
  isLoading,
  onViewDetails,
  onDisconnect,
  onRefresh,
  onReauthorize,
}) => {
  const [sortColumn, setSortColumn] = useState<SortColumn>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Get columns based on account type
  const columns = useMemo(() => {
    switch (accountType) {
      case 'sponsored-ads':
        return [
          { key: 'accountName', label: 'Account Name', sortable: true },
          { key: 'profileId', label: 'Profile ID', sortable: true },
          { key: 'entityId', label: 'Entity ID', sortable: true },
          { key: 'marketplaces', label: 'Marketplaces', sortable: false },
          { key: 'lastManagedAt', label: 'Last Managed', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false },
        ];
      case 'dsp':
        return [
          { key: 'accountName', label: 'Account Name', sortable: true },
          { key: 'entityId', label: 'Entity ID', sortable: true },
          { key: 'profileId', label: 'Profile ID', sortable: true },
          { key: 'marketplace', label: 'Marketplace', sortable: true },
          { key: 'advertiserType', label: 'Advertiser Type', sortable: true },
          { key: 'status', label: 'Status', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false },
        ];
      case 'amc':
        return [
          { key: 'instanceName', label: 'Instance Name', sortable: true },
          { key: 'associatedAccounts', label: 'Associated Accounts', sortable: false },
          { key: 'audienceCount', label: 'Audiences', sortable: true },
          { key: 'workflowStatus', label: 'Workflow Status', sortable: true },
          { key: 'dataFreshness', label: 'Data Freshness', sortable: true },
          { key: 'actions', label: 'Actions', sortable: false },
        ];
    }
  }, [accountType]);

  // Sort accounts
  const sortedAccounts = useMemo(() => {
    if (!sortColumn || !sortDirection) return accounts;

    return [...accounts].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];

      if (aValue === null || aValue === undefined) return 1;
      if (bValue === null || bValue === undefined) return -1;

      if (typeof aValue === 'string') {
        return sortDirection === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      return 0;
    });
  }, [accounts, sortColumn, sortDirection]);

  const handleSort = (column: string) => {
    if (sortColumn === column) {
      setSortDirection(
        sortDirection === 'asc' ? 'desc' : sortDirection === 'desc' ? null : 'asc'
      );
      if (sortDirection === 'desc') {
        setSortColumn(null);
      }
    } else {
      setSortColumn(column);
      setSortDirection('asc');
    }
  };

  const renderStatus = (status: string) => {
    const statusConfig: Record<string, { color: string; label: string; tooltip: string }> = {
      active: { color: 'bg-green-500', label: 'Active', tooltip: 'Account is active and healthy' },
      error: { color: 'bg-red-500', label: 'Error', tooltip: 'Account needs attention' },
      disconnected: { color: 'bg-gray-500', label: 'Disconnected', tooltip: 'Account is disconnected' },
      paused: { color: 'bg-yellow-500', label: 'Paused', tooltip: 'Workflow is paused' },
    };

    const config = statusConfig[status] || statusConfig.disconnected;

    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              <div
                className={cn('h-2 w-2 rounded-full', config.color)}
                data-testid={`status-${status}`}
              />
              <span className="text-sm">{config.label}</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>{config.tooltip}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  };

  const renderAccountTypeActions = (account: any) => {
    const actions = {
      'sponsored-ads': [
        { icon: Plus, label: 'Create Campaign', action: 'create-campaign' },
        { icon: FileText, label: 'View Reports', action: 'view-reports' },
        { icon: Target, label: 'Manage Keywords', action: 'manage-keywords' },
      ],
      'dsp': [
        { icon: Plus, label: 'Create Order', action: 'create-order' },
        { icon: Users, label: 'View Audiences', action: 'view-audiences' },
        { icon: Palette, label: 'Manage Creatives', action: 'manage-creatives' },
      ],
      'amc': [
        { icon: Users, label: 'Create Audience', action: 'create-audience' },
        { icon: PlayCircle, label: 'Run Workflow', action: 'run-workflow' },
        { icon: BarChart3, label: 'View Insights', action: 'view-insights' },
      ],
    };

    return actions[accountType] || [];
  };

  const renderCellContent = (account: any, column: string) => {
    switch (column) {
      case 'marketplaces':
        return account.marketplaces?.join(', ') || '-';
      case 'lastManagedAt':
        return account.lastManagedAt
          ? format(new Date(account.lastManagedAt), 'MMM d, yyyy')
          : '-';
      case 'associatedAccounts':
        const dspCount = account.associatedDSPAccounts?.length || 0;
        const spCount = account.associatedSponsoredAdsAccounts?.length || 0;
        return `${dspCount} DSP, ${spCount} SP`;
      case 'audienceCount':
        return `${account.audienceCount || 0} audiences`;
      case 'campaignCount':
        return account.campaignCount ? `${account.campaignCount} campaigns` : '-';
      case 'activeKeywords':
        return account.activeKeywords ? `${account.activeKeywords} keywords` : '-';
      case 'dailySpend':
        return account.dailySpend
          ? `$${account.dailySpend.toLocaleString()}/day`
          : '-';
      case 'orderCount':
        return account.orderCount ? `${account.orderCount} orders` : '-';
      case 'activeLineItems':
        return account.activeLineItems ? `${account.activeLineItems} line items` : '-';
      case 'dspSpend':
        return account.dspSpend ? `$${account.dspSpend.toLocaleString()}` : '-';
      case 'status':
      case 'workflowStatus':
        return renderStatus(account[column]);
      default:
        return account[column] || '-';
    }
  };

  if (isLoading) {
    return (
      <div data-testid="table-skeleton">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 p-4" data-testid="skeleton-row">
            <Skeleton className="h-12 w-full" />
          </div>
        ))}
      </div>
    );
  }

  if (accounts.length === 0) {
    return (
      <Alert className="border-2 border-dashed">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          No accounts found. Try adjusting your filters or sync from Amazon to load accounts.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="w-full overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  column.sortable && 'cursor-pointer select-none hover:bg-muted/50',
                  'whitespace-nowrap'
                )}
                onClick={() => column.sortable && handleSort(column.key)}
              >
                <div className="flex items-center gap-1">
                  {column.label}
                  {column.sortable && (
                    <span className="ml-1" data-testid="sort-indicator">
                      {sortColumn === column.key && sortDirection === 'asc' && (
                        <ChevronUp className="h-4 w-4" data-testid="sort-asc" />
                      )}
                      {sortColumn === column.key && sortDirection === 'desc' && (
                        <ChevronDown className="h-4 w-4" data-testid="sort-desc" />
                      )}
                      {(sortColumn !== column.key || !sortDirection) && (
                        <div className="h-4 w-4" />
                      )}
                    </span>
                  )}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedAccounts.map((account) => (
            <TableRow key={account.id}>
              {columns.map((column) => (
                <TableCell key={column.key} className="whitespace-nowrap">
                  {column.key === 'actions' ? (
                    <div className="flex items-center gap-2">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onViewDetails(account)}
                            >
                              <Eye className="h-4 w-4" />
                              <span className="sr-only">View Details</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>View Details</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => onRefresh(account.id)}
                            >
                              <RefreshCw className="h-4 w-4" />
                              <span className="sr-only">Refresh</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>Refresh Token</TooltipContent>
                        </Tooltip>
                      </TooltipProvider>

                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="h-4 w-4" />
                            <span className="sr-only">More</span>
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {renderAccountTypeActions(account).map((action) => (
                            <DropdownMenuItem key={action.action}>
                              <action.icon className="mr-2 h-4 w-4" />
                              {action.label}
                            </DropdownMenuItem>
                          ))}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => onReauthorize(account.id)}>
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Reauthorize
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={() => onDisconnect(account.id)}
                            className="text-red-600"
                          >
                            Disconnect
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  ) : (
                    renderCellContent(account, column.key)
                  )}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};