/**
 * MemoryVault AI — Optional Auth Modal
 * =====================================
 * Startup modal offering 3 user choices:
 *   1. Login (Existing User)
 *   2. Register (New Account with unique username check)
 *   3. Continue as Guest (Skip login & proceed immediately)
 */

'use client';

import { useState } from 'react';
import { User, Lock, UserPlus, LogIn, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';
import { loginUser, registerUser } from '@/lib/api';

interface AuthModalProps {
  isOpen: boolean;
  onSelectUser: (user: { username: string; isGuest: boolean }) => void;
  onClose?: () => void;
}

export default function AuthModal({ isOpen, onSelectUser, onClose }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'welcome' | 'login' | 'register'>('welcome');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }

    setLoading(true);
    try {
      const res = await loginUser(username.trim(), password);
      if (res.success && res.user) {
        onSelectUser({ username: res.user.username, isGuest: false });
      } else {
        setError(res.error || 'Invalid login credentials.');
      }
    } catch {
      setError('Failed to connect to backend server. Make sure port 8000 is active.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError('Please enter both username and password.');
      return;
    }
    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters long.');
      return;
    }

    setLoading(true);
    try {
      const res = await registerUser(username.trim(), password);
      if (res.success && res.user) {
        onSelectUser({ username: res.user.username, isGuest: false });
      } else {
        setError(res.error || 'Username already taken or invalid.');
      }
    } catch {
      setError('Failed to connect to backend server.');
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = () => {
    onSelectUser({ username: 'guest', isGuest: true });
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="w-full max-w-md overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        {/* Header Banner */}
        <div className="relative bg-gradient-to-r from-sky-600 via-indigo-600 to-purple-600 p-6 text-white text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-white/10 backdrop-blur-md shadow-inner mb-3">
            <Sparkles size={24} className="text-sky-200" />
          </div>
          <h2 className="text-xl font-extrabold tracking-tight">MemoryVault AI</h2>
          <p className="text-xs text-sky-100 mt-1">Context-Aware Misplaced Item Prediction</p>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
              ⚠️ {error}
            </div>
          )}

          {/* TAB 1: WELCOME SCREEN */}
          {activeTab === 'welcome' && (
            <div className="flex flex-col gap-4 text-center">
              <div className="text-sm text-slate-300">
                Welcome! Choose how you would like to proceed with your item search:
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('login');
                  }}
                  className="flex items-center justify-center gap-2 rounded-xl bg-sky-600 py-3 text-sm font-bold text-white shadow-lg shadow-sky-600/30 hover:bg-sky-500 transition-all"
                >
                  <LogIn size={16} />
                  Login to Account
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('register');
                  }}
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-800 py-3 text-sm font-bold text-slate-200 hover:bg-slate-700 transition-all"
                >
                  <UserPlus size={16} />
                  Register New Account
                </button>

                <div className="relative my-1 flex items-center justify-center">
                  <div className="w-full border-t border-slate-800" />
                  <span className="absolute bg-slate-900 px-3 text-[10px] uppercase font-semibold text-slate-500">
                    OR
                  </span>
                </div>

                <button
                  type="button"
                  onClick={handleGuest}
                  className="flex items-center justify-center gap-2 rounded-xl border border-slate-700/60 bg-slate-800/40 py-3 text-sm font-semibold text-sky-400 hover:bg-slate-800 hover:text-sky-300 transition-all"
                >
                  <span>Continue as Guest (No Login Required)</span>
                  <ArrowRight size={16} />
                </button>
              </div>

              <div className="mt-2 flex items-center justify-center gap-1.5 text-[11px] text-slate-500">
                <ShieldCheck size={13} className="text-emerald-400" />
                <span>Guest sessions work instantly. Logged in users get saved habit locations!</span>
              </div>
            </div>
          )}

          {/* TAB 2: LOGIN FORM */}
          {activeTab === 'login' && (
            <form onSubmit={handleLogin} className="flex flex-col gap-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <LogIn size={18} className="text-sky-400" />
                Login to MemoryVault
              </h3>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-xs font-semibold text-slate-400">Username</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-xs font-semibold text-slate-400">Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-3 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 rounded-xl bg-sky-600 py-2.5 text-sm font-bold text-white shadow-lg shadow-sky-600/30 hover:bg-sky-500 disabled:opacity-50 transition-all"
              >
                {loading ? 'Authenticating...' : 'Sign In'}
              </button>

              <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('welcome');
                  }}
                  className="hover:underline text-slate-400"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('register');
                  }}
                  className="text-sky-400 hover:underline"
                >
                  Need an account? Register
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: REGISTER FORM */}
          {activeTab === 'register' && (
            <form onSubmit={handleRegister} className="flex flex-col gap-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <UserPlus size={18} className="text-sky-400" />
                Register Unique Account
              </h3>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-xs font-semibold text-slate-400">Choose Username (Unique)</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-3 text-slate-500" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Choose a unique username"
                    className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex flex-col gap-1 text-left">
                <label className="text-xs font-semibold text-slate-400">Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-3 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Create a password"
                    className="w-full rounded-xl border border-slate-700 bg-slate-800 py-2.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="mt-2 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 py-2.5 text-sm font-bold text-white shadow-lg hover:from-sky-500 hover:to-indigo-500 disabled:opacity-50 transition-all"
              >
                {loading ? 'Creating Account...' : 'Create Account'}
              </button>

              <div className="flex items-center justify-between text-xs text-slate-400 mt-1">
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('welcome');
                  }}
                  className="hover:underline text-slate-400"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setActiveTab('login');
                  }}
                  className="text-sky-400 hover:underline"
                >
                  Already registered? Sign In
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
