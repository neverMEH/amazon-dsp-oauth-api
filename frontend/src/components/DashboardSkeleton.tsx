import { Skeleton } from '@/components/ui/skeleton'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

export function DashboardHeaderSkeleton() {
  return (
    <div className="sticky top-0 z-50 w-full border-b bg-background/95">
      <div className="container flex h-16 items-center px-4 lg:px-6">
        <div className="flex items-center space-x-2 mr-6">
          <Skeleton className="w-8 h-8 rounded-lg" />
          <Skeleton className="h-5 w-24 hidden sm:block" />
        </div>
        
        <div className="hidden lg:flex items-center space-x-1 mr-6">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-20" />
        </div>
        
        <div className="hidden md:flex flex-1 max-w-sm mr-4">
          <Skeleton className="h-9 w-full" />
        </div>
        
        <div className="flex items-center space-x-3 ml-auto">
          <Skeleton className="h-9 w-9" />
          <Skeleton className="h-9 w-9" />
          <Skeleton className="h-9 w-32" />
        </div>
      </div>
    </div>
  )
}

export function StatsCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, index) => (
        <Card key={index}>
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
      ))}
    </div>
  )
}

export function AccountSwitcherSkeleton() {
  return <Skeleton className="h-10 w-64" />
}

export function DashboardContentSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <AccountSwitcherSkeleton />
      </div>
      
      <StatsCardsSkeleton />
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <Skeleton className="h-6 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-20" />
            </div>
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="flex items-center space-x-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1">
                    <Skeleton className="h-4 w-32 mb-1" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <Skeleton className="h-6 w-16" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-24 mb-2" />
            <Skeleton className="h-4 w-32" />
          </CardHeader>
          <CardContent className="space-y-4">
            {Array.from({ length: 3 }).map((_, index) => (
              <div key={index} className="space-y-2">
                <div className="flex items-center justify-between">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <Skeleton className="h-2 w-full" />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export function FullDashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800">
      <DashboardHeaderSkeleton />
      <div className="container mx-auto p-6">
        <DashboardContentSkeleton />
      </div>
    </div>
  )
}