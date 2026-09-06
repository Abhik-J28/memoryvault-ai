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
import { BarChart2, Brain, Wifi, WifiOff, RotateCcw } from 'lucide-react';
import ChatPane from '@/components/ChatPane';
import RouteInspector from '@/components/RouteInspector';
import AnalyticsDrawer from '@/components/AnalyticsDrawer';
import type { RouteStep, LayoutData, PredictionData } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BackendStatus = 'checking' | 'connected' | 'offline';

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
        {/* Dual-ring pulse animation for the green dot */}
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

  // offline
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
  const [sessionId, setSessionId] = useState(() => generateSessionId());

  // Route data state (populated when chat reaches RESULT state)
  const [routeData, setRouteData] = useState<RouteStep[] | null>(null);
  const [layout, setLayout] = useState<LayoutData | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [chatContext, setChatContext] = useState<Record<string, unknown>>({});

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
  }, []);

  // Reset conversation and state to search for another lost item
  const handleResetSearch = useCallback(() => {
    setSessionId(generateSessionId());
    setRouteData(null);
    setLayout(null);
    setPrediction(null);
    setChatContext({});
  }, []);

  // Callback from ChatPane when route data arrives
  const handleRouteData = useCallback(
    (route: RouteStep[], layoutData: LayoutData, pred: PredictionData) => {
      setRouteData(route);
      setLayout(layoutData);
      setPrediction(pred);
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
      <header
        className="flex items-center justify-between px-6 py-3 shadow-md"
        style={{
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #1e293b',
        }}
        role="banner"
      >
        {/* ---- Left: Logo + Brand name ---- */}
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-xl shadow-md"
            style={{ backgroundColor: '#0284c7' }}
            aria-hidden="true"
          >
            <Brain size={20} color="#ffffff" />
          </div>

          <div className="flex flex-col leading-tight">
            <span
              className="text-lg font-black tracking-tight"
              style={{
                color: '#f8fafc',
                fontFamily:
                  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                lineHeight: 1.2,
              }}
            >
              MemoryVault AI
            </span>
            <span
              className="text-[10px] font-bold uppercase tracking-widest"
              style={{ color: '#0284c7', letterSpacing: '0.6px' }}
            >
              Context-Aware Misplaced Item Prediction
            </span>
          </div>
        </div>

        {/* ---- Centre / Right: Search Another + Status pill + Analytics button ---- */}
        <div className="flex items-center gap-3">
          {/* Primary Action: Search Another Item */}
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-bold uppercase tracking-wide text-white transition-all duration-200 shadow-sm hover:shadow-md"
            style={{
              backgroundColor: '#0284c7',
              borderColor: '#0284c7',
            }}
            onClick={handleResetSearch}
            title="Start a new prediction session for another misplaced item"
          >
            <RotateCcw size={14} className="shrink-0" />
            Search Another Item
          </button>

          <StatusPill status={backendStatus} />

          <button
            id="evaluator-analytics-toggle"
            type="button"
            className="inline-flex items-center gap-2 rounded-lg border px-3.5 py-1.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200"
            style={{
              borderColor: '#334155',
              color: '#94a3b8',
              backgroundColor: 'transparent',
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                '#1e293b';
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                '#0284c7';
              (e.currentTarget as HTMLButtonElement).style.color = '#e2e8f0';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.backgroundColor =
                'transparent';
              (e.currentTarget as HTMLButtonElement).style.borderColor =
                '#334155';
              (e.currentTarget as HTMLButtonElement).style.color = '#94a3b8';
            }}
            onClick={() => setAnalyticsOpen(true)}
            aria-label="Open Evaluator Analytics drawer"
          >
            <BarChart2 size={14} className="shrink-0" />
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
            onRouteData={handleRouteData}
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
            onResetSearch={handleResetSearch}
          />
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* ANALYTICS DRAWER (Phase 6)                                         */}
      {/* ------------------------------------------------------------------ */}
      <AnalyticsDrawer
        isOpen={analyticsOpen}
        onClose={() => setAnalyticsOpen(false)}
      />
    </div>
  );
}
