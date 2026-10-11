/**
 * MemoryVault AI — API Client Helper
 * ====================================
 * Phase 5
 *
 * Centralised HTTP client for all backend API interactions.
 */

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://127.0.0.1:8000';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RouteStep {
  room: string;
  label: string;
  probability: number;
  distance_from_previous: number;
  cumulative_distance: number;
  x: number;
  y: number;
  path_from_previous: string[];
}

export interface ChatResponse {
  session_id: string;
  bot_message: string;
  quick_replies: string[];
  state: string;
  context: Record<string, unknown>;
  route_data?: RouteStep[] | null;
  layout?: LayoutData | null;
  prediction?: PredictionData | null;
  custom_user_rooms?: string[];
  repeated_finding_rooms?: string[];
  finding_counts?: Record<string, number>;
}

export interface AuthUser {
  id: number;
  username: string;
}

export interface AuthResponse {
  success: boolean;
  error?: string;
  user?: AuthUser;
}

export interface CustomLocation {
  id: number;
  username: string;
  item_type: string;
  room: string;
  notes?: string;
  entry_count?: number;
  is_manual?: number;
  created_at?: string;
}

export interface PredictionData {
  predicted_location: string;
  probabilities: Record<string, number>;
  top3: string[];
}

export interface LayoutRoom {
  label: string;
  x: number;
  y: number;
  icon: string;
}

export interface LayoutEdge {
  from: string;
  to: string;
  distance: number;
}

export interface LayoutData {
  meta: { coordinate_space: { width: number; height: number } };
  rooms: Record<string, LayoutRoom>;
  edges: LayoutEdge[];
}

export interface AnalyticsMetrics {
  accuracy: number;
  top3_accuracy: number;
  roc_auc_macro: number;
  classification_report: Record<string, unknown>;
  confusion_matrix: number[][];
  class_labels: string[];
  roc_curves: Record<string, { fpr: number[]; tpr: number[] }>;
}

export interface ClusterPoint {
  x: number;
  y: number;
  cluster: number;
}

export interface ClusterData {
  points: ClusterPoint[];
  centroids: ClusterPoint[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * Send a chat message to the backend and return the bot's response.
 */
export async function sendChatMessage(
  sessionId: string,
  message: string,
  state: string,
  context: Record<string, unknown>,
  username?: string | null,
): Promise<ChatResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      state,
      context,
      username: username || null,
    }),
  });

  if (!res.ok) {
    throw new Error(`Chat API error: ${res.status}`);
  }

  return res.json();
}

/**
 * Register a new user account.
 */
export async function registerUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return res.json();
}

/**
 * Authenticate user credentials.
 */
export async function loginUser(username: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  return res.json();
}

/**
 * Save custom user location override.
 */
export async function saveCustomLocation(
  username: string,
  itemType: string,
  room: string,
  notes?: string,
): Promise<{ success: boolean; message?: string }> {
  const res = await fetch(`${BACKEND_URL}/api/v1/user/custom-locations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, item_type: itemType, room, notes: notes || '' }),
  });
  return res.json();
}

/**
 * Fetch custom user locations.
 */
export async function getCustomLocations(
  username: string,
  itemType?: string,
): Promise<CustomLocation[]> {
  const query = itemType
    ? `username=${encodeURIComponent(username)}&item_type=${encodeURIComponent(itemType)}`
    : `username=${encodeURIComponent(username)}`;
  const res = await fetch(`${BACKEND_URL}/api/v1/user/custom-locations?${query}`);
  if (!res.ok) return [];
  return res.json();
}

/**
 * Delete a custom location override.
 */
export async function deleteCustomLocation(
  locationId: number,
  username: string,
): Promise<{ success: boolean }> {
  const res = await fetch(
    `${BACKEND_URL}/api/v1/user/custom-locations/${locationId}?username=${encodeURIComponent(username)}`,
    { method: 'DELETE' },
  );
  return res.json();
}

/**
 * Send "Found Here" feedback.
 */
export async function sendFeedback(
  sessionId: string,
  itemType: string,
  foundLocation: string,
  context: Record<string, unknown>,
  username?: string | null,
): Promise<void> {
  await fetch(`${BACKEND_URL}/api/v1/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      item_type: itemType,
      found_location: foundLocation,
      context,
      username: username || null,
    }),
  });
}


/**
 * Fetch ML model performance metrics.
 */
export async function fetchAnalyticsMetrics(): Promise<AnalyticsMetrics> {
  const res = await fetch(`${BACKEND_URL}/api/v1/analytics/metrics`);
  if (!res.ok) throw new Error(`Analytics metrics error: ${res.status}`);
  return res.json();
}

/**
 * Fetch PCA cluster visualisation data.
 */
export async function fetchClusterData(): Promise<ClusterData> {
  const res = await fetch(`${BACKEND_URL}/api/v1/analytics/clusters`);
  if (!res.ok) throw new Error(`Cluster data error: ${res.status}`);
  return res.json();
}

/**
 * Fetch home layout graph.
 */
export async function fetchLayout(): Promise<LayoutData> {
  const res = await fetch(`${BACKEND_URL}/api/v1/layout`);
  if (!res.ok) throw new Error(`Layout error: ${res.status}`);
  return res.json();
}
