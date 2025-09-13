import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  Wifi, 
  WifiOff, 
  AlertCircle, 
  CheckCircle, 
  RefreshCw,
  Clock,
  Signal
} from 'lucide-react'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

type ConnectionStatus = 'online' | 'offline' | 'poor' | 'checking'

interface ApiStatus {
  status: 'healthy' | 'degraded' | 'down'
  response_time: number
  last_check: string
  services: {
    database: boolean
    amazon_api: boolean
    auth_service: boolean
  }
}

export function ConnectionStatusIndicator({ className }: { className?: string }) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking')
  const [apiStatus, setApiStatus] = useState<ApiStatus | null>(null)
  const [lastCheck, setLastCheck] = useState<Date>(new Date())
  const { toast } = useToast()

  const checkConnection = async () => {
    try {
      setConnectionStatus('checking')
      
      // Check network connectivity
      if (!navigator.onLine) {
        setConnectionStatus('offline')
        return
      }

      // Check API health
      const startTime = Date.now()
      const response = await fetch('/api/v1/health', {
        method: 'GET',
        cache: 'no-cache',
      })
      const responseTime = Date.now() - startTime

      if (response.ok) {
        const data = await response.json()
        setApiStatus({
          ...data,
          response_time: responseTime,
        })
        
        if (responseTime > 2000) {
          setConnectionStatus('poor')
        } else {
          setConnectionStatus('online')
        }
      } else {
        setConnectionStatus('offline')
      }
    } catch (error) {
      console.error('Connection check failed:', error)
      setConnectionStatus('offline')
    } finally {
      setLastCheck(new Date())
    }
  }

  useEffect(() => {
    checkConnection()

    // Check connection every 30 seconds
    const interval = setInterval(checkConnection, 30000)

    // Listen for online/offline events
    const handleOnline = () => {
      setConnectionStatus('online')
      checkConnection()
      toast({
        title: 'Connection Restored',
        description: 'You are back online.',
      })
    }

    const handleOffline = () => {
      setConnectionStatus('offline')
      toast({
        variant: 'destructive',
        title: 'Connection Lost',
        description: 'You are currently offline.',
      })
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      clearInterval(interval)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [toast])

  const getStatusIcon = () => {
    switch (connectionStatus) {
      case 'online':
        return <CheckCircle className="h-4 w-4" />
      case 'offline':
        return <WifiOff className="h-4 w-4" />
      case 'poor':
        return <Signal className="h-4 w-4" />
      case 'checking':
        return <RefreshCw className="h-4 w-4 animate-spin" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'online':
        return 'bg-green-500'
      case 'offline':
        return 'bg-red-500'
      case 'poor':
        return 'bg-yellow-500'
      case 'checking':
        return 'bg-blue-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'online':
        return 'Connected'
      case 'offline':
        return 'Offline'
      case 'poor':
        return 'Poor Connection'
      case 'checking':
        return 'Checking...'
      default:
        return 'Unknown'
    }
  }

  const formatResponseTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  return (
    <div className={cn('flex items-center space-x-3', className)}>
      {/* Compact Status Badge */}
      <Badge 
        variant={connectionStatus === 'online' ? 'default' : 'destructive'}
        className={cn(
          'flex items-center space-x-1 px-2 py-1 text-xs',
          connectionStatus === 'online' && 'bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-300',
          connectionStatus === 'poor' && 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-900/20 dark:text-yellow-300'
        )}
      >
        <div className={cn('w-2 h-2 rounded-full', getStatusColor())} />
        <span>{getStatusText()}</span>
        {getStatusIcon()}
      </Badge>

      {/* Detailed Status (when expanded) */}
      {apiStatus && connectionStatus === 'online' && (
        <div className="hidden lg:flex items-center space-x-2 text-xs text-muted-foreground">
          <span>{formatResponseTime(apiStatus.response_time)}</span>
          {apiStatus.services.database && apiStatus.services.amazon_api && apiStatus.services.auth_service && (
            <CheckCircle className="h-3 w-3 text-green-500" />
          )}
        </div>
      )}

      <Button
        variant="ghost"
        size="sm"
        onClick={checkConnection}
        disabled={connectionStatus === 'checking'}
        className="h-6 w-6 p-0"
      >
        <RefreshCw className={cn('h-3 w-3', connectionStatus === 'checking' && 'animate-spin')} />
      </Button>
    </div>
  )
}

export function DetailedConnectionStatus() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('checking')
  const [apiStatus, setApiStatus] = useState<ApiStatus | null>(null)

  const checkConnection = async () => {
    try {
      setConnectionStatus('checking')
      
      if (!navigator.onLine) {
        setConnectionStatus('offline')
        return
      }

      const startTime = Date.now()
      const response = await fetch('/api/v1/health', {
        method: 'GET',
        cache: 'no-cache',
      })
      const responseTime = Date.now() - startTime

      if (response.ok) {
        const data = await response.json()
        setApiStatus({
          ...data,
          response_time: responseTime,
        })
        
        if (responseTime > 2000) {
          setConnectionStatus('poor')
        } else {
          setConnectionStatus('online')
        }
      } else {
        setConnectionStatus('offline')
      }
    } catch (error) {
      console.error('Connection check failed:', error)
      setConnectionStatus('offline')
    }
  }

  useEffect(() => {
    checkConnection()
    const interval = setInterval(checkConnection, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Wifi className="h-5 w-5" />
          System Status
        </CardTitle>
        <CardDescription>
          Real-time status of all system components
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {connectionStatus === 'offline' ? (
          <Alert variant="destructive">
            <WifiOff className="h-4 w-4" />
            <AlertDescription>
              You are currently offline. Some features may not be available.
            </AlertDescription>
          </Alert>
        ) : apiStatus ? (
          <>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">API Response</span>
              <Badge variant={apiStatus.response_time > 1000 ? 'secondary' : 'default'}>
                {apiStatus.response_time}ms
              </Badge>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm">Database</span>
                <div className="flex items-center space-x-1">
                  {apiStatus.services.database ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-xs text-muted-foreground">
                    {apiStatus.services.database ? 'Healthy' : 'Down'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Amazon API</span>
                <div className="flex items-center space-x-1">
                  {apiStatus.services.amazon_api ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-xs text-muted-foreground">
                    {apiStatus.services.amazon_api ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-sm">Authentication</span>
                <div className="flex items-center space-x-1">
                  {apiStatus.services.auth_service ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span className="text-xs text-muted-foreground">
                    {apiStatus.services.auth_service ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="pt-2 border-t">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Last checked:</span>
                <span className="flex items-center space-x-1">
                  <Clock className="h-3 w-3" />
                  <span>{new Date(apiStatus.last_check).toLocaleTimeString()}</span>
                </span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center p-4">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}
      </CardContent>
    </Card>
  )
}