/**
 * MemoryVault AI - Supabase Client Helper
 * ========================================
 * Phase 1, Step 3
 *
 * Initialises and exports a singleton Supabase client using credentials
 * sourced from Next.js public environment variables.
 *
 * Required env vars (set in .env.local):
 *   NEXT_PUBLIC_SUPABASE_URL
 *   NEXT_PUBLIC_SUPABASE_ANON_KEY
 */

import { createClient, SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl: string | undefined = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey: string | undefined = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl) {
  console.warn(
    '[MemoryVault] Warning: NEXT_PUBLIC_SUPABASE_URL is not defined. ' +
      'Supabase features will not work. Set it in your .env.local file.'
  );
}

if (!supabaseAnonKey) {
  console.warn(
    '[MemoryVault] Warning: NEXT_PUBLIC_SUPABASE_ANON_KEY is not defined. ' +
      'Supabase features will not work. Set it in your .env.local file.'
  );
}

// Defensive initialisation: fall back to empty strings so createClient does not
// throw synchronously; missing credentials will surface as runtime API errors.
const supabase: SupabaseClient = createClient(
  supabaseUrl ?? '',
  supabaseAnonKey ?? ''
);

export default supabase;
