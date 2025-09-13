const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  scope: string;
  token_type: string;
}

export interface UserInfo {
  email?: string;
  name?: string;
  sub?: string;
}

class ApiService {
  async getHealth() {
    const response = await fetch(`${API_BASE_URL}/`);
    if (!response.ok) throw new Error('API is not healthy');
    return response.json();
  }

  async initiateLogin(state?: string) {
    const params = new URLSearchParams();
    if (state) params.append('state', state);
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login?${params}`);
    if (!response.ok) throw new Error('Failed to initiate login');
    
    const data = await response.json();
    return data.auth_url;
  }

  async handleCallback(code: string, state?: string): Promise<TokenResponse> {
    const params = new URLSearchParams({ code });
    if (state) params.append('state', state);
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/callback?${params}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to exchange code for tokens');
    }
    
    return response.json();
  }

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    
    if (!response.ok) {
      throw new Error('Failed to refresh token');
    }
    
    return response.json();
  }

  decodeToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Failed to decode token:', error);
      return null;
    }
  }
}

export const api = new ApiService();