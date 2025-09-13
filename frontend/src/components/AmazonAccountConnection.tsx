import { useState, useEffect } from 'react'
import { useUser } from '@clerk/clerk-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { 
  Link, 
  Unlink, 
  CheckCircle, 
  AlertCircle, 
  Clock,
  ShoppingBag,
  Globe,
  DollarSign,
  RefreshCw,
  Plus,
  Trash2
} from 'lucide-react'
import { toast } from '@/hooks/use-toast'

interface AmazonAccount {
  profile_id: number
  country_code: string
  currency_code: string
  account_name?: string
  connected: boolean
  needs_refresh: boolean
  expires_at?: string
  last_updated?: string
  error?: string
}

interface ConnectionStatus {
  user_id: string
  total_connections: number
  connections: AmazonAccount[]
  checked_at: string
}

export function AmazonAccountConnection() {
  const { user } = useUser()
  const [isConnecting, setIsConnecting] = useState(false)
  const [isLoadingStatus, setIsLoadingStatus] = useState(true)
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load connection status on component mount
  useEffect(() => {
    if (user?.id) {
      loadConnectionStatus()
    }
  }, [user?.id])

  const loadConnectionStatus = async () => {
    if (!user?.id) return

    try {
      setIsLoadingStatus(true)
      setError(null)

      const response = await fetch(`/api/v1/auth/amazon/status/${user.id}`, {
        headers: {
          'X-Admin-Key': process.env.NEXT_PUBLIC_ADMIN_KEY || '',
        },
      })

      if (response.ok) {
        const data = await response.json()
        setConnectionStatus(data)
      } else {
        const errorData = await response.json()
        setError(errorData.error?.message || 'Failed to load connection status')
      }
    } catch (err) {
      setError('Network error loading connection status')
      console.error('Error loading connection status:', err)
    } finally {
      setIsLoadingStatus(false)
    }
  }

  const initiateConnection = async () => {
    if (!user?.id) return

    try {
      setIsConnecting(true)
      setError(null)

      const response = await fetch(`/api/v1/auth/amazon/connect/${user.id}`, {
        headers: {
          'X-Admin-Key': process.env.NEXT_PUBLIC_ADMIN_KEY || '',
        },
      })

      if (response.ok) {
        const data = await response.json()
        
        // Redirect to Amazon OAuth
        window.location.href = data.auth_url
      } else {
        const errorData = await response.json()
        setError(errorData.error?.message || 'Failed to initiate connection')
        toast({
          title: 'Connection Failed',
          description: errorData.error?.message || 'Failed to initiate Amazon connection',
          variant: 'destructive',
        })
      }
    } catch (err) {
      setError('Network error initiating connection')
      toast({
        title: 'Network Error',
        description: 'Failed to connect to server',
        variant: 'destructive',
      })
    } finally {
      setIsConnecting(false)
    }
  }

  const disconnectAccount = async (profileId: number) => {
    if (!user?.id) return

    try {
      const response = await fetch(`/api/v1/auth/amazon/disconnect/${user.id}/${profileId}`, {
        method: 'DELETE',
        headers: {
          'X-Admin-Key': process.env.NEXT_PUBLIC_ADMIN_KEY || '',
        },
      })

      if (response.ok) {
        toast({
          title: 'Account Disconnected',
          description: `Amazon account ${profileId} has been disconnected`,
        })
        
        // Reload status
        await loadConnectionStatus()
      } else {
        const errorData = await response.json()
        toast({
          title: 'Disconnection Failed',
          description: errorData.error?.message || 'Failed to disconnect account',
          variant: 'destructive',
        })
      }
    } catch (err) {
      toast({
        title: 'Network Error',
        description: 'Failed to disconnect account',
        variant: 'destructive',
      })
    }
  }

  const getConnectionStatusIcon = (account: AmazonAccount) => {
    if (!account.connected) {
      return <Unlink className="h-4 w-4 text-muted-foreground" />
    }
    if (account.error) {
      return <AlertCircle className="h-4 w-4 text-destructive" />
    }
    if (account.needs_refresh) {
      return <Clock className="h-4 w-4 text-yellow-500" />
    }
    return <CheckCircle className="h-4 w-4 text-green-500" />
  }

  const getConnectionStatusText = (account: AmazonAccount) => {
    if (!account.connected) return 'Not Connected'
    if (account.error) return 'Error'
    if (account.needs_refresh) return 'Needs Refresh'
    return 'Connected'
  }

  const getConnectionStatusVariant = (account: AmazonAccount) => {
    if (!account.connected) return 'secondary'
    if (account.error) return 'destructive'
    if (account.needs_refresh) return 'outline'
    return 'default'
  }

  const formatExpiryTime = (expiresAt?: string) => {
    if (!expiresAt) return 'Unknown'
    
    const expiry = new Date(expiresAt)
    const now = new Date()
    const diffMs = expiry.getTime() - now.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
    
    if (diffMs < 0) return 'Expired'
    if (diffHours > 0) return `${diffHours}h ${diffMinutes}m`
    return `${diffMinutes}m`
  }

  if (!user) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Amazon Account Connection</CardTitle>
          <CardDescription>
            Please sign in to manage your Amazon advertising account connections
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Main Connection Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <ShoppingBag className="h-5 w-5 text-orange-500" />
                Amazon Account Connection
              </CardTitle>
              <CardDescription>
                Connect your Amazon advertising accounts to access campaign data and insights
              </CardDescription>
            </div>
            <Button 
              onClick={initiateConnection}
              disabled={isConnecting}
              className="flex items-center gap-2"
            >
              {isConnecting ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              {isConnecting ? 'Connecting...' : 'Connect Account'}
            </Button>
          </div>
        </CardHeader>

        {error && (
          <CardContent className="pt-0">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          </CardContent>
        )}
      </Card>

      {/* Connected Accounts */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Connected Accounts</CardTitle>
              <CardDescription>
                {isLoadingStatus 
                  ? 'Loading account status...' 
                  : connectionStatus
                    ? `${connectionStatus.total_connections} account(s) connected`
                    : 'No accounts connected'
                }
              </CardDescription>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={loadConnectionStatus}
              disabled={isLoadingStatus}
            >
              <RefreshCw className={`h-4 w-4 ${isLoadingStatus ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {isLoadingStatus ? (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 bg-muted rounded-lg animate-pulse" />
                    <div className="space-y-1">
                      <div className="h-4 w-24 bg-muted rounded animate-pulse" />
                      <div className="h-3 w-32 bg-muted rounded animate-pulse" />
                    </div>
                  </div>
                  <div className="h-6 w-16 bg-muted rounded animate-pulse" />
                </div>
              ))}
            </div>
          ) : connectionStatus && connectionStatus.connections.length > 0 ? (
            <div className="space-y-3">
              {connectionStatus.connections.map((account) => (
                <div key={account.profile_id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 bg-orange-100 dark:bg-orange-900/20 rounded-lg flex items-center justify-center">
                      {getConnectionStatusIcon(account)}
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">
                          {account.account_name || `Profile ${account.profile_id}`}
                        </span>
                        <Badge variant={getConnectionStatusVariant(account)}>
                          {getConnectionStatusText(account)}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Globe className="h-3 w-3" />
                          {account.country_code}
                        </span>
                        <span className="flex items-center gap-1">
                          <DollarSign className="h-3 w-3" />
                          {account.currency_code}
                        </span>
                        {account.expires_at && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Expires in {formatExpiryTime(account.expires_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => disconnectAccount(account.profile_id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <ShoppingBag className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No Amazon accounts connected</p>
              <p className="text-sm">Click "Connect Account" above to get started</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>How to Connect</CardTitle>
          <CardDescription>
            Follow these steps to connect your Amazon advertising account
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-4 border rounded-lg">
              <div className="h-8 w-8 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">1</span>
              </div>
              <h4 className="font-medium mb-1">Click Connect</h4>
              <p className="text-sm text-muted-foreground">
                Click the "Connect Account" button above
              </p>
            </div>
            
            <div className="text-center p-4 border rounded-lg">
              <div className="h-8 w-8 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">2</span>
              </div>
              <h4 className="font-medium mb-1">Authorize</h4>
              <p className="text-sm text-muted-foreground">
                Sign in to Amazon and grant permissions
              </p>
            </div>
            
            <div className="text-center p-4 border rounded-lg">
              <div className="h-8 w-8 bg-purple-100 dark:bg-purple-900/20 rounded-full flex items-center justify-center mx-auto mb-2">
                <span className="text-sm font-semibold text-purple-600 dark:text-purple-400">3</span>
              </div>
              <h4 className="font-medium mb-1">Start Using</h4>
              <p className="text-sm text-muted-foreground">
                Access your campaign data and insights
              </p>
            </div>
          </div>
          
          <Separator />
          
          <div className="space-y-2">
            <h5 className="font-medium text-sm">Required Permissions</h5>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Access to advertising campaigns and performance data</li>
              <li>• Read account information and profiles</li>
              <li>• Generate reports and download insights</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}