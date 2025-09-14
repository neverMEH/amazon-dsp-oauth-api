import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AccountSettingsPanel } from '@/components/account/AccountSettingsPanel';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ResponsiveBreadcrumbNav } from '@/components/ui/breadcrumb';
import { useUser } from '@clerk/clerk-react';
import { Settings as SettingsIcon, User, Bell, Shield, Palette } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';

export const SettingsPage: React.FC = () => {
  const { user } = useUser();

  return (
    <div className="space-y-6">
      <ResponsiveBreadcrumbNav />

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your application and account preferences
        </p>
      </div>

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4 max-w-2xl">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>General Preferences</CardTitle>
              <CardDescription>
                Customize your application experience
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="theme">Theme</Label>
                  <div className="text-sm text-muted-foreground">
                    Choose between light, dark, or system theme
                  </div>
                </div>
                <ThemeToggle />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="auto-refresh">Auto-refresh data</Label>
                  <div className="text-sm text-muted-foreground">
                    Automatically refresh account data every 5 minutes
                  </div>
                </div>
                <Switch id="auto-refresh" />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="compact-mode">Compact mode</Label>
                  <div className="text-sm text-muted-foreground">
                    Use a more condensed layout for data display
                  </div>
                </div>
                <Switch id="compact-mode" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Your account details from Clerk
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>Email</Label>
                <div className="text-sm text-muted-foreground">
                  {user?.primaryEmailAddress?.emailAddress || 'Not available'}
                </div>
              </div>
              
              <div className="grid gap-2">
                <Label>User ID</Label>
                <div className="text-sm text-muted-foreground font-mono">
                  {user?.id || 'Not available'}
                </div>
              </div>
              
              <div className="grid gap-2">
                <Label>Account created</Label>
                <div className="text-sm text-muted-foreground">
                  {user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : 'Not available'}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="accounts">
          <AccountSettingsPanel />
        </TabsContent>

        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Email Notifications</CardTitle>
              <CardDescription>
                Configure when you want to receive email alerts
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="token-expiry">Token expiry warnings</Label>
                  <div className="text-sm text-muted-foreground">
                    Get notified when tokens are about to expire
                  </div>
                </div>
                <Switch id="token-expiry" defaultChecked />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="account-disconnect">Account disconnections</Label>
                  <div className="text-sm text-muted-foreground">
                    Alert when an account is disconnected
                  </div>
                </div>
                <Switch id="account-disconnect" defaultChecked />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="api-errors">API errors</Label>
                  <div className="text-sm text-muted-foreground">
                    Notify about API failures and errors
                  </div>
                </div>
                <Switch id="api-errors" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>In-App Notifications</CardTitle>
              <CardDescription>
                Control notifications within the application
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="toast-success">Success messages</Label>
                  <div className="text-sm text-muted-foreground">
                    Show toast notifications for successful operations
                  </div>
                </div>
                <Switch id="toast-success" defaultChecked />
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="toast-errors">Error messages</Label>
                  <div className="text-sm text-muted-foreground">
                    Show toast notifications for errors
                  </div>
                </div>
                <Switch id="toast-errors" defaultChecked />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="security" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Security Settings</CardTitle>
              <CardDescription>
                Manage your security preferences and API access
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="two-factor">Two-factor authentication</Label>
                  <div className="text-sm text-muted-foreground">
                    Add an extra layer of security to your account
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Configure
                </Button>
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="api-keys">API Keys</Label>
                  <div className="text-sm text-muted-foreground">
                    Manage your API keys for programmatic access
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Manage Keys
                </Button>
              </div>
              
              <Separator />
              
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="activity-log">Activity Log</Label>
                  <div className="text-sm text-muted-foreground">
                    View recent account activity and API usage
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  View Log
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Session Management</CardTitle>
              <CardDescription>
                Control your active sessions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Session timeout</Label>
                  <div className="text-sm text-muted-foreground">
                    Automatically log out after 30 minutes of inactivity
                  </div>
                </div>
                <Switch defaultChecked />
              </div>
              
              <Separator />
              
              <div className="pt-2">
                <Button variant="destructive" size="sm">
                  Sign Out All Devices
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};