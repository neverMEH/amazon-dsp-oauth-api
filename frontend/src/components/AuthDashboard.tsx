import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConnectionStatus } from '@/components/ConnectionStatus';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LogOut, RefreshCw, Shield, CheckCircle } from 'lucide-react';

export function AuthDashboard() {
  const navigate = useNavigate();
  const [authStatus, setAuthStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAuthStatus();
  }, []);

  const fetchAuthStatus = async () => {
    try {
      const response = await fetch('/api/v1/auth/status');
      const data = await response.json();
      setAuthStatus(data);
    } catch (error) {
      console.error('Failed to fetch auth status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    sessionStorage.clear();
    navigate('/');
  };

  const handleRefresh = async () => {
    try {
      const response = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
      });
      if (response.ok) {
        fetchAuthStatus();
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">OAuth Dashboard</h1>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>

        <ConnectionStatus />

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Authentication Status
            </CardTitle>
            <CardDescription>
              Your Amazon DSP OAuth connection details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {authStatus?.is_authenticated ? (
              <>
                <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800 dark:text-green-200">
                    Successfully authenticated with Amazon DSP
                  </AlertDescription>
                </Alert>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground mb-1">Token ID</div>
                    <div className="font-mono text-xs">{authStatus.token_id}</div>
                  </div>
                  
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground mb-1">Scope</div>
                    <Badge variant="secondary">{authStatus.scope}</Badge>
                  </div>
                  
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground mb-1">Refresh Count</div>
                    <div className="font-semibold">{authStatus.refresh_count || 0}</div>
                  </div>
                  
                  <div className="p-4 bg-muted rounded-lg">
                    <div className="text-sm text-muted-foreground mb-1">Status</div>
                    <Badge variant={authStatus.is_valid ? 'default' : 'destructive'}>
                      {authStatus.is_valid ? 'Valid' : 'Expired'}
                    </Badge>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button onClick={handleRefresh} variant="outline">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Manual Refresh
                  </Button>
                </div>
              </>
            ) : (
              <Alert>
                <AlertDescription>
                  No active authentication found. Please login again.
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}