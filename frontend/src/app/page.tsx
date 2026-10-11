/**
 * MemoryVault AI - Primary Page
 * ==============================
 * Phase 1–6 Combined
 *
 * Full application layout:
 *   - Top Utility Bar (brand, status pill, analytics button)
 *   - 55/45 Split-Pane: Chat Pane (left) + Route Inspector (right)
 *   - Analytics Drawer (slide-over)
 *
 * Design tokens applied (from UI/UX Spec §6.1):
 *   --color-brand-dark   : #0f172a  (Slate 900)  — header background
 *   --color-bg-base      : #f8fafc  (Slate 50)   — page canvas
 *   --color-success      : #059669  (Emerald 600) — connected badge
 *   --color-warning      : #d97706  (Amber 600)  — offline badge
 *   --color-brand-primary: #0284c7  (Sky 600)    — accent / button
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
import { BarChart2, Brain, Wifi, WifiOff, RotateCcw, User, Bookmark, LogOut, UserCheck } from 'lucide-react';
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
        Backend Connected
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
      Backend Offline
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
      {/* TOP UTILITY BAR                                                     */}
      {/* ------------------------------------------------------------------ */}
      {/* ------------------------------------------------------------------ */}
      {/* TOP UTILITY BAR                                                     */}
      {/* ------------------------------------------------------------------ */}
      <header
        className="flex flex-wrap items-center justify-between gap-4 px-6 py-2.5 shadow-lg border-b border-slate-800 bg-slate-900/95 backdrop-blur-sm"
        role="banner"
      >
        {/* ---- Left: Logo + Brand name ---- */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl shadow-md bg-gradient-to-tr from-sky-600 to-blue-500 text-white shrink-0"
            aria-hidden="true"
          >
            <Brain size={20} />
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

        {/* ---- Right: User Badge + Actions + Status pill + Analytics button ---- */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* User Profile Pill */}
          {currentUser ? (
            <div className="flex items-center gap-2 rounded-xl border border-slate-700/80 bg-slate-800/90 px-3 py-1.5 text-xs text-slate-200 shadow-inner">
              <div className="flex items-center gap-1.5 font-bold">
                <User size={13} className="text-sky-400 shrink-0" />
                <span className="max-w-[100px] truncate">
                  {currentUser.isGuest ? 'Guest' : currentUser.username}
                </span>
              </div>

              {/* My Saved Places Button */}
              <button
                type="button"
                onClick={() => setSavedLocationsOpen(true)}
                className="ml-1 flex items-center gap-1.5 rounded-lg border border-pink-500/40 bg-pink-500/20 px-2.5 py-1 text-[11px] font-bold text-pink-300 hover:bg-pink-500/30 hover:border-pink-400 hover:text-pink-100 transition-all active:scale-95 shadow-sm cursor-pointer"
                title="Manage custom habit location overrides (Pink Map Highlights)"
              >
                <Bookmark size={11} className="shrink-0" />
                Saved Places
              </button>

              {/* Switch / Logout */}
              <button
                type="button"
                onClick={handleLogout}
                className="ml-1 p-1 rounded-md text-slate-400 hover:text-red-400 hover:bg-slate-700/50 transition-all cursor-pointer"
                title="Switch or Logout User"
              >
                <LogOut size={12} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="flex items-center gap-1.5 rounded-xl border border-sky-400/40 bg-sky-500/15 px-3 py-1.5 text-xs font-bold text-sky-300 hover:bg-sky-500/25 hover:text-white transition-all shadow-sm active:scale-95 cursor-pointer"
            >
              <UserCheck size={13} className="shrink-0" />
              Sign In / Register
            </button>
          )}

          {/* Primary Action: Search Another Item */}
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-xl px-3.5 py-1.5 text-xs font-bold uppercase tracking-wider text-white bg-gradient-to-r from-sky-600 to-blue-600 hover:from-sky-500 hover:to-blue-500 border border-sky-400/30 shadow-md shadow-sky-950/40 transition-all duration-150 active:scale-95 cursor-pointer"
            onClick={handleResetSearch}
            title="Start a new prediction session for another misplaced item"
          >
            <RotateCcw size={13} className="shrink-0" />
            Search Another Item
          </button>

          <StatusPill status={backendStatus} />

          <button
            id="evaluator-analytics-toggle"
            type="button"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate-300 hover:text-white hover:bg-slate-700 hover:border-sky-500/50 transition-all active:scale-95 cursor-pointer shadow-sm"
            onClick={() => setAnalyticsOpen(true)}
            aria-label="Open Evaluator Analytics drawer"
          >
            <BarChart2 size={13} className="shrink-0 text-sky-400" />
            Evaluator Analytics
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
            onResetSearch={handleResetSearch}
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
