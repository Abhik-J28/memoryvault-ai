/**
 * MemoryVault AI - Primary Page
 * ==============================
 * Phase 1, Step 3: Top Utility Bar
 *
 * Screen 1 of the UI/UX Specification — Top Utility Bar only.
 * Conversational chat thread, quick chips, and route cards are
 * deferred to later phases.
 *
 * Design tokens applied (from UI/UX Spec §6.1):
 *   --color-brand-dark   : #0f172a  (Slate 900)  — header background
 *   --color-bg-base      : #f8fafc  (Slate 50)   — page canvas
 *   --color-success      : #059669  (Emerald 600) — connected badge
 *   --color-warning      : #d97706  (Amber 600)  — offline badge
 *   --color-brand-primary: #0284c7  (Sky 600)    — accent / button
 */

'use client';

import { useEffect, useState } from 'react';
import { BarChart2, Brain, Wifi, WifiOff } from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type BackendStatus = 'checking' | 'connected' | 'offline';

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

  // Probe the FastAPI health endpoint on mount
  useEffect(() => {
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000';

    const checkHealth = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/health`, {
          // Short timeout so we fail fast rather than hanging for 30s
          signal: AbortSignal.timeout(5000),
        });
        setBackendStatus(res.ok ? 'connected' : 'offline');
      } catch {
        setBackendStatus('offline');
      }
    };

    checkHealth();
  }, []);

  return (
    /*
     * Page canvas — Slate 50 (#f8fafc) per design token --color-bg-base
     * Full viewport height so future split-pane content fills naturally.
     */
    <div
      className="flex min-h-screen flex-col"
      style={{ backgroundColor: '#f8fafc' }}
    >
      {/* ------------------------------------------------------------------ */}
      {/* TOP UTILITY BAR — Screen 1, UI/UX Spec §4                          */}
      {/* Brand dark (#0f172a / Slate 900) background per design token        */}
      {/* ------------------------------------------------------------------ */}
      <header
        className="flex items-center justify-between px-6 py-3 shadow-lg"
        style={{ backgroundColor: '#0f172a' }}
        role="banner"
      >
        {/* ---- Left: Logo + Brand name ---- */}
        <div className="flex items-center gap-3">
          {/* Brain icon as logo stand-in — matches cognitive-assistant theme */}
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg"
            style={{ backgroundColor: '#0284c7' }}
            aria-hidden="true"
          >
            <Brain size={18} color="#ffffff" />
          </div>

          <div className="flex flex-col leading-tight">
            <span
              className="text-lg font-extrabold tracking-tight"
              style={{
                color: '#f8fafc',
                fontFamily:
                  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif',
                lineHeight: 1.2,
              }}
            >
              MemoryVault AI
            </span>
            <span
              className="text-[10px] font-bold uppercase tracking-widest"
              style={{ color: '#475569', letterSpacing: '0.5px' }}
            >
              Item Prediction &amp; Search Router
            </span>
          </div>
        </div>

        {/* ---- Centre / Right: Status pill + Analytics button ---- */}
        <div className="flex items-center gap-4">
          {/* Backend status indicator pill */}
          <StatusPill status={backendStatus} />

          {/* Evaluator Analytics toggle — wires to future metrics drawer (Phase 6) */}
          <button
            id="evaluator-analytics-toggle"
            type="button"
            className="inline-flex items-center gap-2 rounded-lg border px-4 py-1.5 text-xs font-semibold uppercase tracking-wide transition-all duration-200"
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
            aria-label="Open Evaluator Analytics drawer"
          >
            <BarChart2 size={14} className="shrink-0" />
            Evaluator Analytics
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* MAIN WORKSPACE — placeholder canvas (chat + route panes follow)     */}
      {/* ------------------------------------------------------------------ */}
      <main
        className="flex flex-1 items-center justify-center"
        style={{ backgroundColor: '#f8fafc' }}
        aria-label="Main workspace"
      >
        <div className="text-center">
          <p
            className="text-sm font-medium"
            style={{ color: '#94a3b8' }}
          >
            Conversational workspace loads in Phase 5.
          </p>
        </div>
      </main>
    </div>
  );
}
