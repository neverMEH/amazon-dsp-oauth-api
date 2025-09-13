import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

export interface Account {
  id: string
  name: string
  advertiserId: string
  marketplaceId: string
  countryCode: string
  currencyCode: string
  isActive: boolean
  lastSyncAt?: string
}

export interface Stats {
  totalAccounts: number
  activeAccounts: number
  totalCampaigns: number
  totalSpend: number
  impressions: number
  clicks: number
  conversions: number
}

interface DashboardState {
  // User data
  currentAccount: Account | null
  accounts: Account[]
  stats: Stats | null
  
  // UI state
  isLoading: boolean
  error: string | null
  sidebarCollapsed: boolean
  
  // Actions
  setCurrentAccount: (account: Account | null) => void
  setAccounts: (accounts: Account[]) => void
  setStats: (stats: Stats | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  reset: () => void
}

const initialState = {
  currentAccount: null,
  accounts: [],
  stats: null,
  isLoading: false,
  error: null,
  sidebarCollapsed: false,
}

export const useDashboardStore = create<DashboardState>()(
  devtools(
    persist(
      (set, get) => ({
        ...initialState,
        
        setCurrentAccount: (account) => set({ currentAccount: account }),
        setAccounts: (accounts) => set({ accounts }),
        setStats: (stats) => set({ stats }),
        setLoading: (isLoading) => set({ isLoading }),
        setError: (error) => set({ error }),
        setSidebarCollapsed: (sidebarCollapsed) => set({ sidebarCollapsed }),
        reset: () => set(initialState),
      }),
      {
        name: 'dashboard-store',
        partialize: (state) => ({
          currentAccount: state.currentAccount,
          sidebarCollapsed: state.sidebarCollapsed,
        }),
      }
    ),
    {
      name: 'dashboard-store',
    }
  )
)