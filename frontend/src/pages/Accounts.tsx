import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus,
  Settings,
  RefreshCw,
  Download,
  HelpCircle,
  Shield,
  Link2,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import { Badge } from '@/components/ui/badge';
import AmazonAccountsList from '@/components/account/AmazonAccountsList';
import { StoredAmazonAccount } from '@/types/amazonAdsAccount';
import { accountService } from '@/services/accountService';

const AccountsPage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [selectedAccount, setSelectedAccount] = useState<StoredAmazonAccount | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [showDisconnectDialog, setShowDisconnectDialog] = useState(false);
  const [accountToDisconnect, setAccountToDisconnect] = useState<string | null>(null);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'checking' | 'connected' | 'error'>('idle');
  const [hasAccounts, setHasAccounts] = useState(false);

  // Check Amazon connection status
  const checkConnectionStatus = useCallback(async () => {
    setConnectionStatus('checking');
    try {
      const token = await getAuthToken();
      if (!token) {
        setConnectionStatus('error');
        return;
      }

      const response = await fetch('/api/v1/auth/status', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConnectionStatus(data.authenticated ? 'connected' : 'idle');
      } else {
        setConnectionStatus('error');
      }
    } catch (error) {
      setConnectionStatus('error');
      console.error('Failed to check connection status:', error);
    }
  }, []);

  // Connect to Amazon
  const handleConnectAmazon = useCallback(async () => {
    console.log('🔍 Connect button clicked!');
    setIsConnecting(true);
    try {
      console.log('🔍 Making request to /api/v1/auth/amazon/login...');
      // Initiate OAuth flow (no auth required for this endpoint)
      const response = await fetch('/api/v1/auth/amazon/login');

      console.log('🔍 Response status:', response.status);
      console.log('🔍 Response ok:', response.ok);

      if (response.ok) {
        const data = await response.json();
        console.log('🔍 Response data:', data);
        // Redirect to Amazon OAuth
        console.log('🔍 Redirecting to:', data.auth_url);
        window.location.href = data.auth_url;
      } else {
        const errorData = await response.text();
        console.error('🔍 Response error:', errorData);
        throw new Error('Failed to initiate connection');
      }
    } catch (error) {
      console.error('🔍 Connect failed:', error);
      toast({
        title: "Connection Failed",
        description: "Unable to connect to Amazon. Please try again.",
        variant: "destructive",
      });
      setIsConnecting(false);
    }
  }, [toast]);

  // Disconnect account
  const handleDisconnectAccount = useCallback(async () => {
    if (!accountToDisconnect) return;

    setIsDisconnecting(true);
    try {
      await accountService.disconnectAccount(accountToDisconnect);

      toast({
        title: "Account Disconnected",
        description: "The account has been successfully disconnected.",
      });

      setShowDisconnectDialog(false);
      setAccountToDisconnect(null);

      // Refresh the page to update the account list
      window.location.reload();
    } catch (error) {
      toast({
        title: "Disconnection Failed",
        description: "Failed to disconnect the account. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsDisconnecting(false);
    }
  }, [accountToDisconnect, toast]);

  // Export accounts data
  const handleExportAccounts = useCallback(async () => {
    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error('No authentication token available');
      }

      const response = await fetch('/api/v1/accounts/amazon-ads-accounts', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `amazon-accounts-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        toast({
          title: "Export Complete",
          description: "Account data has been exported successfully.",
        });
      }
    } catch (error) {
      toast({
        title: "Export Failed",
        description: "Failed to export account data.",
        variant: "destructive",
      });
    }
  }, [toast]);

  // Handle account selection
  const handleAccountSelect = useCallback((account: StoredAmazonAccount) => {
    setSelectedAccount(account);
    toast({
      title: "Account Selected",
      description: `Selected ${account.accountName} (${account.adsAccountId})`,
    });
  }, [toast]);

  // Get auth token from Clerk
  async function getAuthToken(): Promise<string | null> {
    // @ts-ignore - Clerk is available globally
    const clerk = window.Clerk;
    if (!clerk || !clerk.session) {
      console.warn('Clerk not initialized or no active session');
      return null;
    }

    try {
      // Get the session token - this is what the backend expects
      const token = await clerk.session.getToken();
      return token;
    } catch (error) {
      console.error('Failed to get Clerk token:', error);
      return null;
    }
  }

  // Check if there are any accounts available
  const checkAccountsAvailable = useCallback(async () => {
    try {
      const token = await getAuthToken();
      if (!token) {
        setHasAccounts(false);
        return;
      }

      const response = await accountService.getAccounts();
      setHasAccounts(response.accounts.length > 0);
    } catch (error) {
      console.error('Failed to check accounts:', error);
      setHasAccounts(false);
    }
  }, []);

  // Check connection status on mount
  React.useEffect(() => {
    checkConnectionStatus();
    checkAccountsAvailable();
  }, [checkConnectionStatus, checkAccountsAvailable]);

  return (
    <div className="px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Amazon Advertising Accounts</h1>
          <p className="text-muted-foreground mt-1">
            Manage your connected Amazon Advertising accounts and profiles
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportAccounts}
          >
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button
            onClick={handleConnectAmazon}
            disabled={isConnecting || (connectionStatus === 'connected' && hasAccounts)}
          >
            {isConnecting ? (
              <>
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                Connecting...
              </>
            ) : connectionStatus === 'connected' && hasAccounts ? (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Connected
              </>
            ) : connectionStatus === 'connected' && !hasAccounts ? (
              <>
                <Plus className="h-4 w-4 mr-2" />
                Reconnect Amazon Account
              </>
            ) : (
              <>
                <Plus className="h-4 w-4 mr-2" />
                Connect Amazon Account
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Connection Status Alert */}
      {connectionStatus === 'connected' && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertTitle>Connected to Amazon</AlertTitle>
          <AlertDescription>
            Your Amazon Advertising account is connected and ready to use.
          </AlertDescription>
        </Alert>
      )}

      {connectionStatus === 'error' && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Connection Error</AlertTitle>
          <AlertDescription>
            Unable to verify Amazon connection. Please check your authentication.
          </AlertDescription>
        </Alert>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="accounts" className="space-y-4">
        <TabsList className="grid w-auto grid-cols-3">
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="help">Help</TabsTrigger>
        </TabsList>

        {/* Accounts Tab */}
        <TabsContent value="accounts" className="space-y-4">
          <AmazonAccountsList
            onAccountSelect={handleAccountSelect}
            onRefresh={() => window.location.reload()}
          />

          {/* Selected Account Details */}
          {selectedAccount && (
            <Card>
              <CardHeader>
                <CardTitle>Selected Account</CardTitle>
                <CardDescription>
                  {selectedAccount.accountName} ({selectedAccount.adsAccountId})
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Status:</span>
                    <Badge>{selectedAccount.status}</Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Countries:</span>
                    <span className="text-sm">{(selectedAccount.metadata?.countryCodes || selectedAccount.countryCodes || []).join(', ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">Profiles:</span>
                    <span className="text-sm">{selectedAccount.metadata?.alternateIds?.length || 0}</span>
                  </div>
                  <Separator className="my-2" />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => navigate(`/accounts/${selectedAccount.id}`)}
                    >
                      View Details
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        setAccountToDisconnect(selectedAccount.id);
                        setShowDisconnectDialog(true);
                      }}
                    >
                      Disconnect
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Account Settings</CardTitle>
              <CardDescription>
                Configure how your Amazon Advertising accounts are managed
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">Automatic Token Refresh</p>
                    <p className="text-sm text-muted-foreground">
                      Automatically refresh tokens before they expire
                    </p>
                  </div>
                  <Badge variant="secondary">Enabled</Badge>
                </div>
                <Separator />
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <p className="font-medium">Sync Frequency</p>
                    <p className="text-sm text-muted-foreground">
                      How often to sync account data from Amazon
                    </p>
                  </div>
                  <Badge variant="secondary">Every Hour</Badge>
                </div>
                <Separator />
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <p className="font-medium">Error Notifications</p>
                    <p className="text-sm text-muted-foreground">
                      Get notified when account errors occur
                    </p>
                  </div>
                  <Badge variant="secondary">Email</Badge>
                </div>
              </div>
              <Button onClick={() => navigate('/settings')}>
                <Settings className="h-4 w-4 mr-2" />
                Manage Settings
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Help Tab */}
        <TabsContent value="help" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Getting Started</CardTitle>
              <CardDescription>
                Learn how to connect and manage your Amazon Advertising accounts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex gap-3">
                  <Link2 className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="font-medium">Connect Your Account</p>
                    <p className="text-sm text-muted-foreground">
                      Click "Connect Amazon Account" to authorize access to your advertising data.
                    </p>
                  </div>
                </div>
                <Separator />
                <div className="flex gap-3">
                  <Shield className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="font-medium">Required Permissions</p>
                    <p className="text-sm text-muted-foreground">
                      You'll need the following Amazon Ads API scopes:
                    </p>
                    <ul className="text-sm text-muted-foreground mt-1 ml-4 list-disc">
                      <li>advertising::campaign_management</li>
                      <li>advertising::account_management</li>
                      <li>advertising::dsp_campaigns</li>
                      <li>advertising::reporting</li>
                    </ul>
                  </div>
                </div>
                <Separator />
                <div className="flex gap-3">
                  <HelpCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="font-medium">Multiple Profiles</p>
                    <p className="text-sm text-muted-foreground">
                      Each account can have profiles for different countries. These are automatically
                      detected and displayed when you sync your accounts.
                    </p>
                  </div>
                </div>
              </div>
              <div className="pt-4">
                <Button variant="outline" onClick={() => window.open('https://advertising.amazon.com/API/docs', '_blank')}>
                  View API Documentation
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Disconnect Confirmation Dialog */}
      <Dialog open={showDisconnectDialog} onOpenChange={setShowDisconnectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Disconnect Account</DialogTitle>
            <DialogDescription>
              Are you sure you want to disconnect this account? You'll need to reconnect it
              to access your Amazon Advertising data again.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDisconnectDialog(false)}
              disabled={isDisconnecting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisconnectAccount}
              disabled={isDisconnecting}
            >
              {isDisconnecting ? 'Disconnecting...' : 'Disconnect'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AccountsPage;