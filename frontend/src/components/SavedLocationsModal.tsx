/**
 * MemoryVault AI — Saved Locations Manager Modal
 * ================================================
 * Redesigned to match the high-end AuthModal (Sign In / Register) UI.
 * Features:
 *  - Floating animated background particles
 *  - Interactive 3D parallax tilt card on mouse move
 *  - Shimmering glowing top border gradient
 *  - Smooth tab switching between 'Saved Places' and 'Pin New Habit'
 *  - Glassmorphism design system with pink/purple accent theme
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, useMotionValue, useTransform } from 'framer-motion';
import {
  Bookmark,
  Plus,
  Trash2,
  X,
  Sparkles,
  MapPin,
  CheckCircle2,
  Package,
  Compass,
  FileText,
  ArrowRight,
  ShieldCheck,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CustomLocation } from '@/lib/api';
import { getCustomLocations, saveCustomLocation, deleteCustomLocation } from '@/lib/api';

interface SavedLocationsModalProps {
  isOpen: boolean;
  username: string;
  onClose: () => void;
  onLocationsUpdated?: () => void;
}

const ITEMS_LIST = [
  { id: 'keys', label: 'Car / House Keys' },
  { id: 'wallet', label: 'Wallet / Purse' },
  { id: 'phone', label: 'Mobile Phone' },
  { id: 'spectacles', label: 'Reading Glasses' },
  { id: 'earphones', label: 'Wireless Earbuds' },
];

const ROOMS_LIST = [
  { id: 'entrance_hallway', label: 'Entrance Hallway' },
  { id: 'living_room', label: 'Living Room' },
  { id: 'dining_area', label: 'Dining Area' },
  { id: 'kitchen', label: 'Kitchen' },
  { id: 'bedroom', label: 'Bedroom' },
  { id: 'study_room', label: 'Study Room' },
  { id: 'bathroom', label: 'Bathroom' },
  { id: 'balcony', label: 'Balcony' },
];

// ---------------------------------------------------------------------------
// Background Floating Glow Orbs
// ---------------------------------------------------------------------------
function HabitFloatingOrbs() {
  return (
    <div className="auth-orbs-container" aria-hidden="true">
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className={`auth-orb auth-orb-${i + 1}`}
          style={{
            background:
              i % 2 === 0
                ? 'radial-gradient(circle, rgba(236,72,153,0.35), transparent 70%)'
                : 'radial-gradient(circle, rgba(168,85,247,0.3), transparent 70%)',
          }}
          animate={{
            x: [0, 30 * Math.sin(i * 1.3), -25 * Math.cos(i), 0],
            y: [0, -30 * Math.cos(i * 0.9), 25 * Math.sin(i), 0],
            scale: [1, 1.15, 0.92, 1],
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
// Main Saved Locations Modal Component
// ---------------------------------------------------------------------------
export default function SavedLocationsModal({
  isOpen,
  username,
  onClose,
  onLocationsUpdated,
}: SavedLocationsModalProps) {
  const [activeTab, setActiveTab] = useState<'list' | 'add'>('list');
  const [locations, setLocations] = useState<CustomLocation[]>([]);
  const [loading, setLoading] = useState(false);

  // Form inputs
  const [selectedItem, setSelectedItem] = useState('keys');
  const [selectedRoom, setSelectedRoom] = useState('study_room');
  const [notes, setNotes] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Focused state for styling inputs
  const [itemFocused, setItemFocused] = useState(false);
  const [roomFocused, setRoomFocused] = useState(false);
  const [notesFocused, setNotesFocused] = useState(false);

  // 3D Parallax tilt effect on mouse move
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const rotateX = useTransform(mouseY, [-300, 300], [2.5, -2.5]);
  const rotateY = useTransform(mouseX, [-300, 300], [-2.5, 2.5]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      mouseX.set(e.clientX - rect.left - rect.width / 2);
      mouseY.set(e.clientY - rect.top - rect.height / 2);
    },
    [mouseX, mouseY],
  );

  const loadLocations = useCallback(async () => {
    if (!username) return;
    setLoading(true);
    try {
      const data = await getCustomLocations(username);
      setLocations(data);
    } catch {
      // Fallback
    } finally {
      setLoading(false);
    }
  }, [username]);

  useEffect(() => {
    if (isOpen && username) {
      loadLocations();
    }
  }, [isOpen, username, loadLocations]);

  // Reset status on tab switch
  useEffect(() => {
    setStatusMsg(null);
    setErrorMsg(null);
  }, [activeTab]);

  if (!isOpen) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    setErrorMsg(null);
    setIsSaving(true);
    try {
      const res = await saveCustomLocation(username, selectedItem, selectedRoom, notes);
      if (res.success) {
        setStatusMsg(
          `Successfully saved ${selectedRoom.replace(/_/g, ' ').toUpperCase()} for ${selectedItem.replace(/_/g, ' ').toUpperCase()}!`,
        );
        setNotes('');
        await loadLocations();
        if (onLocationsUpdated) onLocationsUpdated();
      } else {
        setErrorMsg('Failed to save habit location.');
      }
    } catch {
      setErrorMsg('Network error connecting to backend.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteCustomLocation(id, username);
      await loadLocations();
      if (onLocationsUpdated) onLocationsUpdated();
    } catch {
      // Graceful error fallback
    }
  };

  // Motion variants for tab sliding
  const slideVariants = {
    enter: (dir: number) => ({ x: dir > 0 ? 50 : -50, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir: number) => ({ x: dir > 0 ? -50 : 50, opacity: 0 }),
  };

  const tabDirection = activeTab === 'add' ? 1 : -1;

  return (
    <div className="habit-overlay" onClick={onClose}>
      <HabitFloatingOrbs />

      <motion.div
        className="habit-card"
        initial={{ opacity: 0, y: 35, scale: 0.94 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 25, scale: 0.95 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        style={{ rotateX, rotateY, perspective: 1200 }}
        onMouseMove={handleMouseMove}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Shimmering top glowing gradient line */}
        <div className="habit-card-glow" />

        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="habit-close-btn"
          aria-label="Close habit places modal"
        >
          <X size={17} />
        </button>

        {/* Brand Header */}
        <div className="habit-brand">
          <motion.div
            className="habit-brand-icon"
            animate={{ rotate: [0, 6, -6, 0] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Bookmark size={26} color="#ffffff" />
          </motion.div>
          <h2 className="habit-brand-title">My Saved Item Habit Places</h2>
          <p className="habit-brand-sub">
            Pink Map Overrides &amp; Adaptive Habit Pinning
          </p>
        </div>

        {/* Tab Pills Bar (Matches Auth Tab Bar UI) */}
        <div className="auth-tab-bar">
          <button
            type="button"
            className={cn('auth-tab', activeTab === 'list' && 'habit-tab--active')}
            onClick={() => setActiveTab('list')}
          >
            <span className="flex items-center justify-center gap-1.5">
              <Layers size={14} />
              Saved Places ({locations.length})
            </span>
          </button>
          <button
            type="button"
            className={cn('auth-tab', activeTab === 'add' && 'habit-tab--active')}
            onClick={() => setActiveTab('add')}
          >
            <span className="flex items-center justify-center gap-1.5">
              <Plus size={14} />
              Pin New Habit
            </span>
          </button>
        </div>

        {/* Modal Body with Animated Tab Panels */}
        <div className="auth-body">
          <AnimatePresence mode="wait" custom={tabDirection}>
            {/* ── TAB 1: SAVED PLACES LIST ────────────────────────── */}
            {activeTab === 'list' && (
              <motion.div
                key="list"
                custom={tabDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.28, ease: 'easeOut' }}
                className="flex flex-col gap-4"
              >
                {/* Info Callout */}
                <div className="flex items-start gap-3 rounded-xl border border-pink-500/30 bg-pink-500/10 p-3 text-xs text-pink-200">
                  <Sparkles size={18} className="shrink-0 text-pink-400 mt-0.5" />
                  <div className="leading-snug">
                    <span className="font-bold text-pink-300">
                      High-Priority Blueprint Highlights
                    </span>
                    <p className="mt-0.5 text-[11.5px] opacity-90">
                      Locations saved here will be highlighted in vibrant{' '}
                      <strong className="text-pink-300 font-bold">Pink (#ec4899)</strong>{' '}
                      directly on your search route map alongside ML predictions.
                    </p>
                  </div>
                </div>

                {loading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-3">
                    <div className="auth-spinner border-t-pink-500" />
                    <span className="text-xs text-slate-400">Loading your habit places...</span>
                  </div>
                ) : locations.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700/60 bg-slate-900/40 p-8 text-center gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-pink-500/15 text-pink-400">
                      <Bookmark size={24} />
                    </div>
                    <div>
                      <p className="text-sm font-bold text-slate-200">
                        No habit locations saved yet
                      </p>
                      <p className="text-xs text-slate-400 mt-1 max-w-xs">
                        Pin your everyday spots or record &quot;Found Here&quot; in routes to see dynamic pink highlights.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab('add')}
                      className="mt-2 flex items-center gap-2 rounded-xl bg-pink-600/30 border border-pink-500/40 px-4 py-2 text-xs font-bold text-pink-200 hover:bg-pink-600 hover:text-white transition-all cursor-pointer active:scale-95 shadow-sm"
                    >
                      <Plus size={14} />
                      Pin Your First Habit
                    </button>
                  </div>
                ) : (
                  <div className="habit-list-scroll flex flex-col gap-2.5">
                    {locations.map((loc, idx) => {
                      const isTop = idx === 0;
                      const isMan = loc.is_manual === 1;
                      const count = loc.entry_count ?? 1;

                      return (
                        <div
                          key={loc.id}
                          className={`flex items-center justify-between rounded-xl border p-3.5 transition-all ${
                            isTop
                              ? 'border-pink-500/70 bg-pink-950/25 shadow-lg shadow-pink-950/30'
                              : 'border-slate-800 bg-slate-900/80 hover:border-pink-500/50'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-pink-500/20 text-pink-400 border border-pink-500/30 shadow-inner">
                              <MapPin size={17} />
                            </div>

                            <div className="flex flex-col min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-bold text-slate-100">
                                  {loc.item_type.replace(/_/g, ' ').toUpperCase()}{' '}
                                  <span className="text-slate-500">→</span>{' '}
                                  <span className="text-pink-400 font-extrabold">
                                    {loc.room.replace(/_/g, ' ').toUpperCase()}
                                  </span>
                                </span>

                                {isTop && (
                                  <span className="rounded-md bg-pink-500/30 border border-pink-500/60 px-2 py-0.5 text-[10px] font-black text-pink-300 tracking-wide uppercase shadow-sm">
                                    ⭐ Top Habit
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400 flex-wrap">
                                {isMan ? (
                                  <span className="text-sky-400 font-bold flex items-center gap-1">
                                    📌 Manual Pin
                                  </span>
                                ) : (
                                  <span className="text-emerald-400 font-semibold flex items-center gap-1">
                                    📍 Found Here ({count} {count === 1 ? 'entry' : 'entries'})
                                  </span>
                                )}
                                {loc.notes && (
                                  <span className="text-slate-400 truncate max-w-[200px]">
                                    • &quot;{loc.notes}&quot;
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            onClick={() => handleDelete(loc.id)}
                            className="p-2 rounded-lg text-slate-500 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/40 border border-transparent transition-all cursor-pointer shrink-0 ml-2"
                            title="Delete habit location"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                <div className="auth-hint mt-1">
                  <ShieldCheck size={13} className="auth-hint-icon text-pink-400" />
                  <span>Habit spots are prioritized and automatically synced to your account.</span>
                </div>
              </motion.div>
            )}

            {/* ── TAB 2: PIN NEW HABIT FORM ────────────────────────── */}
            {activeTab === 'add' && (
              <motion.div
                key="add"
                custom={tabDirection}
                variants={slideVariants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.28, ease: 'easeOut' }}
              >
                <form onSubmit={handleSave} className="flex flex-col gap-4">
                  {/* Status / Error Alerts */}
                  <AnimatePresence mode="wait">
                    {statusMsg && (
                      <motion.div
                        key="status"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-2 rounded-xl border border-emerald-500/40 bg-emerald-500/15 p-3 text-xs font-semibold text-emerald-300"
                      >
                        <CheckCircle2 size={16} className="shrink-0 text-emerald-400" />
                        <span>{statusMsg}</span>
                      </motion.div>
                    )}
                    {errorMsg && (
                      <motion.div
                        key="err"
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="auth-error !m-0"
                      >
                        <span>⚠️ {errorMsg}</span>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Target Item Input */}
                  <div className="auth-field">
                    <label className="auth-label">Target Item</label>
                    <div
                      className={cn(
                        'auth-input-wrap',
                        itemFocused && 'auth-input-wrap--focused',
                      )}
                    >
                      <Package size={16} className="auth-input-icon text-pink-400" />
                      <select
                        value={selectedItem}
                        onChange={(e) => setSelectedItem(e.target.value)}
                        onFocus={() => setItemFocused(true)}
                        onBlur={() => setItemFocused(false)}
                        className="habit-select"
                      >
                        {ITEMS_LIST.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Room Location Input */}
                  <div className="auth-field">
                    <label className="auth-label">Usual Room Location</label>
                    <div
                      className={cn(
                        'auth-input-wrap',
                        roomFocused && 'auth-input-wrap--focused',
                      )}
                    >
                      <Compass size={16} className="auth-input-icon text-pink-400" />
                      <select
                        value={selectedRoom}
                        onChange={(e) => setSelectedRoom(e.target.value)}
                        onFocus={() => setRoomFocused(true)}
                        onBlur={() => setRoomFocused(false)}
                        className="habit-select"
                      >
                        {ROOMS_LIST.map((room) => (
                          <option key={room.id} value={room.id}>
                            {room.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Habit Note (Optional) */}
                  <div className="auth-field">
                    <label className="auth-label">Habit Note (Optional)</label>
                    <div
                      className={cn(
                        'auth-input-wrap',
                        notesFocused && 'auth-input-wrap--focused',
                      )}
                    >
                      <FileText size={16} className="auth-input-icon text-pink-400" />
                      <input
                        type="text"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        onFocus={() => setNotesFocused(true)}
                        onBlur={() => setNotesFocused(false)}
                        placeholder="e.g. On top of the study desk shelf"
                        className="auth-input"
                      />
                    </div>
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isSaving}
                    className="habit-primary-btn mt-1"
                  >
                    {isSaving ? (
                      <div className="auth-spinner" />
                    ) : (
                      <>
                        <Plus size={16} />
                        <span>Save Habit Override Location</span>
                        <ArrowRight size={16} className="auth-btn-arrow" />
                      </>
                    )}
                  </button>

                  <div className="auth-hint">
                    <Sparkles size={13} className="auth-hint-icon text-pink-400" />
                    <span>Saved habits instantly appear as vibrant pink rings on your map.</span>
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
