/**
 * MemoryVault AI — Quick-Reply Chips Component
 * ==============================================
 * Phase 5
 *
 * Reusable row of clickable pill buttons that the bot presents
 * as quick-reply options.  Clicking a chip fires the onSelect
 * callback with the chip label.
 */

'use client';

interface QuickChipsProps {
  chips: string[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}

export default function QuickChips({
  chips,
  onSelect,
  disabled = false,
}: QuickChipsProps) {
  if (!chips.length) return null;

  return (
    <div className="flex flex-wrap gap-2 px-1 py-2">
      {chips.map((chip) => (
        <button
          key={chip}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(chip)}
          className="quick-chip"
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
