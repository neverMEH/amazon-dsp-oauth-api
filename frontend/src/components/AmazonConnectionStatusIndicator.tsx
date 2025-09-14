import { useState, useEffect } from 'react'
import { useUser } from '@clerk/clerk-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { 
  CheckCircle, 
  AlertCircle, 
  Clock,
  Unlink,
  RefreshCw,
  AlertTriangle
} from 'lucide-react'

interface ConnectionStatus {
  connected: boolean
  profile_id?: number
  needs_refresh: boolean
  expires_at?: string
  last_updated?: string
  error?: string
  total_connections: number
}

interface AmazonConnectionStatusIndicatorProps {
  showDetails?: boolean
  onRefresh?: () => void
  refreshing?: boolean
}

export function AmazonConnectionStatusIndicator({ 
  showDetails = false, 
  onRefresh,
  refreshing = false 
}: AmazonConnectionStatusIndicatorProps) {
  const { user } = useUser()
  const [status, setStatus] = useState<ConnectionStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user?.id) {
      loadConnectionStatus()
    }
  }, [user?.id])

  const loadConnectionStatus = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch(`/api/v1/auth/amazon/status/${user.id}`, {
        headers: {
          'X-Admin-Key': process.env.NEXT_PUBLIC_ADMIN_KEY || '',
        },
      })

      if (response.ok) {
        const data = await response.json()
        
        // Calculate overall status from connections
        const overallStatus: ConnectionStatus = {
          connected: data.total_connections > 0,
          total_connections: data.total_connections,
          needs_refresh: false,
          error: undefined
        }

        // Check if any connection needs refresh or has errors
        if (data.connections && data.connections.length > 0) {
          const hasErrors = data.connections.some((conn: any) => conn.error)
          const needsRefresh = data.connections.some((conn: any) => conn.needs_refresh)
          
          overallStatus.needs_refresh = needsRefresh
          if (hasErrors) {
            overallStatus.error = 'Some connections have errors'
          }

          // Use first connection's details for single connection scenarios
          if (data.connections.length === 1) {
            const conn = data.connections[0]
            overallStatus.profile_id = conn.profile_id
            overallStatus.expires_at = conn.expires_at
            overallStatus.last_updated = conn.last_updated
            overallStatus.error = conn.error
          }
        }

        setStatus(overallStatus)
      } else {
        setError('Failed to load connection status')
      }
    } catch (err) {
      setError('Network error')
      console.error('Error loading connection status:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRefresh = () => {
    if (onRefresh) {
      onRefresh()
    } else {
      loadConnectionStatus()
    }
  }

  const getStatusIcon = () => {
    if (isLoading || refreshing) {
      return <RefreshCw className="h-3 w-3 animate-spin" />
    }
    
    if (error || status?.error) {
      return <AlertCircle className="h-3 w-3" />
    }
    
    if (!status?.connected) {
      return <Unlink className="h-3 w-3" />
    }
    
    if (status.needs_refresh) {
      return <Clock className="h-3 w-3" />
    }
    
    return <CheckCircle className="h-3 w-3" />
  }

  const getStatusText = () => {
    if (isLoading || refreshing) return 'Loading...'
    if (error) return 'Error'
    if (!status?.connected) return 'Not Connected'
    if (status.error) return 'Error'
    if (status.needs_refresh) return 'Needs Refresh'
    return `${status.total_connections} Connected`
  }

  const getStatusVariant = (): 'default' | 'secondary' | 'destructive' | 'outline' => {
    if (isLoading || refreshing) return 'secondary'
    if (error || status?.error) return 'destructive'
    if (!status?.connected) return 'secondary'
    if (status.needs_refresh) return 'outline'
    return 'default'
  }

  const getStatusColor = () => {
    if (isLoading || refreshing) return 'text-muted-foreground'
    if (error || status?.error) return 'text-red-500'
    if (!status?.connected) return 'text-muted-foreground'
    if (status.needs_refresh) return 'text-yellow-500'
    return 'text-green-500'
  }

  const getTooltipContent = () => {
    if (isLoading || refreshing) return 'Loading connection status...'
    if (error) return `Error: ${error}`
    if (!status?.connected) return 'No Amazon accounts connected'
    if (status.error) return `Connection error: ${status.error}`
    if (status.needs_refresh) return 'Some connections need token refresh'
    
    let content = `${status.total_connections} Amazon account${status.total_connections > 1 ? 's' : ''} connected`
    if (status.expires_at) {
      const expiry = new Date(status.expires_at)
      const now = new Date()
      const diffHours = Math.floor((expiry.getTime() - now.getTime()) / (1000 * 60 * 60))
      content += `\nExpires in ${diffHours}h`
    }
    return content
  }

  if (!showDetails) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge 
              variant={getStatusVariant()}
              className="cursor-pointer select-none"
              onClick={handleRefresh}
            >
              <span className={getStatusColor()}>
                {getStatusIcon()}
              </span>
              <span className="ml-1.5">{getStatusText()}</span>
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p className="whitespace-pre-line">{getTooltipContent()}</p>
            <p className="text-xs text-muted-foreground mt-1">Click to refresh</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <span className={getStatusColor()}>
          {getStatusIcon()}
        </span>
        <span className="text-sm font-medium">
          Amazon Connection
        </span>
        <Badge variant={getStatusVariant()}>
          {getStatusText()}
        </Badge>
      </div>
      
      {(status?.needs_refresh || status?.error) && (
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <AlertTriangle className="h-4 w-4 text-yellow-500" />
            </TooltipTrigger>
            <TooltipContent>
              {status?.needs_refresh && <p>Some tokens need refresh</p>}
              {status?.error && <p>Connection error detected</p>}
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}

      <Button
        variant="ghost"
        size="sm"
        onClick={handleRefresh}
        disabled={isLoading || refreshing}
        className="h-6 px-2"
      >
        <RefreshCw className={`h-3 w-3 ${(isLoading || refreshing) ? 'animate-spin' : ''}`} />
      </Button>
    </div>
  )
}

// Lightweight version for use in headers/navigation
export function AmazonConnectionBadge() {
  return <AmazonConnectionStatusIndicator showDetails={false} />
}

// Detailed version for use in dashboards/settings
export function AmazonConnectionDetails({ onRefresh, refreshing }: { onRefresh?: () => void, refreshing?: boolean }) {
  return <AmazonConnectionStatusIndicator showDetails={true} onRefresh={onRefresh} refreshing={refreshing} />
}