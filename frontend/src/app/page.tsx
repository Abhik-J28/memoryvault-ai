/**
 * MemoryVault AI - Primary Page
 * ==============================
 * Phase 1–6 Combined
 *
 * Full application layout:
 *   - Top Header Bar (clean logo + brand + status + sidebar toggle)
 *   - Slide-out Sidebar (user name, saved places, evaluator analytics, search another item, sign out)
 *   - 55/45 Split-Pane: Chat Pane (left) + Route Inspector (right)
 *   - Analytics Drawer (slide-over)
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { BarChart2, Brain, Wifi, WifiOff, Bookmark, LogOut, UserCheck, Menu, X, RotateCcw } from 'lucide-react';
import ChatPane from '@/components/ChatPane';
import RouteInspector from '@/components/RouteInspector';
import AnalyticsDrawer from '@/components/AnalyticsDrawer';
import AuthModal from '@/components/AuthModal';
import SavedLocationsModal from '@/components/SavedLocationsModal';
import type { RouteStep, LayoutData, PredictionData } from '@/lib/api';
import { fetchLayout } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BackendStatus = 'checking' | 'connected' | 'offline';

interface UserProfile {
  username: string;
  isGuest: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateSessionId(): string {
  return `mv-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Animated pulsing status pill — green when connected, amber when offline */
function StatusPill({ status }: { status: BackendStatus }) {
  if (status === 'checking') {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-700 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-300">
        <span className="h-2 w-2 animate-pulse rounded-full bg-slate-400" />
        Connecting…
      </span>
    );
  }

  if (status === 'connected') {
    return (
      <span
        className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
        style={{ backgroundColor: '#064e3b', color: '#6ee7b7' }}
      >
        <span className="relative flex h-2 w-2">
          <span
            className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
            style={{ backgroundColor: '#059669' }}
          />
          <span
            className="relative inline-flex h-2 w-2 rounded-full"
            style={{ backgroundColor: '#059669' }}
          />
        </span>
        <Wifi size={12} className="shrink-0" />
        Connected
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
      style={{ backgroundColor: '#451a03', color: '#fcd34d' }}
    >
      <span
        className="h-2 w-2 rounded-full"
        style={{ backgroundColor: '#d97706' }}
      />
      <WifiOff size={12} className="shrink-0" />
      Offline
    </span>
  );
}

// ---------------------------------------------------------------------------
// Page component
// ---------------------------------------------------------------------------

