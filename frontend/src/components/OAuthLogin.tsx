import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { LogIn, ExternalLink, Shield, Key, RefreshCw, Info, CheckCircle2 } from 'lucide-react';
import { api } from '@/services/api';
import { cn } from '@/lib/utils';

export function OAuthLogin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [healthCheck, setHealthCheck] = useState<'checking' | 'healthy' | 'error'>('checking');
  const navigate = useNavigate();
  const loginButtonRef = useRef<HTMLButtonElement>(null);

  // Check API health on component mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.getHealth();
        setHealthCheck('healthy');
      } catch {
        setHealthCheck('error');
      }
    };
    checkHealth();

    // Focus the login button when component mounts
    loginButtonRef.current?.focus();
  }, []);

  const handleLogin = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Generate a random state for CSRF protection
      const state = Math.random().toString(36).substring(7);
      sessionStorage.setItem('oauth_state', state);
      
      // Get the auth URL from the backend
      const authUrl = await api.initiateLogin(state);
      
      // Redirect to Amazon's OAuth page
      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate login');
      setLoading(false);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !loading && healthCheck === 'healthy') {
      handleLogin();
    }
  };

  return (
    <TooltipProvider>
      <div 
        className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4"
        onKeyDown={handleKeyDown}
      >
        <Card className="w-full max-w-md shadow-xl">
          <CardHeader className="text-center space-y-1">
            <div className="mx-auto mb-4 h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center animate-in fade-in zoom-in duration-500">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <CardTitle className="text-2xl font-bold">Amazon DSP OAuth</CardTitle>
            <CardDescription>
              Connect your Amazon Advertising account securely
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* API Status Indicator */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-muted/50">
              <span className="text-sm font-medium">API Status</span>
              {healthCheck === 'checking' ? (
                <Skeleton className="h-5 w-20" />
              ) : healthCheck === 'healthy' ? (
                <Badge variant="outline" className="text-green-600 border-green-600">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Online
                </Badge>
              ) : (
                <Badge variant="destructive">
                  Offline
                </Badge>
              )}
            </div>

            {error && (
              <Alert variant="destructive" className="animate-in slide-in-from-top-2">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <div className="space-y-3">
              <div className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <Key className="h-4 w-4 flex-shrink-0" />
                <span>Secure OAuth 2.0 authentication</span>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Info className="h-3 w-3 cursor-help" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="text-xs max-w-xs">
                      OAuth 2.0 is the industry-standard protocol for authorization, 
                      ensuring your credentials are handled securely.
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <RefreshCw className="h-4 w-4 flex-shrink-0" />
                <span>Automatic token refresh</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <Shield className="h-4 w-4 flex-shrink-0" />
                <span>Your credentials are never stored</span>
              </div>
            </div>

            <Button 
              ref={loginButtonRef}
              onClick={handleLogin} 
              disabled={loading || healthCheck === 'error'}
              className={cn(
                "w-full transition-all",
                loading && "animate-pulse"
              )}
              size="lg"
              aria-label="Login with Amazon"
            >
              {loading ? (
                <>
                  <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                  Redirecting to Amazon...
                </>
              ) : (
                <>
                  <LogIn className="mr-2 h-4 w-4" />
                  Login with Amazon
                  <ExternalLink className="ml-2 h-3 w-3" />
                </>
              )}
            </Button>

            {healthCheck === 'error' && (
              <Alert variant="destructive">
                <AlertDescription>
                  Unable to connect to the API. Please check your connection and try again.
                </AlertDescription>
              </Alert>
            )}

            <div className="flex items-center justify-center gap-2">
              <Badge variant="outline" className="text-xs">
                API v1.0.0
              </Badge>
              <Badge variant="outline" className="text-xs">
                Amazon DSP
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </TooltipProvider>
  );
}