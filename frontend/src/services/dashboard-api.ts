import { Account, Stats } from '@/stores/dashboard'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface UserProfile {
  id: string
  email: string
  firstName: string
  lastName: string
  imageUrl?: string
  createdAt: string
  lastLoginAt: string
}

class DashboardAPI {
  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async getUserProfile(): Promise<UserProfile> {
    return this.makeRequest<UserProfile>('/api/v1/users/me')
  }

  async getUserAccounts(): Promise<Account[]> {
    return this.makeRequest<Account[]>('/api/v1/users/me/accounts')
  }

  async getUserStats(): Promise<Stats> {
    return this.makeRequest<Stats>('/api/v1/users/me/stats')
  }

  async getFullUserData(): Promise<{
    profile: UserProfile
    accounts: Account[]
    stats: Stats
  }> {
    return this.makeRequest('/api/v1/users/me/full')
  }

  async syncAccount(accountId: string): Promise<void> {
    return this.makeRequest(`/api/v1/accounts/${accountId}/sync`, {
      method: 'POST',
    })
  }

  async switchAccount(accountId: string): Promise<Account> {
    return this.makeRequest<Account>(`/api/v1/accounts/${accountId}/switch`, {
      method: 'POST',
    })
  }
}

export const dashboardAPI = new DashboardAPI()