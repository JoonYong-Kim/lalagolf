export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type ApiUser = {
  id: string;
  email: string;
  display_name: string;
};

export type UploadReview = {
  id: string;
  status: string;
  parsed_round: ParsedRound;
  warnings: UploadWarning[];
  user_edits: Record<string, unknown>;
  committed_round_id: string | null;
};

export type ParsedRound = {
  file_name?: string;
  play_date?: string | null;
  tee_off_time?: string | null;
  course_name?: string | null;
  companions?: string[];
  total_score?: number | null;
  total_par?: number | null;
  score_to_par?: number | null;
  hole_count?: number;
  holes?: ParsedHole[];
};

export type ParsedHole = {
  hole_number: number;
  par: number;
  score: number;
  putts: number;
  gir: boolean | null;
  penalties: number;
  shots: ParsedShot[];
};

export type ParsedShot = {
  shot_number: number;
  club: string | null;
  distance: number | null;
  start_lie: string | null;
  end_lie: string | null;
  result_grade: string | null;
  feel_grade: string | null;
  penalty_type: string | null;
  penalty_strokes: number;
  score_cost: number;
  raw_text: string | null;
};

export type UploadWarning = {
  code: string;
  message: string;
  path: string;
  raw_text?: string;
  details?: Record<string, unknown>;
};

export type RoundListItem = {
  id: string;
  course_name: string;
  play_date: string;
  total_score: number | null;
  total_par: number | null;
  score_to_par: number | null;
  hole_count: number;
  computed_status: string;
  companions: string[];
};

export type RoundListResponse = {
  items: RoundListItem[];
  total: number;
  limit: number;
  offset: number;
};

export type RoundDetail = RoundListItem & {
  tee: string | null;
  weather: string | null;
  target_score: number | null;
  visibility: string;
  notes_private: string | null;
  holes: RoundHole[];
  metrics: {
    putts_total?: number | null;
    gir_count?: number | null;
    fairway_hit_rate?: number | null;
    penalties_total?: number | null;
  };
  insights: Array<Record<string, unknown>>;
};

export type RoundHole = {
  id: string;
  round_id: string;
  hole_number: number;
  par: number;
  score: number | null;
  putts: number | null;
  fairway_hit: boolean | null;
  gir: boolean | null;
  up_and_down: boolean | null;
  sand_save: boolean | null;
  penalties: number;
  shots: RoundShot[];
};

export type RoundShot = {
  id: string;
  round_id: string;
  hole_id: string;
  shot_number: number;
  club: string | null;
  club_normalized: string | null;
  distance: number | null;
  start_lie: string | null;
  end_lie: string | null;
  result_grade: string | null;
  feel_grade: string | null;
  penalty_type: string | null;
  penalty_strokes: number;
  score_cost: number;
  raw_text: string | null;
};

export type DashboardSummary = {
  kpis: {
    round_count?: number;
    average_score?: number | null;
    best_score?: number | null;
    average_putts?: number | null;
  };
  recent_rounds: RoundListItem[];
  score_trend: Array<{
    round_id: string;
    play_date: string;
    course_name: string;
    total_score: number | null;
    score_to_par: number | null;
  }>;
  priority_insights: Array<{
    problem?: string;
    evidence?: string;
    impact?: string;
    next_action?: string;
    confidence?: string;
  }>;
};

export type InsightUnit = {
  id: string;
  round_id: string | null;
  scope_type: string;
  scope_key: string;
  category: string;
  root_cause: string;
  primary_evidence_metric: string;
  dedupe_key: string;
  problem: string;
  evidence: string;
  impact: string;
  next_action: string;
  confidence: string;
  priority_score: number;
  status: string;
};

export type AnalyticsTrend = {
  kpis: DashboardSummary["kpis"];
  score_trend: DashboardSummary["score_trend"];
  category_summary: Array<{
    category: string;
    count: number;
    total_shot_value: number;
    avg_shot_value: number;
  }>;
  insights: InsightUnit[];
};

export type SharedRound = {
  title: string;
  round: {
    id: string;
    course_name: string;
    play_date: string | null;
    play_month: string;
    total_score: number | null;
    total_par: number | null;
    score_to_par: number | null;
    hole_count: number;
  };
  holes: Array<{
    hole_number: number;
    par: number;
    score: number | null;
    putts: number | null;
    gir: boolean | null;
    penalties: number;
  }>;
  metrics: {
    putts_total?: number | null;
    penalties_total?: number | null;
    gir_count?: number | null;
  };
  insights: Array<{
    category: string;
    problem: string;
    evidence: string;
    impact: string;
    next_action: string;
    confidence: string;
    priority_score: number;
  }>;
};

export type ChatThread = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  evidence: Record<string, unknown>;
  created_at: string;
};

export type ChatThreadDetail = ChatThread & {
  messages: ChatMessage[];
};

export type AdminUploadError = {
  id: string;
  source_file_id: string;
  filename: string | null;
  status: string;
  warnings: UploadWarning[];
  created_at: string;
};

type ApiEnvelope<T> = {
  data: T;
};

export async function getApiHealth(): Promise<{ status: string }> {
  const response = await fetch(`${apiBaseUrl}/health`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`API health check failed: ${response.status}`);
  }

  return response.json();
}

export async function registerOrLogin(payload: {
  email: string;
  password: string;
  display_name?: string;
}): Promise<ApiUser> {
  const registerResponse = await apiFetch<ApiEnvelope<{ user: ApiUser }>>("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      display_name: payload.display_name ?? "Lala Golfer",
    }),
  });
  return registerResponse.data.user;
}

export async function login(payload: { email: string; password: string }): Promise<ApiUser> {
  const response = await apiFetch<ApiEnvelope<{ user: ApiUser }>>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data.user;
}

