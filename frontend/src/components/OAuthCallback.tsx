import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw, CheckCircle, XCircle, ArrowLeft } from 'lucide-react';
import { api } from '@/services/api';
import { cn } from '@/lib/utils';

export function OAuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      const state = searchParams.get('state');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      if (error) {
        setStatus('error');
        setError(errorDescription || error);
        return;
      }

      if (!code) {
        setStatus('error');
        setError('No authorization code received');
        return;
      }

      // Verify state for CSRF protection
      const savedState = sessionStorage.getItem('oauth_state');
      if (state && state !== savedState) {
        setStatus('error');
        setError('Invalid state parameter - possible CSRF attack');
        return;
      }

      try {
        const tokens = await api.handleCallback(code, state || undefined);
        
        // Store tokens in session storage
        sessionStorage.setItem('tokens', JSON.stringify(tokens));
        sessionStorage.removeItem('oauth_state');
        
        setStatus('success');
        
        // Redirect to dashboard after a short delay
        setTimeout(() => {
          navigate('/dashboard', { state: { tokens } });
        }, 1500);
      } catch (err) {
        setStatus('error');
        setError(err instanceof Error ? err.message : 'Failed to exchange code for tokens');
      }
    };

    handleCallback();
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-xl">
        <CardHeader className="text-center">
          <CardTitle>
            {status === 'loading' && 'Processing Authentication'}
            {status === 'success' && 'Authentication Successful'}
            {status === 'error' && 'Authentication Failed'}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === 'loading' && (
            <div className="space-y-6 py-8">
              <div className="flex justify-center">
                <div className="relative">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <div className="absolute inset-0 h-8 w-8 animate-ping rounded-full bg-primary opacity-20" />
                </div>
              </div>
              
              <div className="space-y-3">
                <p className="text-center text-muted-foreground">
                  Exchanging authorization code for tokens...
                </p>
                
                {/* Loading steps indicator */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-green-600" />
                    <span className="text-sm">Authorization code received</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 animate-spin text-primary" />
                    <span className="text-sm">Exchanging for access tokens...</span>
                  </div>
                  <div className="flex items-center gap-2 opacity-50">
                    <div className="h-4 w-4 rounded-full border-2 border-muted" />
                    <span className="text-sm">Redirecting to dashboard</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center space-y-4 py-8">
              <div className={cn(
                "rounded-full bg-green-100 dark:bg-green-900/30 p-3",
                "animate-in zoom-in duration-300"
              )}>
                <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              <div className="text-center space-y-2">
                <p className="font-semibold text-lg">All Set!</p>
                <p className="text-muted-foreground">Redirecting to your dashboard...</p>
                <div className="flex justify-center mt-4">
                  <Skeleton className="h-2 w-32 animate-pulse" />
                </div>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-4">
              <div className="flex flex-col items-center space-y-4 py-8">
                <div className={cn(
                  "rounded-full bg-red-100 dark:bg-red-900/30 p-3",
                  "animate-in zoom-in duration-300"
                )}>
                  <XCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-lg">Something went wrong</p>
                  <p className="text-muted-foreground text-sm mt-1">
                    We couldn't complete the authentication process
                  </p>
                </div>
              </div>
              
              <Alert variant="destructive" className="animate-in slide-in-from-bottom-2">
                <AlertDescription className="text-sm">{error}</AlertDescription>
              </Alert>

              <div className="flex justify-center">
                <Button 
                  onClick={() => navigate('/')}
                  variant="outline"
                  className="gap-2"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Return to login
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}