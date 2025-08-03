export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url?: string;
  google_id?: string;
  subscription_tier: 'free' | 'basic' | 'pro' | 'enterprise';
  subscription_status?: 'active' | 'cancelled' | 'past_due' | 'trialing';
  compute_units_remaining: number;
  compute_units_limit?: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  token: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface GoogleAuthResponse {
  access_token: string;
  user: User;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateUser: (userData: Partial<User>) => void;
}

export interface AuthError {
  message: string;
  code?: string;
  status?: number;
}