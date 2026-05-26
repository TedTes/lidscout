'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthUser, clearToken, getUser, setToken } from '@/lib/auth';
import { authApi } from '@/lib/api';

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    setUser(getUser());
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    setToken(access_token);
    setUser(getUser());
    router.push('/markets');
  };

  const register = async (email: string, password: string) => {
    const { access_token } = await authApi.register(email, password);
    setToken(access_token);
    setUser(getUser());
    router.push('/markets');
  };

  const googleLogin = async (credential: string) => {
    const { access_token } = await authApi.googleLogin(credential);
    setToken(access_token);
    setUser(getUser());
    router.push('/markets');
  };

  const logout = () => {
    clearToken();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