export async function getCurrentUser(): Promise<ApiUser | null> {
  const response = await fetch(`${apiBaseUrl}/me`, {
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Current user request failed: ${response.status}`);
  }
  const data = (await response.json()) as ApiEnvelope<{ user: ApiUser }>;
  return data.data.user;
}

export async function uploadRoundFile(file: File): Promise<{
  source_file_id: string;
  upload_review_id: string;
  status: string;
  job_id: string;
}> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl}/uploads/round-file`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!response.ok) {
    throw new Error(await responseText(response, "Upload failed"));
  }
  const data = (await response.json()) as ApiEnvelope<{
    source_file_id: string;
    upload_review_id: string;
    status: string;
    job_id: string;
  }>;
  return data.data;
}

export async function getUploadReview(uploadReviewId: string): Promise<UploadReview> {
  const response = await apiFetch<ApiEnvelope<UploadReview>>(
    `/uploads/${uploadReviewId}/review`,
    { method: "GET" },
  );
  return response.data;
}

export async function updateUploadReview(
  uploadReviewId: string,
  userEdits: Record<string, unknown>,
): Promise<UploadReview> {
  const response = await apiFetch<ApiEnvelope<UploadReview>>(
    `/uploads/${uploadReviewId}/review`,
    {
      method: "PATCH",
      body: JSON.stringify({ user_edits: userEdits }),
    },
  );
  return response.data;
}

export async function commitUploadReview(uploadReviewId: string): Promise<{
  round_id: string;
  computed_status: string;
  analytics_job_id: string;
}> {
  const response = await apiFetch<ApiEnvelope<{
    round_id: string;
    computed_status: string;
    analytics_job_id: string;
  }>>(`/uploads/${uploadReviewId}/commit`, {
    method: "POST",
    body: JSON.stringify({
      visibility: "private",
      share_course: false,
      share_exact_date: false,
    }),
  });
  return response.data;
}

export async function getRounds(params?: {
  limit?: number;
  offset?: number;
  year?: string;
  course?: string;
  companion?: string;
}): Promise<RoundListResponse> {
  const search = new URLSearchParams();
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.offset) search.set("offset", String(params.offset));
  if (params?.year) search.set("year", params.year);
  if (params?.course) search.set("course", params.course);
  if (params?.companion) search.set("companion", params.companion);
  const query = search.toString();
  const response = await apiFetch<ApiEnvelope<RoundListResponse>>(
    `/rounds${query ? `?${query}` : ""}`,
    { method: "GET" },
  );
  return response.data;
}

export async function getRound(roundId: string): Promise<RoundDetail> {
  const response = await apiFetch<ApiEnvelope<RoundDetail>>(`/rounds/${roundId}`, {
    method: "GET",
  });
  return response.data;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiFetch<ApiEnvelope<DashboardSummary>>("/analytics/summary", {
    method: "GET",
  });
  return response.data;
}

export async function requestRoundRecalculation(roundId: string): Promise<{
  round_id: string;
  computed_status: string;
  analytics_job_id: string;
}> {
  const response = await apiFetch<ApiEnvelope<{
    round_id: string;
    computed_status: string;
    analytics_job_id: string;
  }>>(`/rounds/${roundId}/recalculate`, { method: "POST" });
  return response.data;
}

export async function getAnalyticsTrends(): Promise<AnalyticsTrend> {
  const response = await apiFetch<ApiEnvelope<AnalyticsTrend>>("/analytics/trends", {
    method: "GET",
  });
  return response.data;
}

export async function getInsights(status = "active"): Promise<InsightUnit[]> {
  const response = await apiFetch<ApiEnvelope<InsightUnit[]>>(`/insights?status=${status}`, {
    method: "GET",
  });
  return response.data;
}

export async function updateInsightStatus(
  insightId: string,
  status: "active" | "dismissed",
): Promise<InsightUnit> {
  const response = await apiFetch<ApiEnvelope<InsightUnit>>(`/insights/${insightId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  return response.data;
}

export async function getSharedRound(token: string): Promise<SharedRound> {
  const response = await fetch(`${apiBaseUrl}/shared/${token}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await responseText(response, "Shared round not found"));
  }
  const data = (await response.json()) as ApiEnvelope<SharedRound>;
  return data.data;
}

export async function createChatThread(title?: string): Promise<ChatThread> {
  const response = await apiFetch<ApiEnvelope<ChatThread>>("/chat/threads", {
    method: "POST",
    body: JSON.stringify({ title }),
  });
  return response.data;
}

export async function getChatThread(threadId: string): Promise<ChatThreadDetail> {
  const response = await apiFetch<ApiEnvelope<ChatThreadDetail>>(`/chat/threads/${threadId}`, {
    method: "GET",
  });
  return response.data;
}

export async function sendChatMessage(threadId: string, content: string): Promise<{
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}> {
  const response = await apiFetch<ApiEnvelope<{
    user_message: ChatMessage;
    assistant_message: ChatMessage;
  }>>(`/chat/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
  return response.data;
}

export async function getAdminUploadErrors(limit = 50): Promise<AdminUploadError[]> {
  const response = await apiFetch<ApiEnvelope<AdminUploadError[]>>(
    `/admin/uploads/errors?limit=${limit}`,
    { method: "GET" },
  );
  return response.data;
}

async function apiFetch<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    throw new Error(await responseText(response, `API request failed: ${response.status}`));
  }
  return response.json() as Promise<T>;
}

async function responseText(response: Response, fallback: string): Promise<string> {
  try {
    const payload = await response.json();
    return payload.detail ?? payload.error?.message ?? fallback;
  } catch {
    return fallback;
  }
}