export default function Home() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [savedLocationsOpen, setSavedLocationsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const [currentUser, setCurrentUser] = useState<UserProfile | null>(null);
  const [sessionId, setSessionId] = useState(() => generateSessionId());

  // Route data & custom user habit room overrides
  const [routeData, setRouteData] = useState<RouteStep[] | null>(null);
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [customUserRooms, setCustomUserRooms] = useState<string[]>([]);
  const [repeatedFindingRooms, setRepeatedFindingRooms] = useState<string[]>([]);
  const [findingCounts, setFindingCounts] = useState<Record<string, number>>({});
  const [chatContext, setChatContext] = useState<Record<string, unknown>>({});

  // Initialize user profile from localStorage or open AuthModal
  useEffect(() => {
    const saved = localStorage.getItem('mv_user');
    if (saved) {
      try {
        setCurrentUser(JSON.parse(saved));
      } catch {
        setAuthModalOpen(true);
      }
    } else {
      setAuthModalOpen(true);
    }
  }, []);

  // Probe the FastAPI health endpoint on mount
  useEffect(() => {
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000';

    const checkHealth = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/health`, {
          signal: AbortSignal.timeout(5000),
        });
        setBackendStatus(res.ok ? 'connected' : 'offline');
      } catch {
        setBackendStatus('offline');
      }
    };

    checkHealth();

    // Pre-fetch layout so floor plan blueprint is instantly ready to display habits
    fetchLayout().then((l) => setLayout(l)).catch(() => {});
  }, []);

  const handleSelectUser = (user: UserProfile) => {
    setCurrentUser(user);
    localStorage.setItem('mv_user', JSON.stringify(user));
    setAuthModalOpen(false);
    handleResetSearch();
  };

  const handleLogout = () => {
    localStorage.removeItem('mv_user');
    setCurrentUser(null);
    setCustomUserRooms([]);
    setRepeatedFindingRooms([]);
    setFindingCounts({});
    setSidebarOpen(false);
    setAuthModalOpen(true);
  };

  // Reset conversation and state to search for another lost item
  const handleResetSearch = useCallback(() => {
    setSessionId(generateSessionId());
    setRouteData(null);
    setPrediction(null);
    setCustomUserRooms([]);
    setRepeatedFindingRooms([]);
    setFindingCounts({});
    setChatContext({});
    setSidebarOpen(false);
    fetchLayout().then((l) => setLayout(l)).catch(() => {});
  }, []);

  // Proactive habit callback: when item is identified before route is generated
  const handleEarlyFindings = useCallback(
    (
      layoutData: LayoutData | null,
      repeatedRooms: string[],
      counts: Record<string, number>,
      customRooms?: string[],
      itemType?: string,
    ) => {
      if (layoutData) {
        setLayout(layoutData);
      }
      setRepeatedFindingRooms(repeatedRooms);
      setFindingCounts(counts);
      if (customRooms && customRooms.length > 0) {
        setCustomUserRooms(customRooms);
      }
      if (itemType) {
        setChatContext((prev) => ({ ...prev, item_type: itemType }));
      }
    },
    [],
  );

  // Callback from ChatPane when route data arrives
  const handleRouteData = useCallback(
    (
      route: RouteStep[],
      layoutData: LayoutData,
      pred: PredictionData,
      customRooms?: string[],
      repeatedRooms?: string[],
      counts?: Record<string, number>,
      context?: Record<string, unknown>,
    ) => {
      setRouteData(route);
      setLayout(layoutData);
      setPrediction(pred);
      if (customRooms) {
        setCustomUserRooms(customRooms);
      }
      if (repeatedRooms) {
        setRepeatedFindingRooms(repeatedRooms);
      }
      if (counts) {
        setFindingCounts(counts);
      }
      if (context) {
        setChatContext((prev) => ({ ...prev, ...context }));
      }
    },
    [],
  );

  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ backgroundColor: '#f8fafc' }}
    >
      {/* ------------------------------------------------------------------ */}
      {/* SIDEBAR BACKDROP                                                   */}
      {/* ------------------------------------------------------------------ */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* SLIDE-OUT SIDEBAR                                                  */}
      {/* ------------------------------------------------------------------ */}
      <aside
        className={`fixed top-0 right-0 z-50 h-full w-80 shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{
          background: 'linear-gradient(165deg, #0b1329 0%, #0f172a 60%, #1e293b 100%)',
          borderLeft: '1px solid rgba(148, 163, 184, 0.15)',
        }}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-xl shadow-md bg-gradient-to-tr from-sky-600 to-blue-500 text-white shrink-0"
              aria-hidden="true"
            >
              <Brain size={18} />
            </div>
            <div>
              <p className="text-sm font-black text-slate-100 tracking-tight leading-none">MemoryVault AI</p>
              <p className="text-[10px] font-bold text-sky-400 uppercase tracking-widest mt-1">Control Center</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 transition-all cursor-pointer"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* User Profile Card */}
        <div className="p-5 border-b border-slate-800">
          <div className="flex items-center gap-3.5 rounded-2xl bg-slate-800/80 p-4 border border-slate-700/60 shadow-inner">
            <div
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-base font-black text-white shadow-md"
              style={{ background: 'linear-gradient(135deg, #0284c7 0%, #6366f1 100%)' }}
            >
              {currentUser ? (currentUser.isGuest ? 'G' : currentUser.username.charAt(0).toUpperCase()) : '?'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-slate-100 truncate">
                {currentUser ? (currentUser.isGuest ? 'Guest User' : currentUser.username) : 'Not signed in'}
              </p>
              <span className="inline-block px-2 py-0.5 mt-1 rounded-full text-[10px] font-semibold tracking-wide bg-sky-950/70 border border-sky-800 text-sky-300">
                {currentUser?.isGuest ? 'Guest Mode' : 'Authenticated Profile'}
              </span>
            </div>
          </div>
        </div>

        {/* Action Menu List */}
        <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
          {/* Action 1: Search Another Item */}
          <button
            type="button"
            onClick={handleResetSearch}
            className="sidebar-action-btn group w-full"
          >
            <div className="sidebar-action-icon" style={{ background: 'linear-gradient(135deg, #0284c7, #3b82f6)' }}>
              <RotateCcw size={16} className="text-white" />
            </div>
            <div className="text-left flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-100 group-hover:text-white transition-colors">Search Another Item</p>
              <p className="text-xs text-slate-400 truncate">Reset and triage a new lost object</p>
            </div>
          </button>

          {/* Action 2: Saved Places */}
          <button
            type="button"
            onClick={() => { setSavedLocationsOpen(true); setSidebarOpen(false); }}
            className="sidebar-action-btn group w-full"
          >
            <div className="sidebar-action-icon" style={{ background: 'linear-gradient(135deg, #ec4899, #d946ef)' }}>
              <Bookmark size={16} className="text-white" />
            </div>
            <div className="text-left flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-100 group-hover:text-white transition-colors">Saved Places</p>
              <p className="text-xs text-slate-400 truncate">Manage custom habit locations</p>
            </div>
          </button>

          {/* Action 3: Evaluator Analytics */}
          <button
            type="button"
            id="evaluator-analytics-toggle"
            onClick={() => { setAnalyticsOpen(true); setSidebarOpen(false); }}
            className="sidebar-action-btn group w-full"
          >
            <div className="sidebar-action-icon" style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)' }}>
              <BarChart2 size={16} className="text-white" />
            </div>
            <div className="text-left flex-1 min-w-0">
              <p className="text-sm font-bold text-slate-100 group-hover:text-white transition-colors">Evaluator Analytics</p>
              <p className="text-xs text-slate-400 truncate">View model ROC-AUC & metrics</p>
            </div>
          </button>

          {/* Divider */}
          <div className="pt-2 pb-1">
            <div className="border-t border-slate-800" />
          </div>

          {/* Action 4: Sign In / Logout */}
          {currentUser ? (
            <button
              type="button"
              onClick={handleLogout}
              className="sidebar-action-btn group w-full text-red-400 hover:text-red-300"
            >
              <div className="sidebar-action-icon" style={{ background: 'linear-gradient(135deg, #ef4444, #b91c1c)' }}>
                <LogOut size={16} className="text-white" />
              </div>
              <div className="text-left flex-1 min-w-0">
                <p className="text-sm font-bold text-slate-100 group-hover:text-red-300 transition-colors">Sign Out</p>
                <p className="text-xs text-slate-400 truncate">Switch account or go to guest mode</p>
              </div>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => { setAuthModalOpen(true); setSidebarOpen(false); }}
              className="sidebar-action-btn group w-full"
            >
              <div className="sidebar-action-icon" style={{ background: 'linear-gradient(135deg, #059669, #10b981)' }}>
                <UserCheck size={16} className="text-white" />
              </div>
              <div className="text-left flex-1 min-w-0">
                <p className="text-sm font-bold text-slate-100 group-hover:text-white transition-colors">Sign In / Register</p>
                <p className="text-xs text-slate-400 truncate">Preserve your habits in cloud</p>
              </div>
            </button>
          )}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-5 border-t border-slate-800 bg-slate-900/50">
          <p className="text-center text-[11px] text-slate-500 font-medium">
            MemoryVault AI · Domestic Spatial Intelligence
          </p>
        </div>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* TOP HEADER BAR (Logo on left, Status + Sidebar Menu on right)      */}
      {/* ------------------------------------------------------------------ */}
      <header
        className="flex items-center justify-between px-6 py-3 shadow-lg border-b border-slate-800 bg-slate-900/95 backdrop-blur-sm"
        role="banner"
      >
        {/* Left: MemoryVault Brand */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-2xl shadow-lg bg-gradient-to-tr from-sky-600 to-blue-500 text-white shrink-0"
            aria-hidden="true"
          >
            <Brain size={22} />
          </div>

          <div className="flex flex-col leading-tight">
            <span
              className="text-lg font-black tracking-tight text-slate-100"
              style={{
                fontFamily:
                  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                lineHeight: 1.15,
              }}
            >
              MemoryVault AI
            </span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-sky-400">
              Context-Aware Misplaced Item Prediction
            </span>
          </div>
        </div>

        {/* Right: Status Pill + Sidebar Hamburger Button */}
        <div className="flex items-center gap-3">
          <StatusPill status={backendStatus} />

          <button
            type="button"
            id="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800/90 px-3.5 py-1.5 text-slate-200 hover:text-white hover:bg-slate-700 hover:border-sky-500/60 transition-all active:scale-95 cursor-pointer shadow-md"
            aria-label="Open menu sidebar"
          >
            <Menu size={17} className="text-sky-400" />
            <span className="text-xs font-bold uppercase tracking-wider">Menu</span>
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* MAIN WORKSPACE — 55/45 split pane                                  */}
      {/* ------------------------------------------------------------------ */}
      <main className="split-pane" aria-label="Main workspace">
        {/* Left: Conversational Triage (55%) */}
        <div className="split-left">
          <ChatPane
            key={sessionId}
            sessionId={sessionId}
            username={currentUser?.isGuest ? null : currentUser?.username}
            onRouteData={handleRouteData}
            onEarlyFindings={handleEarlyFindings}
          />
        </div>

        {/* Divider */}
        <div className="split-divider" />

        {/* Right: Route Inspector (45%) */}
        <div className="split-right">
          <RouteInspector
            routeData={routeData}
            layout={layout}
            prediction={prediction}
            sessionId={sessionId}
            context={chatContext}
            itemType={(chatContext.item_type as string) || undefined}
            username={currentUser?.isGuest ? null : currentUser?.username}
            customUserRooms={customUserRooms}
            repeatedFindingRooms={repeatedFindingRooms}
            findingCounts={findingCounts}
            onResetSearch={handleResetSearch}
            onItemFound={(room) => {
              if (!currentUser?.isGuest) {
                setRepeatedFindingRooms((prev) => [room, ...prev.filter((r) => r !== room)]);
                setFindingCounts((prev) => ({ ...prev, [room]: (prev[room] || 0) + 1 }));
              }
            }}
          />
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* MODALS & DRAWERS                                                   */}
      {/* ------------------------------------------------------------------ */}
      <AuthModal
        isOpen={authModalOpen}
        onSelectUser={handleSelectUser}
        onClose={() => setAuthModalOpen(false)}
      />

      <SavedLocationsModal
        isOpen={savedLocationsOpen}
        username={currentUser?.username || 'guest'}
        onClose={() => setSavedLocationsOpen(false)}
        onLocationsUpdated={handleResetSearch}
      />

      <AnalyticsDrawer
        isOpen={analyticsOpen}
        onClose={() => setAnalyticsOpen(false)}
      />
    </div>
  );
}
