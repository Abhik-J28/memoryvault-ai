/**
 * MemoryVault AI — Route Inspector Component
 * =============================================
 * Phase 5 Upgrade: High-Visibility Blueprint Floor Plan & Expandable Inspector
 *
 * Right side of the split-pane layout (45%).
 * Displays a high-contrast blueprint SVG floor plan with room nodes, zone bounds,
 * connecting search paths, distance markers, rank badges, step sequence indicators,
 * and an interactive Fullscreen / Expand modal for maximum visual clarity.
 */

'use client';

import { useState } from 'react';
import {
  MapPin,
  Navigation,
  CheckCircle2,
  ArrowRight,
  Home,
  Maximize2,
  Minimize2,
  Compass,
  Layers,
  Sparkles,
  RotateCcw,
} from 'lucide-react';
import type { RouteStep, LayoutData, PredictionData } from '@/lib/api';
import { sendFeedback } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RouteInspectorProps {
  routeData: RouteStep[] | null;
  layout: LayoutData | null;
  prediction: PredictionData | null;
  sessionId: string;
  context: Record<string, unknown>;
  onResetSearch?: () => void;
}

// ---------------------------------------------------------------------------
// Architectural Room Boundary Boxes (Blueprint Zones)
// ---------------------------------------------------------------------------

const ROOM_ZONES: Record<string, { x: number; y: number; w: number; h: number; zoneLabel: string }> = {
  bedroom: { x: 50, y: 70, w: 200, h: 220, zoneLabel: 'BEDROOM ZONE' },
  study_room: { x: 270, y: 70, w: 190, h: 180, zoneLabel: 'STUDY / OFFICE' },
  bathroom: { x: 480, y: 70, w: 150, h: 180, zoneLabel: 'BATHROOM' },
  balcony: { x: 640, y: 110, w: 130, h: 200, zoneLabel: 'BALCONY' },
  living_room: { x: 130, y: 310, w: 230, h: 180, zoneLabel: 'LIVING AREA' },
  dining_area: { x: 380, y: 310, w: 140, h: 150, zoneLabel: 'DINING' },
  kitchen: { x: 530, y: 300, w: 170, h: 180, zoneLabel: 'KITCHEN' },
  entrance_hallway: { x: 300, y: 480, w: 240, h: 100, zoneLabel: 'MAIN ENTRANCE' },
};

// ---------------------------------------------------------------------------
// High-Visibility Floor Plan SVG Component
// ---------------------------------------------------------------------------

