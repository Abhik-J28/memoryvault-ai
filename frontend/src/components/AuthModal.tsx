/**
 * MemoryVault AI — Premium Auth Modal
 * =====================================
 * Stunning glassmorphism login / register / guest flow
 * Features:
 *   - Animated gradient background with floating orbs
 *   - Smooth tab transitions with framer-motion
 *   - Password visibility toggle
 *   - Inline validation with animated error messages
 *   - "Continue as Guest" with shimmer CTA
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import { Mail, Lock, Eye, EyeClosed, ArrowRight, User, UserPlus, ShieldCheck, Sparkles, Brain } from 'lucide-react';
import { cn } from '@/lib/utils';
import { loginUser, registerUser } from '@/lib/api';

interface AuthModalProps {
  isOpen: boolean;
  onSelectUser: (user: { username: string; isGuest: boolean }) => void;
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Floating orb particles for background animation
// ---------------------------------------------------------------------------
function FloatingOrbs() {
  return (
    <div className="auth-orbs-container">
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className={`auth-orb auth-orb-${i + 1}`}
          animate={{
            x: [0, 30 * Math.sin(i * 1.2), -20 * Math.cos(i), 0],
            y: [0, -25 * Math.cos(i * 0.8), 30 * Math.sin(i), 0],
            scale: [1, 1.15, 0.9, 1],
          }}
          transition={{
            duration: 8 + i * 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Animated input component
// ---------------------------------------------------------------------------
function AnimatedInput({
  icon: Icon,
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  showToggle,
  onToggle,
  isVisible,
}: {
  icon: React.ElementType;
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  showToggle?: boolean;
  onToggle?: () => void;
  isVisible?: boolean;
}) {
  const [isFocused, setIsFocused] = useState(false);

  return (
    <div className="auth-field">
      <label className="auth-label">{label}</label>
      <div className={cn('auth-input-wrap', isFocused && 'auth-input-wrap--focused')}>
        <Icon size={16} className="auth-input-icon" />
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          className="auth-input"
          required
        />
        {showToggle && (
          <button type="button" onClick={onToggle} className="auth-toggle-btn" tabIndex={-1}>
            {isVisible ? <EyeClosed size={16} /> : <Eye size={16} />}
          </button>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Auth Modal
// ---------------------------------------------------------------------------
export default function AuthModal({ isOpen, onSelectUser }: AuthModalProps) {
  const [activeTab, setActiveTab] = useState<'welcome' | 'login' | 'register'>('welcome');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Track mouse position for parallax on the card
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [3, -3]);
  const rotateY = useTransform(mouseX, [-300, 300], [-3, 3]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      mouseX.set(e.clientX - rect.left - rect.width / 2);
      mouseY.set(e.clientY - rect.top - rect.height / 2);
    },
    [mouseX, mouseY],
  );

  // Reset fields on tab change
  useEffect(() => {
    setError(null);
  }, [activeTab]);

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
      setError('Failed to connect to backend. Make sure port 8000 is active.');
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

  // Shared motion variants
  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 80 : -80, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -80 : 80, opacity: 0 }),
  };

  const tabDirection = activeTab === 'login' ? 1 : activeTab === 'register' ? 2 : 0;

  return (
    <div className="auth-overlay">
      <FloatingOrbs />
      <motion.div
        className="auth-card"
        initial={{ opacity: 0, y: 40, scale: 0.92 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        style={{ rotateX, rotateY, perspective: 1200 }}
        onMouseMove={handleMouseMove}
      >
        {/* Glowing top border */}
        <div className="auth-card-glow" />

        {/* Brand Header */}
        <div className="auth-brand">
          <motion.div
            className="auth-brand-icon"
            animate={{ rotate: [0, 5, -5, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Brain size={28} color="#fff" />
          </motion.div>
          <h1 className="auth-brand-title">MemoryVault AI</h1>
          <p className="auth-brand-sub">Context-Aware Misplaced Item Prediction</p>
        </div>

        {/* Tab Pills (only on login/register views) */}
        {activeTab !== 'welcome' && (
          <div className="auth-tab-bar">
            <button
              type="button"
              className={cn('auth-tab', activeTab === 'login' && 'auth-tab--active')}
              onClick={() => setActiveTab('login')}
            >
              Sign In
            </button>
            <button
              type="button"
              className={cn('auth-tab', activeTab === 'register' && 'auth-tab--active')}
              onClick={() => setActiveTab('register')}
            >
              Register
            </button>
          </div>
        )}

        {/* Error Message */}
        <AnimatePresence mode="wait">
          {error && (
            <motion.div
              key="error"
              className="auth-error"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25 }}
            >
              <span>⚠️ {error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Body — Animated Tab Panels */}
        <div className="auth-body">
          <AnimatePresence mode="wait" custom={tabDirection}>
            {/* ── WELCOME ──────────────────────────── */}
            {activeTab === 'welcome' && (
              <motion.div
                key="welcome"
                custom={0}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="auth-panel"
              >
                <p className="auth-welcome-text">
                  Welcome! Choose how you would like to start your search session.
                </p>

                <button
                  type="button"
                  onClick={() => setActiveTab('login')}
                  className="auth-primary-btn"
                >
                  <User size={16} />
                  Sign In to Account
                  <ArrowRight size={16} className="auth-btn-arrow" />
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('register')}
                  className="auth-secondary-btn"
                >
                  <UserPlus size={16} />
                  Create New Account
                </button>

                <div className="auth-divider">
                  <span>or</span>
                </div>

                <button
                  type="button"
                  onClick={handleGuest}
                  className="auth-guest-btn"
                >
                  <Sparkles size={15} />
                  Continue as Guest
                  <ArrowRight size={15} />
                </button>

                <div className="auth-hint">
                  <ShieldCheck size={13} className="auth-hint-icon" />
                  <span>Guest sessions work instantly. Logged-in users get saved habit locations!</span>
                </div>
              </motion.div>
            )}

            {/* ── LOGIN FORM ──────────────────────────── */}
            {activeTab === 'login' && (
              <motion.div
                key="login"
                custom={1}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="auth-panel"
              >
                <form onSubmit={handleLogin} className="auth-form">
                  <AnimatedInput
                    icon={User}
                    label="Username"
                    value={username}
                    onChange={setUsername}
                    placeholder="Enter your username"
                  />

                  <AnimatedInput
                    icon={Lock}
                    label="Password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={setPassword}
                    placeholder="Enter your password"
                    showToggle
                    onToggle={() => setShowPassword(!showPassword)}
                    isVisible={showPassword}
                  />

                  <motion.button
                    type="submit"
                    disabled={loading}
                    className="auth-submit-btn"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {loading ? (
                      <div className="auth-spinner" />
                    ) : (
                      <>
                        Sign In
                        <ArrowRight size={16} />
                      </>
                    )}
                  </motion.button>

                  <div className="auth-footer-links">
                    <button type="button" onClick={() => setActiveTab('welcome')} className="auth-link">
                      ← Back
                    </button>
                    <button type="button" onClick={handleGuest} className="auth-link auth-link--accent">
                      Skip — Continue as Guest →
                    </button>
                  </div>
                </form>
              </motion.div>
            )}

            {/* ── REGISTER FORM ──────────────────────────── */}
            {activeTab === 'register' && (
              <motion.div
                key="register"
                custom={2}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="auth-panel"
              >
                <form onSubmit={handleRegister} className="auth-form">
                  <AnimatedInput
                    icon={User}
                    label="Choose Username (Unique)"
                    value={username}
                    onChange={setUsername}
                    placeholder="Pick a unique username"
                  />

                  <AnimatedInput
                    icon={Lock}
                    label="Create Password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={setPassword}
                    placeholder="Create a strong password"
                    showToggle
                    onToggle={() => setShowPassword(!showPassword)}
                    isVisible={showPassword}
                  />

                  <motion.button
                    type="submit"
                    disabled={loading}
                    className="auth-submit-btn auth-submit-btn--register"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {loading ? (
                      <div className="auth-spinner" />
                    ) : (
                      <>
                        Create Account
                        <ArrowRight size={16} />
                      </>
                    )}
                  </motion.button>

                  <div className="auth-footer-links">
                    <button type="button" onClick={() => setActiveTab('welcome')} className="auth-link">
                      ← Back
                    </button>
                    <button type="button" onClick={handleGuest} className="auth-link auth-link--accent">
                      Skip — Continue as Guest →
                    </button>
                  </div>
                </form>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
