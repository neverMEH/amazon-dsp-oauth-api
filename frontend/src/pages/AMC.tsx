import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Database,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Clock,
  Server,
  Activity,
  Users,
  Calendar,
  Settings,
  ExternalLink
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { useToast } from '@/components/ui/use-toast';

interface AMCInstance {
  instanceId: string;
  instanceName: string;
  instanceType: string;
  region: string;
  status: 'ACTIVE' | 'PROVISIONING' | 'SUSPENDED';
  dataRetentionDays: number;
  createdDate: string;
  advertisers: Array<{
    advertiserId: string;
    advertiserName: string;
  }>;
}

export default function AMC() {
  const [instances, setInstances] = useState<AMCInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const { toast } = useToast();

  const fetchAMCInstances = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/accounts/amc-instances', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('AMC access requires special provisioning. Please contact Amazon support.');
        }
        throw new Error('Failed to fetch AMC instances');
      }

      const data = await response.json();
      setInstances(data.instances || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load AMC instances');
      console.error('Error fetching AMC instances:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchAMCInstances();
    setRefreshing(false);
    toast({
      title: "Refreshed",
      description: "AMC instances have been refreshed",
    });
  };

  useEffect(() => {
    fetchAMCInstances();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ACTIVE':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'PROVISIONING':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'SUSPENDED':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Amazon Marketing Cloud</h1>
            <p className="text-muted-foreground">Manage your AMC instances and data workflows</p>
          </div>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-4 w-32 mb-2" />
                <Skeleton className="h-3 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold">Amazon Marketing Cloud</h1>
            <p className="text-muted-foreground">Manage your AMC instances and data workflows</p>
          </div>
        </div>
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
        <div className="mt-4">
          <Button onClick={fetchAMCInstances} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  if (instances.length === 0) {
    return (
      <div className="container mx-auto py-6">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-3xl font-bold">Amazon Marketing Cloud</h1>
            <p className="text-muted-foreground">Manage your AMC instances and data workflows</p>
          </div>
          <Button onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={cn("mr-2 h-4 w-4", refreshing && "animate-spin")} />
            Refresh
          </Button>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No AMC Instances Found</h3>
            <p className="text-muted-foreground text-center max-w-md">
              You don't have any AMC instances provisioned yet. AMC requires special provisioning from Amazon.
              Contact your Amazon representative to get started.
            </p>
            <div className="mt-6 flex gap-3">
              <Button variant="outline" onClick={handleRefresh}>
                <RefreshCw className="mr-2 h-4 w-4" />
                Check Again
              </Button>
              <Button variant="default" asChild>
                <a href="https://advertising.amazon.com/API/docs/en-us/guides/amazon-marketing-cloud/overview" target="_blank" rel="noopener noreferrer">
                  Learn More
                  <ExternalLink className="ml-2 h-4 w-4" />
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Amazon Marketing Cloud</h1>
          <p className="text-muted-foreground">Manage your AMC instances and data workflows</p>
        </div>
        <Button onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={cn("mr-2 h-4 w-4", refreshing && "animate-spin")} />
          Refresh
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {instances.map((instance, index) => (
          <motion.div
            key={instance.instanceId}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="h-full hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{instance.instanceName}</CardTitle>
                    <CardDescription className="text-xs mt-1">
                      {instance.instanceId}
                    </CardDescription>
                  </div>
                  <Badge className={cn("ml-2", getStatusColor(instance.status))}>
                    {instance.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Region</p>
                      <p className="font-medium">{instance.region}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Retention</p>
                      <p className="font-medium">{instance.dataRetentionDays} days</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Type</p>
                      <p className="font-medium">{instance.instanceType}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Created</p>
                      <p className="font-medium">
                        {new Date(instance.createdDate).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>

                {instance.advertisers.length > 0 && (
                  <div className="border-t pt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Users className="h-4 w-4 text-muted-foreground" />
                      <p className="text-sm font-medium">Linked Advertisers</p>
                    </div>
                    <div className="space-y-1">
                      {instance.advertisers.slice(0, 3).map((advertiser) => (
                        <div key={advertiser.advertiserId} className="text-xs text-muted-foreground">
                          {advertiser.advertiserName}
                        </div>
                      ))}
                      {instance.advertisers.length > 3 && (
                        <div className="text-xs text-muted-foreground">
                          +{instance.advertisers.length - 3} more
                        </div>
                      )}
                    </div>
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    <Settings className="mr-2 h-3 w-3" />
                    Configure
                  </Button>
                  <Button variant="default" size="sm" className="flex-1">
                    <Activity className="mr-2 h-3 w-3" />
                    Workflows
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}