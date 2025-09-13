import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { OAuthLogin } from '@/components/OAuthLogin';
import { OAuthCallback } from '@/components/OAuthCallback';
import { TokenDashboard } from '@/components/TokenDashboard';
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
  );
}

export default App;