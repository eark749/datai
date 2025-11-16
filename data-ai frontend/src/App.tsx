import { useState, useEffect } from 'react';
import { Login } from './components/Login';
import { Register } from './components/Register';
import { ChatInterface } from './components/ChatInterface';
import { logout as logoutAPI } from './api/auth.service';

type Screen = 'login' | 'register' | 'chat';

interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [tokens, setTokens] = useState<AuthTokens | null>(null);

  // Check for existing tokens on mount
  useEffect(() => {
    const storedAccessToken = localStorage.getItem('accessToken');
    const storedRefreshToken = localStorage.getItem('refreshToken');
    
    if (storedAccessToken && storedRefreshToken) {
      setTokens({
        accessToken: storedAccessToken,
        refreshToken: storedRefreshToken,
      });
      setCurrentScreen('chat');
    }
  }, []);

  const handleLoginSuccess = (accessToken: string, refreshToken: string) => {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    setTokens({ accessToken, refreshToken });
    setCurrentScreen('chat');
  };

  const handleRegisterSuccess = (accessToken: string, refreshToken: string) => {
    localStorage.setItem('accessToken', accessToken);
    localStorage.setItem('refreshToken', refreshToken);
    setTokens({ accessToken, refreshToken });
    setCurrentScreen('chat');
  };

  const handleLogout = async () => {
    if (tokens?.refreshToken) {
      try {
        // Call the backend logout API to revoke refresh token
        await logoutAPI(tokens.refreshToken);
      } catch (error) {
        console.error('Logout error:', error);
        // Continue with logout even if API call fails
      }
    }

    // Clear tokens regardless of API response
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setTokens(null);
    setCurrentScreen('login');
  };

  return (
    <div className="min-h-screen bg-white">
      {currentScreen === 'login' && (
        <Login
          onLoginSuccess={handleLoginSuccess}
          onNavigateToRegister={() => setCurrentScreen('register')}
        />
      )}
      {currentScreen === 'register' && (
        <Register
          onRegisterSuccess={handleRegisterSuccess}
          onNavigateToLogin={() => setCurrentScreen('login')}
        />
      )}
      {currentScreen === 'chat' && (
        <ChatInterface onLogout={handleLogout} />
      )}
    </div>
  );
}
