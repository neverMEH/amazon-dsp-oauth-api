import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { api } from '@/services/api';

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
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Processing Authentication</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {status === 'loading' && (
            <div className="flex flex-col items-center space-y-4 py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Exchanging authorization code for tokens...</p>
            </div>
          )}

          {status === 'success' && (
            <div className="flex flex-col items-center space-y-4 py-8">
              <div className="rounded-full bg-green-100 dark:bg-green-900 p-3">
                <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-lg">Authentication Successful!</p>
                <p className="text-muted-foreground mt-2">Redirecting to your dashboard...</p>
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="space-y-4">
              <div className="flex flex-col items-center space-y-4 py-8">
                <div className="rounded-full bg-red-100 dark:bg-red-900 p-3">
                  <XCircle className="h-8 w-8 text-red-600 dark:text-red-400" />
                </div>
                <div className="text-center">
                  <p className="font-semibold text-lg">Authentication Failed</p>
                </div>
              </div>
              
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>

              <div className="text-center">
                <a 
                  href="/" 
                  className="text-primary hover:underline text-sm"
                >
                  Return to login
                </a>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}