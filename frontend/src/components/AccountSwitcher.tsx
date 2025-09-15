import { useEffect, useState } from 'react'
import { Check, ChevronDown, Plus, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useDashboardStore, Account } from '@/stores/dashboard'
import { dashboardAPI } from '@/services/dashboard-api'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

interface AccountSwitcherProps {
  className?: string
}

export function AccountSwitcher({ className }: AccountSwitcherProps) {
  const { 
    currentAccount, 
    accounts, 
    isLoading, 
    setCurrentAccount, 
    setAccounts, 
    setLoading,
    setError 
  } = useDashboardStore()
  
  const [isOpen, setIsOpen] = useState(false)
  const [isSyncing, setIsSyncing] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    const loadAccounts = async () => {
      try {
        setLoading(true)
        const accountsData = await dashboardAPI.getUserAccounts()
        setAccounts(accountsData)
        
        // Set first active account as current if none selected
        if (!currentAccount && accountsData.length > 0) {
          const activeAccount = accountsData.find(acc => acc.isActive) || accountsData[0]
          setCurrentAccount(activeAccount)
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load accounts'
        setError(errorMessage)
        toast({
          variant: 'destructive',
          title: 'Error Loading Accounts',
          description: errorMessage,
        })
      } finally {
        setLoading(false)
      }
    }

    loadAccounts()
  }, [setAccounts, setCurrentAccount, setLoading, setError, currentAccount, toast])

  const handleAccountSwitch = async (account: Account) => {
    try {
      setCurrentAccount(account)
      setIsOpen(false)
      
      // Call API to switch account context
      await dashboardAPI.switchAccount(account.id)
      
      toast({
        title: 'Account Switched',
        description: `Switched to ${account.name}`,
      })
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to switch account'
      toast({
        variant: 'destructive',
        title: 'Error Switching Account',
        description: errorMessage,
      })
      // Revert on error
      // Keep current account unchanged on error
    }
  }

  const handleSyncAccount = async (accountId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    try {
      setIsSyncing(accountId)
      await dashboardAPI.syncAccount(accountId)
      
      toast({
        title: 'Account Synced',
        description: 'Account data has been updated',
      })
      
      // Refresh accounts list
      const accountsData = await dashboardAPI.getUserAccounts()
      setAccounts(accountsData)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to sync account'
      toast({
        variant: 'destructive',
        title: 'Sync Failed',
        description: errorMessage,
      })
    } finally {
      setIsSyncing(null)
    }
  }

  const formatLastSync = (dateString?: string): string => {
    if (!dateString) return 'Never synced'

    const date = new Date(dateString)
    const now = new Date()
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60))

    if (diffInHours < 1) return 'Just synced'
    if (diffInHours < 24) return `${diffInHours}h ago`
    if (diffInHours < 168) return `${Math.floor(diffInHours / 24)}d ago`
    return date.toLocaleDateString()
  }

  const handleConnectAccount = async () => {
    console.log('🔍 Connect Account button clicked from AccountSwitcher!');
    try {
      console.log('🔍 Making request to /api/v1/auth/amazon/login...');
      const response = await fetch('/api/v1/auth/amazon/login');

      console.log('🔍 Response status:', response.status);
      console.log('🔍 Response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🔍 Response data:', data);
        console.log('🔍 Redirecting to:', data.auth_url);
        window.location.href = data.auth_url;
      } else {
        const errorData = await response.text();
        console.error('🔍 Response error:', errorData);
        toast({
          variant: 'destructive',
          title: 'Connection Failed',
          description: 'Unable to connect to Amazon. Please try again.',
        });
      }
    } catch (error) {
      console.error('🔍 Connect failed:', error);
      toast({
        variant: 'destructive',
        title: 'Connection Failed',
        description: 'Unable to connect to Amazon. Please try again.',
      });
    }
  }

  if (isLoading) {
    return (
      <div className={cn('w-64', className)}>
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (accounts.length === 0) {
    return (
      <Button
        variant="outline"
        className={cn('w-64 justify-start', className)}
        onClick={handleConnectAccount}
      >
        <Plus className="mr-2 h-4 w-4" />
        Connect Account
      </Button>
    )
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={isOpen}
          className={cn('w-64 justify-between', className)}
        >
          <div className="flex items-center space-x-2 flex-1 min-w-0">
            <div className="flex flex-col items-start flex-1 min-w-0">
              <span className="text-sm font-medium truncate">
                {currentAccount?.name || 'Select account'}
              </span>
              {currentAccount && (
                <span className="text-xs text-muted-foreground">
                  {currentAccount.countryCode} • {currentAccount.currencyCode}
                </span>
              )}
            </div>
            {currentAccount?.isActive && (
              <Badge variant="secondary" className="text-xs">
                Active
              </Badge>
            )}
          </div>
          <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64 p-0">
        <DropdownMenuLabel className="px-3 py-2 text-sm font-semibold">
          Switch Account
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <div className="max-h-64 overflow-y-auto">
          {accounts.map((account) => (
            <DropdownMenuItem
              key={account.id}
              className="flex items-center justify-between p-3 cursor-pointer"
              onClick={() => handleAccountSwitch(account)}
            >
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium truncate">
                      {account.name}
                    </span>
                    {account.isActive && (
                      <Badge variant="secondary" className="text-xs">
                        Active
                      </Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {account.countryCode} • {formatLastSync(account.lastSyncAt)}
                  </div>
                </div>
                
                <div className="flex items-center space-x-2 shrink-0">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-6 w-6 p-0"
                    onClick={(e) => handleSyncAccount(account.id, e)}
                    disabled={isSyncing === account.id}
                  >
                    <RefreshCw 
                      className={cn(
                        'h-3 w-3',
                        isSyncing === account.id && 'animate-spin'
                      )} 
                    />
                  </Button>
                  
                  {currentAccount?.id === account.id && (
                    <Check className="h-4 w-4 text-purple-600" />
                  )}
                </div>
              </div>
            </DropdownMenuItem>
          ))}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem className="p-3" onClick={handleConnectAccount}>
          <Plus className="mr-2 h-4 w-4" />
          Connect New Account
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}