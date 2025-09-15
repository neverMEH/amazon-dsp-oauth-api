// Amazon Ads API v3.0 Account Types

export interface AlternateId {
  countryCode: string;
  entityId: string;
  profileId: number;
}

export interface AmazonAdsAccount {
  adsAccountId: string;
  accountName: string;
  status: 'CREATED' | 'DISABLED' | 'PARTIALLY_CREATED' | 'PENDING';
  alternateIds: AlternateId[];
  countryCodes: string[];
  errors?: {
    [countryCode: string]: Array<{
      errorId: number;
      errorCode: string;
      errorMessage: string;
    }>;
  };
}

export interface AmazonAdsAccountsResponse {
  accounts: AmazonAdsAccount[];
  nextToken?: string;
  total: number;
  source: string;
  timestamp: string;
}

// Extended account with local database fields
export interface StoredAmazonAccount {
  id: string; // Local database ID
  userId: string;
  adsAccountId: string;
  accountName: string;
  status: 'CREATED' | 'DISABLED' | 'PARTIALLY_CREATED' | 'PENDING';
  marketplaceId?: string;
  accountType: string;
  isDefault: boolean;
  connectedAt: string;
  lastSyncedAt?: string;
  countryCodes?: string[]; // Optional at root for backward compatibility
  alternateIds?: AlternateId[]; // Optional at root for backward compatibility
  metadata: {
    alternateIds: AlternateId[];
    countryCodes: string[];
    errors?: AmazonAdsAccount['errors'];
    profileId?: number;
    countryCode?: string;
    apiStatus: string;
  };
  syncStatus?: 'pending' | 'in_progress' | 'completed' | 'failed';
  syncErrorMessage?: string;
  syncRetryCount?: number;
  nextSyncAt?: string;
}

// Helper type for displaying accounts in UI
export interface AccountDisplayData {
  id: string;
  name: string;
  amazonId: string;
  status: 'active' | 'disabled' | 'partial' | 'pending';
  countries: string[];
  profileCount: number;
  hasErrors: boolean;
  errorCountries?: string[];
  primaryProfile?: {
    profileId: number;
    countryCode: string;
    entityId: string;
  };
  lastSync?: string;
  syncStatus?: 'pending' | 'in_progress' | 'completed' | 'failed';
}

// Transform function signatures
export type TransformToDisplayData = (account: StoredAmazonAccount) => AccountDisplayData;
export type FilterByCountry = (accounts: StoredAmazonAccount[], countryCode: string) => StoredAmazonAccount[];
export type GetProfileForCountry = (account: StoredAmazonAccount, countryCode: string) => AlternateId | undefined;