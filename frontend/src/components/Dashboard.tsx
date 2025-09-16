import { useUser } from '@clerk/clerk-react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Activity,
  Calendar,
  TrendingUp,
  Users,
  Settings,
  BarChart3,
  ArrowUpRight,
  ArrowDownRight,
  Plus,
  Database,
  Target,
  ShoppingCart
} from 'lucide-react'
import { DashboardHeader } from './DashboardHeader'
import { StatsCards } from './StatsCards'
import { AccountSwitcher } from './AccountSwitcher'
import { useDashboardStore } from '@/stores/dashboard'

// Mock data for recent activity
const recentActivity = [
  {
    id: '1',
    type: 'campaign_created',
    title: 'New Campaign Created',
    description: 'Holiday Sale Campaign launched successfully',
    timestamp: '2 hours ago',
    status: 'success'
  },
  {
    id: '2',
    type: 'budget_alert',
    title: 'Budget Alert',
    description: 'Campaign "Summer Sale" is at 90% of daily budget',
    timestamp: '4 hours ago',
    status: 'warning'
  },
  {
    id: '3',
    type: 'account_sync',
    title: 'Account Synced',
    description: 'US Marketplace data updated successfully',
    timestamp: '6 hours ago',
    status: 'info'
  },
  {
    id: '4',
    type: 'performance_alert',
    title: 'Performance Alert',
    description: 'CTR dropped 15% for Electronics category',
    timestamp: '8 hours ago',
    status: 'error'
  },
]

const performanceMetrics = [
  { label: 'CTR', value: '2.45%', change: 12.5, isPositive: true },
  { label: 'CPC', value: '$0.85', change: -8.2, isPositive: false },
  { label: 'ROAS', value: '4.2x', change: 15.8, isPositive: true },
]

function getActivityIcon(type: string) {
  switch (type) {
    case 'campaign_created':
      return <Plus className="h-4 w-4" />
    case 'budget_alert':
      return <Activity className="h-4 w-4" />
    case 'account_sync':
      return <Users className="h-4 w-4" />
    case 'performance_alert':
      return <TrendingUp className="h-4 w-4" />
    default:
      return <Activity className="h-4 w-4" />
  }
}

function getStatusColor(status: string) {
  switch (status) {
    case 'success':
      return 'text-green-600 bg-green-100 dark:bg-green-900/20'
    case 'warning':
      return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/20'
    case 'error':
      return 'text-red-600 bg-red-100 dark:bg-red-900/20'
    default:
      return 'text-blue-600 bg-blue-100 dark:bg-blue-900/20'
  }
}

export function Dashboard() {
  const { user } = useUser()
  const navigate = useNavigate()
  const { currentAccount } = useDashboardStore()

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800">
      <DashboardHeader />
      
      <div className="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Welcome Section */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Welcome back, {user?.firstName}!
            </h1>
            <p className="text-muted-foreground mt-1">
              Here's what's happening with your neverMEH campaigns today.
            </p>
          </div>
          <AccountSwitcher />
        </div>

        {/* Stats Cards */}
        <StatsCards />

        {/* Main Content */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Recent Activity
              </CardTitle>
              <CardDescription>
                Latest updates from your campaigns and accounts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="all" className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
                  <TabsTrigger value="alerts">Alerts</TabsTrigger>
                </TabsList>
                <TabsContent value="all" className="space-y-4 mt-4">
                  {recentActivity.map((activity) => (
                    <div key={activity.id} className="flex items-start space-x-4 p-4 rounded-lg border bg-muted/30">
                      <div className={`p-2 rounded-full ${getStatusColor(activity.status)}`}>
                        {getActivityIcon(activity.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-sm">{activity.title}</p>
                          <span className="text-xs text-muted-foreground">{activity.timestamp}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{activity.description}</p>
                      </div>
                    </div>
                  ))}
                </TabsContent>
                <TabsContent value="campaigns" className="mt-4">
                  <div className="text-center py-8 text-muted-foreground">
                    <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No recent campaign activity</p>
                  </div>
                </TabsContent>
                <TabsContent value="alerts" className="mt-4">
                  <div className="space-y-4">
                    {recentActivity.filter(a => a.status === 'warning' || a.status === 'error').map((activity) => (
                      <div key={activity.id} className="flex items-start space-x-4 p-4 rounded-lg border bg-muted/30">
                        <div className={`p-2 rounded-full ${getStatusColor(activity.status)}`}>
                          {getActivityIcon(activity.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-sm">{activity.title}</p>
                            <span className="text-xs text-muted-foreground">{activity.timestamp}</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{activity.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Performance Overview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Performance
              </CardTitle>
              <CardDescription>
                {currentAccount?.name || 'Overall'} metrics overview
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {performanceMetrics.map((metric) => (
                <div key={metric.label} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{metric.label}</span>
                    <span className="text-lg font-bold">{metric.value}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="flex-1 bg-muted rounded-full h-2">
                      <div 
                        className="h-2 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500"
                        style={{ width: '65%' }}
                      />
                    </div>
                    <div className={`flex items-center text-xs ${
                      metric.isPositive ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {metric.isPositive ? (
                        <ArrowUpRight className="h-3 w-3 mr-1" />
                      ) : (
                        <ArrowDownRight className="h-3 w-3 mr-1" />
                      )}
                      {Math.abs(metric.change)}%
                    </div>
                  </div>
                </div>
              ))}
              
              <div className="pt-4 border-t">
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={() => navigate('/accounts?type=amc')}
                >
                  <BarChart3 className="h-4 w-4 mr-2" />
                  View AMC Analytics
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Navigate to key areas and account types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-4">
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-green-50 hover:border-green-200 dark:hover:bg-green-950/20"
                onClick={() => navigate('/accounts?type=sponsored-ads')}
              >
                <Target className="h-6 w-6 text-green-600" />
                <span>Sponsored Ads</span>
                <span className="text-xs text-muted-foreground">Campaigns & Keywords</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-blue-50 hover:border-blue-200 dark:hover:bg-blue-950/20"
                onClick={() => navigate('/accounts?type=dsp')}
              >
                <Database className="h-6 w-6 text-blue-600" />
                <span>DSP</span>
                <span className="text-xs text-muted-foreground">Programmatic Ads</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-purple-50 hover:border-purple-200 dark:hover:bg-purple-950/20"
                onClick={() => navigate('/accounts?type=amc')}
              >
                <BarChart3 className="h-6 w-6 text-purple-600" />
                <span>AMC</span>
                <span className="text-xs text-muted-foreground">Analytics & Insights</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-orange-50 hover:border-orange-200 dark:hover:bg-orange-950/20"
                onClick={() => navigate('/accounts')}
              >
                <Users className="h-6 w-6 text-orange-600" />
                <span>All Accounts</span>
                <span className="text-xs text-muted-foreground">Manage Connections</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-slate-50 hover:border-slate-200 dark:hover:bg-slate-950/20"
                onClick={() => navigate('/settings')}
              >
                <Settings className="h-6 w-6 text-slate-600" />
                <span>Settings</span>
                <span className="text-xs text-muted-foreground">Preferences</span>
              </Button>
              <Button
                variant="outline"
                className="h-auto p-4 flex-col space-y-2 hover:bg-indigo-50 hover:border-indigo-200 dark:hover:bg-indigo-950/20"
                onClick={() => window.open('https://advertising.amazon.com', '_blank')}
              >
                <ShoppingCart className="h-6 w-6 text-indigo-600" />
                <span>Amazon Ads</span>
                <span className="text-xs text-muted-foreground">External Console</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}