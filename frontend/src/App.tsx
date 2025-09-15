import { ClerkProvider, SignedIn, SignedOut } from '@clerk/clerk-react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from '@/components/Dashboard';
import { SignInPage } from '@/pages/SignIn';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Toaster } from '@/components/ui/toaster';
import { TokenResponse } from '@/services/api';
import { AccountManagementPage } from '@/components/account/AccountManagementPage';
import { SettingsPage } from '@/pages/Settings';

// Legacy components for backward compatibility
import { OAuthLogin } from '@/components/OAuthLogin';
import { OAuthCallback } from '@/components/OAuthCallback';
import { TokenDashboard } from '@/components/TokenDashboard';
import { AuthDashboard } from '@/components/AuthDashboard';
import { ConnectionStatusDemo } from '@/pages/ConnectionStatusDemo';

// Import your publishable key
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Publishable Key")
}

function App() {
  return (
    <ClerkProvider publishableKey={PUBLISHABLE_KEY}>
      <ErrorBoundary>
        <ThemeProvider defaultTheme="system" storageKey="amazon-dsp-theme">
          <div className="relative">
            {/* Global Theme Toggle - Only show when signed in */}
            <SignedIn>
              <div className="fixed top-4 right-20 z-50">
                <ThemeToggle />
              </div>
            </SignedIn>
            
            <Router>
              <Routes>
                {/* Public routes */}
                <Route 
                  path="/" 
                  element={
                    <>
                      <SignedOut>
                        <Navigate to="/sign-in" replace />
                      </SignedOut>
                      <SignedIn>
                        <Navigate to="/dashboard" replace />
                      </SignedIn>
                    </>
                  } 
                />
                <Route 
                  path="/sign-in" 
                  element={
                    <>
                      <SignedOut>
                        <SignInPage />
                      </SignedOut>
                      <SignedIn>
                        <Navigate to="/dashboard" replace />
                      </SignedIn>
                    </>
                  } 
                />

                {/* Protected routes */}
                <Route 
                  path="/dashboard" 
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  } 
                />
                <Route
                  path="/accounts"
                  element={
                    <ProtectedRoute>
                      <ErrorBoundary>
                        <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 p-6">
                          <div className="max-w-7xl mx-auto">
                            <AccountManagementPage />
                          </div>
                        </div>
                      </ErrorBoundary>
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/settings" 
                  element={
                    <ProtectedRoute>
                      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 p-6">
                        <div className="max-w-7xl mx-auto">
                          <SettingsPage />
                        </div>
                      </div>
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/profile" 
                  element={
                    <ProtectedRoute>
                      <div className="min-h-screen bg-gradient-to-br from-purple-50 to-indigo-100 dark:from-slate-900 dark:to-slate-800 p-6">
                        <div className="max-w-4xl mx-auto">
                          <h1 className="text-3xl font-bold mb-6">User Profile</h1>
                          <p className="text-muted-foreground">View and edit your profile information.</p>
                        </div>
                      </div>
                    </ProtectedRoute>
                  } 
                />

                {/* Legacy routes for backward compatibility */}
                <Route path="/oauth-login" element={<OAuthLogin />} />
                <Route path="/callback" element={<OAuthCallback />} />
                <Route path="/token-dashboard" element={<TokenDashboard tokens={{
                  access_token: '',
                  refresh_token: '',
                  expires_in: 0,
                  scope: '',
                  token_type: ''
                } as TokenResponse} />} />
                <Route path="/auth-dashboard" element={<AuthDashboard />} />
                <Route path="/status-demo" element={<ConnectionStatusDemo />} />

                {/* Catch all route */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Router>
            
            <Toaster />
          </div>
        </ThemeProvider>
      </ErrorBoundary>
    </ClerkProvider>
  );
}

export default App;