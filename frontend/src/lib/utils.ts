/**
 * MemoryVault AI — Utility Functions
 * ====================================
 * Lightweight className merge utility (shadcn-compatible)
 */

export function cn(...inputs: (string | undefined | null | false)[]) {
  return inputs.filter(Boolean).join(' ');
}
