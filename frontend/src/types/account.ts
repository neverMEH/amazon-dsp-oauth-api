// Account management types

export type AccountStatus = 'healthy' | 'warning' | 'expired' | 'disconnected';

export interface Marketplace {
  id: string;
  name: string;
  countryCode: string;
  region: string;
}

export interface Account {
  id: string;
  accountName: string;
  accountId: string;
  marketplace: Marketplace;
  status: AccountStatus;
  tokenExpiresAt: string | null;
  lastRefreshTime: string | null;
  createdAt: string;
  updatedAt: string;
  isDefault?: boolean;
  profileDetails?: ProfileDetails;
}

export interface ProfileDetails {
  profileId: string;
  profileName: string;
  profileType: 'advertiser' | 'agency';
  country: string;
  currency: string;
  timezone: string;
  accountInfo?: {
    marketplaceStringId: string;
    id: string;
    type: string;
    name: string;
    subType?: string;
  };
}

export interface AccountHealth {
  accountId: string;
  status: AccountStatus;
  message: string;
  lastChecked: string;
  tokenHealth: {
    isValid: boolean;
    expiresIn: number; // seconds
    needsRefresh: boolean;
  };
}

export interface AccountSettings {
  autoRefreshTokens: boolean;
  defaultAccountId: string | null;
  notificationPreferences: {
    emailOnTokenExpiry: boolean;
    emailOnTokenRefresh: boolean;
    emailOnConnectionIssue: boolean;
  };
  dashboardLayout: 'grid' | 'list';
}

export interface RefreshHistory {
  id: string;
  accountId: string;
  timestamp: string;
  success: boolean;
  error?: string;
  triggeredBy: 'manual' | 'auto' | 'system';
}

// API Response types
export interface AccountsListResponse {
  accounts: Account[];
  total: number;
}

export interface AccountDetailsResponse {
  account: Account;
  refreshHistory: RefreshHistory[];
}

export interface AccountHealthResponse {
  health: AccountHealth[];
}

export interface DisconnectAccountResponse {
  success: boolean;
  message: string;
}

export interface ReauthorizeResponse {
  success: boolean;
  authorizationUrl?: string;
  message: string;
}

export interface SettingsResponse {
  settings: AccountSettings;
}

export interface UpdateSettingsRequest {
  autoRefreshTokens?: boolean;
  defaultAccountId?: string | null;
  notificationPreferences?: Partial<AccountSettings['notificationPreferences']>;
  dashboardLayout?: 'grid' | 'list';
}