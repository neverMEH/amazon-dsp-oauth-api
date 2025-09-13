import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Copy, 
  RefreshCw, 
  LogOut, 
  Clock, 
  CheckCircle,
  AlertCircle,
  Eye,
  EyeOff
} from 'lucide-react';
import { api, TokenResponse } from '@/services/api';

interface TokenDashboardProps {
  tokens: TokenResponse;
}

export function TokenDashboard({ tokens: initialTokens }: TokenDashboardProps) {
  const [tokens, setTokens] = useState<TokenResponse>(initialTokens);
  const [refreshing, setRefreshing] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [showTokens, setShowTokens] = useState(false);
  const [tokenInfo, setTokenInfo] = useState<any>(null);
  const [expiresIn, setExpiresIn] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    // Decode and display token information
    if (tokens.access_token) {
      const decoded = api.decodeToken(tokens.access_token);
      setTokenInfo(decoded);
    }

    // Update expiration time
    const updateExpiration = () => {
      if (tokens.expires_in) {
        const now = Date.now();
        const expirationTime = now + (tokens.expires_in * 1000);
        const timeLeft = expirationTime - Date.now();
        
        if (timeLeft > 0) {
          const hours = Math.floor(timeLeft / (1000 * 60 * 60));
          const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
          setExpiresIn(`${hours}h ${minutes}m`);
        } else {
          setExpiresIn('Expired');
        }
      }
    };

    updateExpiration();
    const interval = setInterval(updateExpiration, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [tokens]);

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      const newTokens = await api.refreshToken(tokens.refresh_token);
      setTokens(newTokens);
      
      // Store in session for persistence
      sessionStorage.setItem('tokens', JSON.stringify(newTokens));
    } catch (error) {
      console.error('Failed to refresh token:', error);
    } finally {
      setRefreshing(false);
    }
  };

  const handleCopy = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopied(type);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleLogout = () => {
    sessionStorage.removeItem('tokens');
    sessionStorage.removeItem('oauth_state');
    navigate('/');
  };

  const maskToken = (token: string) => {
    if (showTokens) return token;
    return token.substring(0, 20) + '...' + token.substring(token.length - 10);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Token Dashboard</h1>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>

        <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle>Successfully Authenticated</AlertTitle>
          <AlertDescription>
            Your Amazon DSP OAuth tokens have been retrieved successfully.
          </AlertDescription>
        </Alert>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle>Access Token</CardTitle>
                <CardDescription>Use this token to make API requests</CardDescription>
              </div>
              <div className="flex items-center space-x-2">
                <Badge variant={expiresIn === 'Expired' ? 'destructive' : 'secondary'}>
                  <Clock className="mr-1 h-3 w-3" />
                  {expiresIn}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowTokens(!showTokens)}
                >
                  {showTokens ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <code className="flex-1 p-3 bg-muted rounded-md text-sm font-mono break-all">
                {maskToken(tokens.access_token)}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() => handleCopy(tokens.access_token, 'access')}
              >
                {copied === 'access' ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>

            {tokenInfo && (
              <div className="space-y-2 pt-4 border-t">
                <h4 className="text-sm font-medium">Token Information</h4>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {tokenInfo.iss && (
                    <div>
                      <span className="text-muted-foreground">Issuer:</span>
                      <span className="ml-2 font-mono">{tokenInfo.iss}</span>
                    </div>
                  )}
                  {tokenInfo.sub && (
                    <div>
                      <span className="text-muted-foreground">Subject:</span>
                      <span className="ml-2 font-mono">{tokenInfo.sub}</span>
                    </div>
                  )}
                  {tokenInfo.aud && (
                    <div>
                      <span className="text-muted-foreground">Audience:</span>
                      <span className="ml-2 font-mono">{tokenInfo.aud}</span>
                    </div>
                  )}
                  {tokenInfo.scope && (
                    <div className="col-span-2">
                      <span className="text-muted-foreground">Scopes:</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {tokenInfo.scope.split(' ').map((scope: string) => (
                          <Badge key={scope} variant="outline" className="text-xs">
                            {scope}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle>Refresh Token</CardTitle>
                <CardDescription>Use this to get new access tokens</CardDescription>
              </div>
              <Button 
                onClick={handleRefresh} 
                disabled={refreshing}
                size="sm"
              >
                {refreshing ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Refreshing...
                  </>
                ) : (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Refresh Now
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <code className="flex-1 p-3 bg-muted rounded-md text-sm font-mono break-all">
                {maskToken(tokens.refresh_token)}
              </code>
              <Button
                variant="outline"
                size="icon"
                onClick={() => handleCopy(tokens.refresh_token, 'refresh')}
              >
                {copied === 'refresh' ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>API Configuration</CardTitle>
            <CardDescription>Use these settings in your application</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between items-center p-3 bg-muted rounded-md">
                <span className="text-sm font-medium">Token Type</span>
                <Badge>{tokens.token_type}</Badge>
              </div>
              <div className="flex justify-between items-center p-3 bg-muted rounded-md">
                <span className="text-sm font-medium">Expires In</span>
                <Badge variant="outline">{tokens.expires_in} seconds</Badge>
              </div>
              {tokens.scope && (
                <div className="p-3 bg-muted rounded-md">
                  <span className="text-sm font-medium">Scopes</span>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {tokens.scope.split(' ').map((scope) => (
                      <Badge key={scope} variant="secondary" className="text-xs">
                        {scope}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Security Note</AlertTitle>
              <AlertDescription>
                Never share your tokens publicly or commit them to version control. 
                Always use environment variables or secure storage for production applications.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}