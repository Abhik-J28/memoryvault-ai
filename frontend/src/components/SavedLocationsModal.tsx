/**
 * MemoryVault AI — Saved Locations Manager Modal
 * ================================================
 * Allows users to add, view, and manage custom item locations.
 * Custom locations trigger a vibrant PINK highlight (#ec4899)
 * on the floor plan SVG blueprint map alongside ML predictions.
 */

'use client';

import { useEffect, useState } from 'react';
import { Bookmark, Plus, Trash2, X, Sparkles, MapPin, CheckCircle2 } from 'lucide-react';
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

export default function SavedLocationsModal({
  isOpen,
  username,
  onClose,
  onLocationsUpdated,
}: SavedLocationsModalProps) {
  const [locations, setLocations] = useState<CustomLocation[]>([]);
  const [loading, setLoading] = useState(false);

  // Form state
  const [selectedItem, setSelectedItem] = useState('keys');
  const [selectedRoom, setSelectedRoom] = useState('study_room');
  const [notes, setNotes] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && username) {
      loadLocations();
    }
  }, [isOpen, username]);

  const loadLocations = async () => {
    setLoading(true);
    try {
      const data = await getCustomLocations(username);
      setLocations(data);
    } catch {
      // Graceful error fallback
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMsg(null);
    try {
      const res = await saveCustomLocation(username, selectedItem, selectedRoom, notes);
      if (res.success) {
        setStatusMsg(`Saved ${selectedRoom.replace('_', ' ')} for ${selectedItem.replace('_', ' ')}!`);
        setNotes('');
        await loadLocations();
        if (onLocationsUpdated) onLocationsUpdated();
      }
    } catch {
      setStatusMsg('Failed to save location.');
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fadeIn">
      <div className="w-full max-w-xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-6 py-4">
          <div className="flex items-center gap-2 text-pink-400">
            <Bookmark size={20} />
            <h3 className="font-extrabold text-white text-base">
              My Saved Item Habit Places <span className="text-xs text-pink-400 font-semibold">(Pink Map Overrides)</span>
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 flex flex-col gap-6 max-h-[80vh] overflow-y-auto">
          {/* Info Banner */}
          <div className="flex items-start gap-3 rounded-xl border border-pink-500/30 bg-pink-500/10 p-3.5 text-xs text-pink-200">
            <Sparkles size={20} className="shrink-0 text-pink-400 mt-0.5" />
            <div>
              <p className="font-bold text-pink-300">User-Adaptive Location Pinning</p>
              <p className="mt-0.5 opacity-90">
                Locations saved here will be highlighted in <strong className="text-pink-300">Vibrant Pink (#ec4899)</strong> directly on your search route blueprint map alongside machine learning predictions!
              </p>
            </div>
          </div>

          {/* Form: Add New Saved Place */}
          <form onSubmit={handleSave} className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Plus size={14} className="text-sky-400" />
              Pin New Habit Location
            </h4>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400">Target Item</label>
                <select
                  value={selectedItem}
                  onChange={(e) => setSelectedItem(e.target.value)}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:border-sky-500 focus:outline-none"
                >
                  {ITEMS_LIST.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400">Usual Room Location</label>
                <select
                  value={selectedRoom}
                  onChange={(e) => setSelectedRoom(e.target.value)}
                  className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white focus:border-pink-500 focus:outline-none"
                >
                  {ROOMS_LIST.map((room) => (
                    <option key={room.id} value={room.id}>
                      {room.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-semibold text-slate-400">Habit Note (Optional)</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. On top of the study desk shelf"
                className="rounded-xl border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none"
              />
            </div>

            {statusMsg && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-semibold">
                <CheckCircle2 size={14} />
                <span>{statusMsg}</span>
              </div>
            )}

            <button
              type="submit"
              className="mt-1 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-pink-600 to-purple-600 py-2.5 text-xs font-bold text-white shadow-md hover:from-pink-500 hover:to-purple-500 transition-all"
            >
              <Plus size={15} />
              Save Habit Override Location
            </button>
          </form>

          {/* List: Existing Saved Locations */}
          <div className="flex flex-col gap-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
              <span>Saved Places List ({locations.length})</span>
            </h4>

            {loading ? (
              <div className="py-6 text-center text-xs text-slate-500">Loading saved places...</div>
            ) : locations.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 p-6 text-center text-xs text-slate-500">
                No custom places saved yet. Add one above to see pink highlights on your blueprint map!
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {locations.map((loc) => (
                  <div
                    key={loc.id}
                    className="flex items-center justify-between rounded-xl border border-pink-500/30 bg-slate-950 p-3 shadow-sm hover:border-pink-500/60 transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-pink-500/20 text-pink-400">
                        <MapPin size={16} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-white">
                          {loc.item_type.replace('_', ' ').toUpperCase()} →{' '}
                          <span className="text-pink-400">{loc.room.replace('_', ' ').toUpperCase()}</span>
                        </span>
                        {loc.notes && <span className="text-[11px] text-slate-400">{loc.notes}</span>}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDelete(loc.id)}
                      className="rounded-lg p-2 text-slate-500 hover:bg-red-500/10 hover:text-red-400 transition-all"
                      title="Delete saved place"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
