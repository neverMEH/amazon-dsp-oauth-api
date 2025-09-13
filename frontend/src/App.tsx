import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { OAuthLogin } from '@/components/OAuthLogin';
import { OAuthCallback } from '@/components/OAuthCallback';
import { TokenDashboard } from '@/components/TokenDashboard';
import { ThemeProvider } from '@/components/theme-provider';
import { ThemeToggle } from '@/components/theme-toggle';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TokenResponse } from '@/services/api';

function App() {
  const [tokens, setTokens] = useState<TokenResponse | null>(null);

  useEffect(() => {
    // Check for stored tokens on mount
    const storedTokens = sessionStorage.getItem('tokens');
    if (storedTokens) {
      try {
        setTokens(JSON.parse(storedTokens));
      } catch (error) {
        console.error('Failed to parse stored tokens:', error);
        sessionStorage.removeItem('tokens');
      }
    }
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="system" storageKey="amazon-dsp-theme">
        <div className="relative">
          {/* Global Theme Toggle */}
          <div className="fixed top-4 right-4 z-50">
            <ThemeToggle />
          </div>
          
          <Router>
            <Routes>
              <Route path="/" element={tokens ? <Navigate to="/dashboard" /> : <OAuthLogin />} />
              <Route path="/callback" element={<OAuthCallback />} />
              <Route 
                path="/dashboard" 
                element={
                  tokens ? (
                    <TokenDashboard tokens={tokens} />
                  ) : (
                    <Navigate to="/" />
                  )
                } 
              />
            </Routes>
          </Router>
          
          <Toaster />
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;