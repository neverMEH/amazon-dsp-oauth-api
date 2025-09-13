import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { 
  Users, 
  DollarSign, 
  Eye, 
  MousePointer, 
  Target,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react'
import { useDashboardStore } from '@/stores/dashboard'
import { dashboardAPI } from '@/services/dashboard-api'
import { useToast } from '@/components/ui/use-toast'
import { cn } from '@/lib/utils'

const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  } else if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)
}

interface StatsCardProps {
  title: string
  value: string | number
  description: string
  icon: React.ComponentType<any>
  trend?: {
    value: number
    isPositive: boolean
  }
  className?: string
}

function StatsCard({ title, value, description, icon: Icon, trend, className }: StatsCardProps) {
  const TrendIcon = trend?.isPositive ? TrendingUp : trend?.isPositive === false ? TrendingDown : Minus

  return (
    <Card className={cn('hover:shadow-md transition-shadow', className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-5 w-5 text-purple-600" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        <div className="flex items-center justify-between mt-2">
          <p className="text-xs text-muted-foreground">{description}</p>
          {trend && (
            <div className={cn(
              'flex items-center text-xs',
              trend.isPositive ? 'text-green-600' : 'text-red-600'
            )}>
              <TrendIcon className="h-3 w-3 mr-1" />
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function StatsCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-5" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-2" />
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-4 w-12" />
        </div>
      </CardContent>
    </Card>
  )
}

export function StatsCards() {
  const { stats, isLoading, error, setStats, setLoading, setError } = useDashboardStore()
  const { toast } = useToast()

  useEffect(() => {
    const loadStats = async () => {
      try {
        setLoading(true)
        setError(null)
        const statsData = await dashboardAPI.getUserStats()
        setStats(statsData)
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load statistics'
        setError(errorMessage)
        toast({
          variant: 'destructive',
          title: 'Error Loading Statistics',
          description: errorMessage,
        })
      } finally {
        setLoading(false)
      }
    }

    loadStats()
  }, [setStats, setLoading, setError, toast])

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <StatsCardSkeleton key={index} />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/10">
        <CardHeader>
          <CardTitle className="text-red-600">Error Loading Statistics</CardTitle>
          <CardDescription className="text-red-600">{error}</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  if (!stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>No Statistics Available</CardTitle>
          <CardDescription>Connect your Amazon DSP accounts to see statistics</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <StatsCard
        title="Total Accounts"
        value={stats.totalAccounts}
        description={`${stats.activeAccounts} active accounts`}
        icon={Users}
        trend={{
          value: 12,
          isPositive: true
        }}
      />
      
      <StatsCard
        title="Total Spend"
        value={formatCurrency(stats.totalSpend)}
        description="Last 30 days"
        icon={DollarSign}
        trend={{
          value: 8.5,
          isPositive: true
        }}
      />
      
      <StatsCard
        title="Impressions"
        value={formatNumber(stats.impressions)}
        description="Last 30 days"
        icon={Eye}
        trend={{
          value: 15.3,
          isPositive: true
        }}
      />
      
      <StatsCard
        title="Clicks"
        value={formatNumber(stats.clicks)}
        description={`${stats.conversions} conversions`}
        icon={MousePointer}
        trend={{
          value: 2.1,
          isPositive: false
        }}
      />
    </div>
  )
}