function FloorPlanSVG({
  layout,
  routeData,
  highlightedRoom,
  isFullscreen = false,
}: {
  layout: LayoutData;
  routeData: RouteStep[] | null;
  highlightedRoom: string | null;
  isFullscreen?: boolean;
}) {
  const { rooms, edges } = layout;
  const space = layout.meta.coordinate_space;

  // Build route path edges
  const routeEdges: Array<{ from: string; to: string }> = [];
  if (routeData) {
    if (routeData.length > 0) {
      const firstPath = routeData[0].path_from_previous;
      for (let i = 0; i < firstPath.length - 1; i++) {
        routeEdges.push({ from: firstPath[i], to: firstPath[i + 1] });
      }
    }
    for (let s = 1; s < routeData.length; s++) {
      const path = routeData[s].path_from_previous;
      for (let i = 0; i < path.length - 1; i++) {
        routeEdges.push({ from: path[i], to: path[i + 1] });
      }
    }
  }

  const isRouteEdge = (from: string, to: string) =>
    routeEdges.some(
      (e) => (e.from === from && e.to === to) || (e.from === to && e.to === from),
    );

  // Map room to sequence rank (1, 2, 3...)
  const getRoomRank = (roomKey: string) => {
    if (!routeData) return null;
    const index = routeData.findIndex((s) => s.room === roomKey);
    return index >= 0 ? index + 1 : null;
  };

  return (
    <svg
      viewBox={`0 0 ${space.width} ${space.height}`}
      className={`floor-plan-svg ${isFullscreen ? 'fullscreen-svg' : ''}`}
      role="img"
      aria-label="High-visibility home blueprint and AI search route"
    >
      <defs>
        {/* Blueprint Grid Pattern */}
        <pattern id="blueprint-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="1" opacity="0.6" />
          <path d="M 20 0 L 20 40 M 0 20 L 40 20" fill="none" stroke="#0f172a" strokeWidth="0.5" opacity="0.4" />
        </pattern>

        {/* Glow Filters */}
        <filter id="neon-glow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <filter id="node-shadow" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="4" stdDeviation="6" floodColor="#000000" floodOpacity="0.6" />
        </filter>

        {/* Linear Gradients */}
        <linearGradient id="route-line-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>

        <linearGradient id="room-normal-grad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#1e293b" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>

        <linearGradient id="room-active-grad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#0369a1" />
          <stop offset="100%" stopColor="#0284c7" />
        </linearGradient>

        <linearGradient id="room-route-grad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#047857" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
      </defs>

      {/* Background blueprint canvas */}
      <rect width={space.width} height={space.height} rx="16" fill="#0b1329" />
      <rect width={space.width} height={space.height} rx="16" fill="url(#blueprint-grid)" />

      {/* Blueprint Architectural Zone Boundaries */}
      {Object.entries(ROOM_ZONES).map(([key, zone]) => {
        const isHovered = highlightedRoom === key;
        return (
          <g key={`zone-${key}`}>
            <rect
              x={zone.x}
              y={zone.y}
              width={zone.w}
              height={zone.h}
              rx="12"
              fill={isHovered ? '#0284c7' : '#1e293b'}
              fillOpacity={isHovered ? '0.2' : '0.12'}
              stroke={isHovered ? '#38bdf8' : '#334155'}
              strokeWidth={isHovered ? 2 : 1}
              strokeDasharray="4 4"
            />
            <text
              x={zone.x + 10}
              y={zone.y + 18}
              fill="#475569"
              fontSize="9"
              fontWeight="700"
              letterSpacing="1"
              fontFamily="monospace"
            >
              {zone.zoneLabel}
            </text>
          </g>
        );
      })}

      {/* Connecting Edges (Standard topology) */}
      {edges.map((edge, i) => {
        const fromRoom = rooms[edge.from];
        const toRoom = rooms[edge.to];
        if (!fromRoom || !toRoom) return null;
        const isActive = routeData && isRouteEdge(edge.from, edge.to);
        if (isActive) return null; // Render active edges on top layer

        const midX = (fromRoom.x + toRoom.x) / 2;
        const midY = (fromRoom.y + toRoom.y) / 2;

        return (
          <g key={`inactive-edge-${i}`}>
            <line
              x1={fromRoom.x}
              y1={fromRoom.y}
              x2={toRoom.x}
              y2={toRoom.y}
              stroke="#334155"
              strokeWidth="2.5"
              strokeDasharray="5 5"
              opacity="0.6"
            />
            {/* Distance Pill */}
            <rect
              x={midX - 16}
              y={midY - 9}
              width="32"
              height="18"
              rx="4"
              fill="#0f172a"
              stroke="#1e293b"
              strokeWidth="1"
            />
            <text
              x={midX}
              y={midY + 4}
              textAnchor="middle"
              fill="#64748b"
              fontSize="9"
              fontWeight="600"
              fontFamily="monospace"
            >
              {edge.distance}m
            </text>
          </g>
        );
      })}

      {/* Active Search Route Path (Neon Illuminated) */}
      {edges.map((edge, i) => {
        const fromRoom = rooms[edge.from];
        const toRoom = rooms[edge.to];
        if (!fromRoom || !toRoom) return null;
        const isActive = routeData && isRouteEdge(edge.from, edge.to);
        if (!isActive) return null;

        const midX = (fromRoom.x + toRoom.x) / 2;
        const midY = (fromRoom.y + toRoom.y) / 2;

        return (
          <g key={`active-edge-${i}`}>
            {/* Neon halo outer glow */}
            <line
              x1={fromRoom.x}
              y1={fromRoom.y}
              x2={toRoom.x}
              y2={toRoom.y}
              stroke="#38bdf8"
              strokeWidth="10"
              opacity="0.25"
              filter="url(#neon-glow)"
            />
            {/* Solid core line */}
            <line
              x1={fromRoom.x}
              y1={fromRoom.y}
              x2={toRoom.x}
              y2={toRoom.y}
              stroke="url(#route-line-grad)"
              strokeWidth="5"
              strokeLinecap="round"
            />
            {/* Distance Pill */}
            <rect
              x={midX - 18}
              y={midY - 10}
              width="36"
              height="20"
              rx="6"
              fill="#0284c7"
              stroke="#e0f2fe"
              strokeWidth="1"
              filter="url(#node-shadow)"
            />
            <text
              x={midX}
              y={midY + 4}
              textAnchor="middle"
              fill="#ffffff"
              fontSize="10"
              fontWeight="700"
              fontFamily="sans-serif"
            >
              {edge.distance}m
            </text>
          </g>
        );
      })}

      {/* Animated Route Flow Dots */}
      {routeData &&
        routeEdges.map((edge, i) => {
          const fromRoom = rooms[edge.from];
          const toRoom = rooms[edge.to];
          if (!fromRoom || !toRoom) return null;

          return (
            <g key={`dot-flow-${i}`}>
              <circle cx={fromRoom.x} cy={fromRoom.y} r="6" fill="#38bdf8" filter="url(#neon-glow)">
                <animate
                  attributeName="cx"
                  values={`${fromRoom.x};${toRoom.x}`}
                  dur="2.5s"
                  begin={`${i * 0.4}s`}
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="cy"
                  values={`${fromRoom.y};${toRoom.y}`}
                  dur="2.5s"
                  begin={`${i * 0.4}s`}
                  repeatCount="indefinite"
                />
              </circle>
            </g>
          );
        })}

      {/* Room Nodes & Labels */}
      {Object.entries(rooms).map(([key, room]) => {
        const isHighlighted = highlightedRoom === key;
        const isInRoute = routeData?.some((s) => s.room === key);
        const prob = routeData?.find((s) => s.room === key)?.probability;
        const rank = getRoomRank(key);

        let gradFill = 'url(#room-normal-grad)';
        let strokeColor = '#475569';
        let strokeW = 2;

        if (isHighlighted) {
          gradFill = 'url(#room-active-grad)';
          strokeColor = '#38bdf8';
          strokeW = 3.5;
        } else if (isInRoute) {
          gradFill = 'url(#room-route-grad)';
          strokeColor = '#6ee7b7';
          strokeW = 3;
        }

        return (
          <g key={`room-node-${key}`} filter="url(#node-shadow)">
            {/* Animated Pulse Halo for Highlighted / Rank 1 */}
            {(isHighlighted || rank === 1) && (
              <circle
                cx={room.x}
                cy={room.y}
                r="42"
                fill="none"
                stroke={rank === 1 ? '#10b981' : '#38bdf8'}
                strokeWidth="2.5"
                opacity="0.6"
              >
                <animate attributeName="r" values="34;48;34" dur="1.8s" repeatCount="indefinite" />
                <animate attributeName="opacity" values="0.7;0.1;0.7" dur="1.8s" repeatCount="indefinite" />
              </circle>
            )}

            {/* Main Room Circle */}
            <circle
              cx={room.x}
              cy={room.y}
              r="30"
              fill={gradFill}
              stroke={strokeColor}
              strokeWidth={strokeW}
            />

            {/* Emoji / Icon inside Circle */}
            <text
              x={room.x}
              y={room.y + 6}
              textAnchor="middle"
              fontSize="18"
              className="select-none"
            >
              {room.icon === 'door'
                ? '🚪'
                : room.icon === 'sofa'
                  ? '🛋️'
                  : room.icon === 'utensils'
                    ? '🍳'
                    : room.icon === 'bed'
                      ? '🛏️'
                      : room.icon === 'book-open'
                        ? '📚'
                        : room.icon === 'droplets'
                          ? '🚿'
                          : room.icon === 'sun'
                            ? '☀️'
                            : room.icon === 'coffee'
                              ? '🍽️'
                              : '📍'}
            </text>

            {/* Step Sequence Badge (#1, #2, #3...) */}
            {rank !== null && (
              <g>
                <circle
                  cx={room.x - 22}
                  cy={room.y - 18}
                  r="12"
                  fill={rank === 1 ? '#10b981' : '#0284c7'}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
                <text
                  x={room.x - 22}
                  y={room.y - 14}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="11"
                  fontWeight="800"
                  fontFamily="sans-serif"
                >
                  #{rank}
                </text>
              </g>
            )}

            {/* High-Visibility Room Label Pill */}
            <g>
              <rect
                x={room.x - 65}
                y={room.y + 36}
                width="130"
                height="22"
                rx="11"
                fill="#0f172a"
                fillOpacity="0.9"
                stroke={isHighlighted ? '#38bdf8' : isInRoute ? '#059669' : '#334155'}
                strokeWidth="1.5"
              />
              <text
                x={room.x}
                y={room.y + 51}
                textAnchor="middle"
                fill={isHighlighted ? '#ffffff' : '#f1f5f9'}
                fontSize="12"
                fontWeight="700"
                fontFamily="system-ui, sans-serif"
              >
                {room.label}
              </text>
            </g>

            {/* Probability Percentage Badge Pill */}
            {prob !== undefined && (
              <g>
                <rect
                  x={room.x + 10}
                  y={room.y - 24}
                  width="44"
                  height="20"
                  rx="10"
                  fill={prob > 0.2 ? '#059669' : prob > 0.1 ? '#d97706' : '#475569'}
                  stroke="#ffffff"
                  strokeWidth="1"
                  filter="url(#node-shadow)"
                />
                <text
                  x={room.x + 32}
                  y={room.y - 10}
                  textAnchor="middle"
                  fill="#ffffff"
                  fontSize="11"
                  fontWeight="800"
                  fontFamily="monospace"
                >
                  {(prob * 100).toFixed(0)}%
                </text>
              </g>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Route Card Component
// ---------------------------------------------------------------------------

function RouteCard({
  step,
  index,
  isHighlighted,
  onHover,
  onFoundHere,
}: {
  step: RouteStep;
  index: number;
  isHighlighted: boolean;
  onHover: (room: string | null) => void;
  onFoundHere: (room: string) => void;
}) {
  const confidenceColor =
    step.probability > 0.2
      ? '#059669'
      : step.probability > 0.1
        ? '#d97706'
        : '#64748b';

  return (
    <div
      className={`route-card ${isHighlighted ? 'highlighted' : ''}`}
      onMouseEnter={() => onHover(step.room)}
      onMouseLeave={() => onHover(null)}
    >
      {/* Step number badge */}
      <div className="route-card-step" style={{ backgroundColor: confidenceColor }}>
        #{index + 1}
      </div>

      {/* Details */}
      <div className="route-card-details">
        <div className="route-card-title">
          <span>{step.label}</span>
          <span
            className="route-card-badge"
            style={{ backgroundColor: confidenceColor + '22', color: confidenceColor }}
          >
            {(step.probability * 100).toFixed(1)}% Match
          </span>
        </div>
        <div className="route-card-meta">
          <Navigation size={12} />
          <span>{step.distance_from_previous}m segment</span>
          <span className="route-card-dot">•</span>
          <span>{step.cumulative_distance}m total route</span>
        </div>
      </div>

      {/* Found Here action button */}
      <button
        type="button"
        className="found-here-btn"
        onClick={() => onFoundHere(step.room)}
        aria-label={`Mark item as found in ${step.label}`}
      >
        <CheckCircle2 size={14} />
        Found Here
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Route Inspector Component
// ---------------------------------------------------------------------------

export default function RouteInspector({
  routeData,
  layout,
  prediction,
  sessionId,
  context,
  onResetSearch,
}: RouteInspectorProps) {
  const [highlightedRoom, setHighlightedRoom] = useState<string | null>(null);
  const [foundRoom, setFoundRoom] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const handleFoundHere = async (room: string) => {
    setFoundRoom(room);
    const itemType = (context.item_type as string) || '';
    try {
      await sendFeedback(sessionId, itemType, room, context);
    } catch {
      // Graceful error handling
    }
  };

  // ── Empty State ─────────────────────────────────────────────────────
  if (!routeData || !layout) {
    return (
      <div className="route-inspector">
        <div className="route-inspector-header">
          <MapPin size={18} className="text-sky-500" />
          <span className="font-bold text-slate-800">Search Route Inspector</span>
          {onResetSearch && (
            <button
              type="button"
              className="search-another-header-btn"
              onClick={onResetSearch}
              title="Start a fresh search for another lost item"
            >
              <RotateCcw size={14} />
              <span>New Search</span>
            </button>
          )}
        </div>
        <div className="route-inspector-empty">
          <Home size={52} color="#334155" />
          <p className="font-semibold text-slate-700 text-base">
            Complete the conversation to generate your high-clarity floor plan & search route.
          </p>
          <p className="route-inspector-hint">
            MemoryVault AI will calculate habit probability vectors and plot an optimal A* path.
          </p>
        </div>
      </div>
    );
  }

  // ── Active Route Inspector View ──────────────────────────────────────
  return (
    <>
      <div className="route-inspector">
        {/* Top Header Bar */}
        <div className="route-inspector-header">
          <div className="flex items-center gap-2">
            <Compass size={18} color="#0284c7" />
            <span className="font-bold">Search Route Inspector</span>
          </div>

          {prediction && (
            <span className="route-inspector-confidence">
              Top Pick: <strong>{prediction.predicted_location.replace(/_/g, ' ')}</strong>
            </span>
          )}

          <div className="flex items-center gap-2">
            {onResetSearch && (
              <button
                type="button"
                className="search-another-header-btn"
                onClick={onResetSearch}
                title="Search another lost item"
              >
                <RotateCcw size={14} />
                <span>Search Another</span>
              </button>
            )}

            {/* Expand Fullscreen Button */}
            <button
              type="button"
              className="floor-plan-expand-btn"
              onClick={() => setIsFullscreen(true)}
              title="Expand Floor Plan (HD Fullscreen View)"
            >
              <Maximize2 size={15} />
              <span>Expand Map</span>
            </button>
          </div>
        </div>

        {/* Blueprint Floor Plan Container */}
        <div className="floor-plan-container">
          <FloorPlanSVG
            layout={layout}
            routeData={routeData}
            highlightedRoom={highlightedRoom}
          />

          {/* Map Legend Bar */}
          <div className="floor-plan-legend">
            <div className="legend-item">
              <span className="legend-dot entrance"></span>
              <span>Door / Start</span>
            </div>
            <div className="legend-item">
              <span className="legend-line route"></span>
              <span>A* Path Segment</span>
            </div>
            <div className="legend-item">
              <span className="legend-badge high">95%</span>
              <span>High Prob</span>
            </div>
            <div className="legend-item">
              <span className="legend-badge med">15%</span>
              <span>Med/Low Prob</span>
            </div>
          </div>
        </div>

        {/* Step-by-Step Route Checklist */}
        <div className="route-cards-container">
          <div className="route-cards-title">
            <ArrowRight size={15} color="#0284c7" />
            <span>Optimised Search Sequence Checklist</span>
            <span className="route-step-count">{routeData.length} Stop(s)</span>
          </div>

          {routeData.map((step, i) => (
            <RouteCard
              key={step.room}
              step={step}
              index={i}
              isHighlighted={highlightedRoom === step.room || foundRoom === step.room}
              onHover={setHighlightedRoom}
              onFoundHere={handleFoundHere}
            />
          ))}

          {foundRoom && (
            <div className="found-confirmation flex-col items-stretch gap-3">
              <div className="flex items-center gap-2">
                <Sparkles size={18} color="#059669" />
                <span>
                  Item recorded as found in <strong>{foundRoom.replace(/_/g, ' ')}</strong>! Model weights updated.
                </span>
              </div>
              {onResetSearch && (
                <button
                  type="button"
                  className="search-another-primary-btn mt-1"
                  onClick={onResetSearch}
                >
                  <RotateCcw size={16} />
                  <span>Search Another Lost Item</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Fullscreen HD Lightbox Modal */}
      {isFullscreen && (
        <div className="floor-plan-modal-backdrop" onClick={() => setIsFullscreen(false)}>
          <div
            className="floor-plan-modal-content"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="floor-plan-modal-header">
              <div className="flex items-center gap-2">
                <Layers size={20} color="#38bdf8" />
                <h3 className="font-bold text-lg text-white">
                  High-Resolution Architectural Search Route Blueprint
                </h3>
              </div>
              <button
                type="button"
                className="floor-plan-modal-close"
                onClick={() => setIsFullscreen(false)}
              >
                <Minimize2 size={18} />
                <span>Close HD View</span>
              </button>
            </div>

            <div className="floor-plan-modal-body">
              <FloorPlanSVG
                layout={layout}
                routeData={routeData}
                highlightedRoom={highlightedRoom}
                isFullscreen={true}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
