import React, { useState, useEffect } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Settings,
  Bell,
  Mail,
  Layout,
  RefreshCw,
  Save,
  Info,
  Check,
  Grid3x3,
  List,
  Star,
  AlertTriangle
} from 'lucide-react';
import { AccountSettings, Account, UpdateSettingsRequest } from '@/types/account';
import { accountService } from '@/services/accountService';
import { useToast } from '@/components/ui/use-toast';
import { cn } from '@/lib/utils';

interface AccountSettingsPanelProps {
  accounts?: Account[];
  onSettingsUpdate?: (settings: AccountSettings) => void;
  className?: string;
}

export const AccountSettingsPanel: React.FC<AccountSettingsPanelProps> = ({
  accounts = [],
  onSettingsUpdate,
  className,
}) => {
  const { toast } = useToast();
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalSettings, setOriginalSettings] = useState<AccountSettings | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    setIsLoading(true);
    try {
      const response = await accountService.getSettings();
      setSettings(response.settings);
      setOriginalSettings(response.settings);
    } catch (error) {
      console.error('Failed to load settings:', error);
      toast({
        title: "Failed to load settings",
        description: "Could not load your settings. Please try again.",
        variant: "destructive",
      });
      
      // Set default settings if loading fails
      const defaultSettings: AccountSettings = {
        autoRefreshTokens: true,
        defaultAccountId: null,
        notificationPreferences: {
          emailOnTokenExpiry: true,
          emailOnTokenRefresh: false,
          emailOnConnectionIssue: true,
        },
        dashboardLayout: 'grid',
      };
      setSettings(defaultSettings);
      setOriginalSettings(defaultSettings);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSettingChange = (key: keyof AccountSettings, value: any) => {
    if (!settings) return;
    
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    setHasChanges(JSON.stringify(newSettings) !== JSON.stringify(originalSettings));
  };

  const handleNotificationChange = (
    key: keyof AccountSettings['notificationPreferences'],
    value: boolean
  ) => {
    if (!settings) return;
    
    const newSettings = {
      ...settings,
      notificationPreferences: {
        ...settings.notificationPreferences,
        [key]: value,
      },
    };
    setSettings(newSettings);
    setHasChanges(JSON.stringify(newSettings) !== JSON.stringify(originalSettings));
  };

  const saveSettings = async () => {
    if (!settings || !hasChanges) return;

    setIsSaving(true);
    try {
      const updateRequest: UpdateSettingsRequest = {
        autoRefreshTokens: settings.autoRefreshTokens,
        defaultAccountId: settings.defaultAccountId,
        notificationPreferences: settings.notificationPreferences,
        dashboardLayout: settings.dashboardLayout,
      };

      const response = await accountService.updateSettings(updateRequest);
      setSettings(response.settings);
      setOriginalSettings(response.settings);
      setHasChanges(false);

      toast({
        title: "Settings saved",
        description: "Your preferences have been updated successfully.",
      });

      if (onSettingsUpdate) {
        onSettingsUpdate(response.settings);
      }
    } catch (error) {
      console.error('Failed to save settings:', error);
      toast({
        title: "Failed to save settings",
        description: "Could not save your settings. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const resetSettings = () => {
    if (originalSettings) {
      setSettings(originalSettings);
      setHasChanges(false);
    }
  };

  if (isLoading) {
    return <AccountSettingsPanelSkeleton />;
  }

  if (!settings) {
    return (
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Unable to load settings. Please refresh the page.
        </AlertDescription>
      </Alert>
    );
  }

  const defaultAccount = accounts.find(acc => acc.id === settings.defaultAccountId);

  return (
    <div className={cn("space-y-6", className)}>
      {/* General Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            General Settings
          </CardTitle>
          <CardDescription>
            Configure your account management preferences
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Auto Refresh Tokens */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex-1 space-y-1">
              <Label htmlFor="auto-refresh" className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Auto-refresh Tokens
              </Label>
              <p className="text-sm text-muted-foreground">
                Automatically refresh tokens before they expire to maintain uninterrupted access
              </p>
            </div>
            <Switch
              id="auto-refresh"
              checked={settings.autoRefreshTokens}
              onCheckedChange={(checked) => handleSettingChange('autoRefreshTokens', checked)}
            />
          </div>

          <Separator />

          {/* Default Account */}
          <div className="space-y-3">
            <Label htmlFor="default-account" className="flex items-center gap-2">
              <Star className="h-4 w-4" />
              Default Account
            </Label>
            <Select
              value={settings.defaultAccountId || "none"}
              onValueChange={(value) => 
                handleSettingChange('defaultAccountId', value === "none" ? null : value)
              }
            >
              <SelectTrigger id="default-account">
                <SelectValue placeholder="Select a default account">
                  {defaultAccount ? (
                    <span className="flex items-center gap-2">
                      {defaultAccount.accountName}
                      <span className="text-xs text-muted-foreground">
                        ({defaultAccount.marketplace.countryCode})
                      </span>
                    </span>
                  ) : (
                    "No default account"
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No default account</SelectItem>
                {accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    <div className="flex items-center justify-between w-full">
                      <span>{account.accountName}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {account.marketplace.countryCode}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              The default account will be pre-selected in forms and dashboards
            </p>
          </div>

          <Separator />

          {/* Dashboard Layout */}
          <div className="space-y-3">
            <Label htmlFor="layout" className="flex items-center gap-2">
              <Layout className="h-4 w-4" />
              Dashboard Layout
            </Label>
            <Select
              value={settings.dashboardLayout}
              onValueChange={(value: 'grid' | 'list') => 
                handleSettingChange('dashboardLayout', value)
              }
            >
              <SelectTrigger id="layout">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="grid">
                  <div className="flex items-center gap-2">
                    <Grid3x3 className="h-4 w-4" />
                    Grid View
                  </div>
                </SelectItem>
                <SelectItem value="list">
                  <div className="flex items-center gap-2">
                    <List className="h-4 w-4" />
                    List View
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground">
              Choose how accounts are displayed in the dashboard
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Email Notifications
          </CardTitle>
          <CardDescription>
            Manage when you receive email notifications
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Token Expiry Notifications */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex-1 space-y-1">
              <Label htmlFor="email-expiry" className="flex items-center gap-2">
                <Mail className="h-4 w-4" />
                Token Expiry Warnings
              </Label>
              <p className="text-sm text-muted-foreground">
                Receive email notifications when tokens are about to expire
              </p>
            </div>
            <Switch
              id="email-expiry"
              checked={settings.notificationPreferences.emailOnTokenExpiry}
              onCheckedChange={(checked) => 
                handleNotificationChange('emailOnTokenExpiry', checked)
              }
            />
          </div>

          <Separator />

          {/* Token Refresh Notifications */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex-1 space-y-1">
              <Label htmlFor="email-refresh" className="flex items-center gap-2">
                <RefreshCw className="h-4 w-4" />
                Token Refresh Confirmations
              </Label>
              <p className="text-sm text-muted-foreground">
                Receive email confirmations when tokens are successfully refreshed
              </p>
            </div>
            <Switch
              id="email-refresh"
              checked={settings.notificationPreferences.emailOnTokenRefresh}
              onCheckedChange={(checked) => 
                handleNotificationChange('emailOnTokenRefresh', checked)
              }
            />
          </div>

          <Separator />

          {/* Connection Issue Notifications */}
          <div className="flex items-center justify-between space-x-4">
            <div className="flex-1 space-y-1">
              <Label htmlFor="email-issues" className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4" />
                Connection Issues
              </Label>
              <p className="text-sm text-muted-foreground">
                Receive alerts when there are connection issues with your accounts
              </p>
            </div>
            <Switch
              id="email-issues"
              checked={settings.notificationPreferences.emailOnConnectionIssue}
              onCheckedChange={(checked) => 
                handleNotificationChange('emailOnConnectionIssue', checked)
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Actions */}
      {hasChanges && (
        <Card className="border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10">
          <CardContent className="flex items-center justify-between py-4">
            <div className="flex items-center gap-2 text-sm">
              <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <span>You have unsaved changes</span>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={resetSettings}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={saveSettings}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Success Message */}
      {!hasChanges && originalSettings && (
        <Alert className="border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10">
          <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertDescription>
            All settings are saved and up to date
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};

// Loading skeleton for AccountSettingsPanel
export const AccountSettingsPanelSkeleton: React.FC = () => {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32 mb-2" />
          <Skeleton className="h-4 w-48" />
        </CardHeader>
        <CardContent className="space-y-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-40 mb-2" />
          <Skeleton className="h-4 w-56" />
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center justify-between">
              <div className="space-y-2 flex-1">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-4 w-64" />
              </div>
              <Skeleton className="h-6 w-10" />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
};