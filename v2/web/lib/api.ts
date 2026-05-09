export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:2324/api/v1";
export const googleOAuthStartUrl = `${apiBaseUrl}/auth/google/start`;
export type ApiLocale = "ko" | "en";

export type ApiUser = {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
};

export type UploadReview = {
  id: string;
  status: string;
  parsed_round: ParsedRound;
  warnings: UploadWarning[];
  user_edits: Record<string, unknown>;
  committed_round_id: string | null;
  raw_content: string | null;
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
  upload_review_id: string | null;
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
  item_summary: AnalysisItemSummary[];
  shot_quality_summary: ShotQualitySummary;
  insights: InsightUnit[];
};

export type AnalysisItemSummary = {
  group: string;
  item: string;
  count: number;
  total_shot_value: number;
  avg_shot_value: number;
  result_c_count: number;
  feel_c_count: number;
  penalty_count: number;
  made_count?: number;
  ok_count?: number;
  recovered_count?: number;
  failed_recovery_count?: number;
  ob_count?: number;
  hazard_count?: number;
  good_feel_penalty_count?: number;
  item_rate?: number | null;
  primary_club_group?: string | null;
  up_and_down_chance_count?: number;
  up_and_down_success_count?: number;
  result_c_rate: number | null;
  feel_c_rate: number | null;
  penalty_rate: number | null;
  made_rate?: number | null;
  ok_rate?: number | null;
  recovered_rate?: number | null;
  failed_recovery_rate?: number | null;
  ob_rate?: number | null;
  hazard_rate?: number | null;
  good_feel_penalty_rate?: number | null;
  up_and_down_success_rate?: number | null;
};

export type RoundAnalytics = {
  round_id: string;
  metrics: Record<string, unknown>;
  shot_quality_summary: ShotQualitySummary;
  shot_values: Array<{
    shot_id: string;
    category: string;
    shot_value: number | null;
    expected_before: number | null;
    expected_after: number | null;
    shot_cost: number;
    expected_confidence: string | null;
  }>;
  insights: InsightUnit[];
};

export type ShotQualitySummary = {
  sample_count: number;
  feel_distribution: GradeDistribution;
  result_distribution: GradeDistribution;
  feel_result_matrix: Record<"A" | "B" | "C", Record<"A" | "B" | "C", number>>;
  risk: {
    reproducible_count?: number;
    technical_miss_count?: number;
    lucky_result_count?: number;
    strategy_issue_count?: number;
    high_risk_count?: number;
    driver_tee_shot_count?: number;
    driver_result_c_count?: number;
    driver_result_c_rate?: number | null;
    strategy_issue_rate?: number | null;
    technical_miss_rate?: number | null;
    lucky_result_rate?: number | null;
    high_risk_rate?: number | null;
  };
  tee_result_distribution: GradeDistribution;
  under_90_result_distribution: GradeDistribution;
  over_90_result_distribution: GradeDistribution;
  club_groups: Array<{
    club_group: string;
    count: number;
    feel: Record<"A" | "B" | "C", number>;
    result: Record<"A" | "B" | "C", number>;
    penalty_count: number;
    feel_c_rate: number | null;
    result_c_rate: number | null;
    penalty_rate: number | null;
  }>;
};

export type GradeDistribution = {
  counts: Record<"A" | "B" | "C", number>;
  rates: Record<"A" | "B" | "C", number | null>;
  total: number;
};

export type ShareCreateResponse = {
  id: string;
  round_id: string;
  title: string | null;
  url_path: string | null;
  token: string;
  expires_at: string | null;
  revoked_at: string | null;
  last_accessed_at: string | null;
};

export type ChatStatus = {
  enabled: boolean;
  reachable: boolean;
  model: string;
  base_url: string;
  mode: "llm" | "deterministic";
  detail: string;
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

export type PracticePlan = {
  id: string;
  source_insight_id: string | null;
  title: string;
  purpose: string | null;
  category: string;
  root_cause: string | null;
  drill_json: Record<string, unknown>;
  target_json: Record<string, unknown>;
  scheduled_for: string | null;
  status: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PracticeDiaryEntry = {
  id: string;
  practice_plan_id: string | null;
  source_insight_id: string | null;
  round_id: string | null;
  entry_date: string;
  title: string;
  body: string;
  category: string | null;
  tags: string[];
  confidence: string | null;
  mood: string | null;
  created_at: string;
  updated_at: string;
};

export type RoundGoal = {
  id: string;
  source_insight_id: string | null;
  practice_plan_id: string | null;
  title: string;
  description: string | null;
  category: string;
  metric_key: string;
  target_operator: string;
  target_value: string | null;
  target_value_max: string | null;
  target_json: Record<string, unknown>;
  applies_to: string;
  due_round_id: string | null;
  due_date: string | null;
  status: string;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type GoalEvaluation = {
  id: string;
  goal_id: string;
  round_id: string | null;
  evaluation_status: string;
  actual_value: string | null;
  actual_json: Record<string, unknown>;
  evaluated_by: string;
  note: string | null;
  evaluated_at: string;
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
      display_name: payload.display_name ?? "GolfRaider",
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

export async function logout(): Promise<void> {
  await apiFetch<ApiEnvelope<{ ok: boolean }>>("/auth/logout", { method: "POST" });
}

export async function getGoogleOAuthStatus(): Promise<{ configured: boolean }> {
  const response = await fetch(`${apiBaseUrl}/auth/google/status`, {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    return { configured: false };
  }
  const data = (await response.json()) as ApiEnvelope<{ configured: boolean }>;
  return data.data;
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

export async function updateUploadReviewRawContent(
  uploadReviewId: string,
  rawContent: string,
): Promise<UploadReview> {
  const response = await apiFetch<ApiEnvelope<UploadReview>>(
    `/uploads/${uploadReviewId}/review/raw`,
    {
      method: "PATCH",
      body: JSON.stringify({ raw_content: rawContent }),
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

export async function getDashboardSummary(locale?: ApiLocale): Promise<DashboardSummary> {
  const query = locale ? `?locale=${locale}` : "";
  const response = await apiFetch<ApiEnvelope<DashboardSummary>>(`/analytics/summary${query}`, {
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

export async function updateShot(
  shotId: string,
  values: Partial<Pick<RoundShot, "raw_text">>,
): Promise<RoundShot> {
  const response = await apiFetch<ApiEnvelope<RoundShot>>(`/shots/${shotId}`, {
    method: "PATCH",
    body: JSON.stringify(values),
  });
  return response.data;
}

export async function getAnalyticsTrends(locale?: ApiLocale): Promise<AnalyticsTrend> {
  const query = locale ? `?locale=${locale}` : "";
  const response = await apiFetch<ApiEnvelope<AnalyticsTrend>>(`/analytics/trends${query}`, {
    method: "GET",
  });
  return response.data;
}

export async function getRoundAnalytics(roundId: string, locale?: ApiLocale): Promise<RoundAnalytics> {
  const query = locale ? `?locale=${locale}` : "";
  const response = await apiFetch<ApiEnvelope<RoundAnalytics>>(
    `/analytics/rounds/${roundId}${query}`,
    { method: "GET" },
  );
  return response.data;
}

export async function getInsights(status = "active", locale?: ApiLocale): Promise<InsightUnit[]> {
  const search = new URLSearchParams({ status });
  if (locale) search.set("locale", locale);
  const response = await apiFetch<ApiEnvelope<InsightUnit[]>>(`/insights?${search.toString()}`, {
    method: "GET",
  });
  return response.data;
}

export async function updateInsightStatus(
  insightId: string,
  status: "active" | "dismissed",
  locale?: ApiLocale,
): Promise<InsightUnit> {
  const query = locale ? `?locale=${locale}` : "";
  const response = await apiFetch<ApiEnvelope<InsightUnit>>(`/insights/${insightId}${query}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  return response.data;
}

export async function getSharedRound(token: string, locale?: ApiLocale): Promise<SharedRound> {
  const query = locale ? `?locale=${locale}` : "";
  const response = await fetch(`${apiBaseUrl}/shared/${token}${query}`, {
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

export async function getChatStatus(): Promise<ChatStatus> {
  const response = await apiFetch<ApiEnvelope<ChatStatus>>("/chat/status", { method: "GET" });
  return response.data;
}

export async function createShare(roundId: string, title?: string): Promise<ShareCreateResponse> {
  const response = await apiFetch<ApiEnvelope<ShareCreateResponse>>("/shares", {
    method: "POST",
    body: JSON.stringify({ round_id: roundId, title }),
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

export async function getPracticePlans(): Promise<PracticePlan[]> {
  const response = await apiFetch<ApiEnvelope<PracticePlan[]>>("/practice/plans", {
    method: "GET",
  });
  return response.data;
}

export async function createPracticePlan(payload: {
  source_insight_id?: string;
  title: string;
  purpose?: string;
  category?: string;
  scheduled_for?: string;
  drill_json?: Record<string, unknown>;
  target_json?: Record<string, unknown>;
}): Promise<PracticePlan> {
  const response = await apiFetch<ApiEnvelope<PracticePlan>>("/practice/plans", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data;
}

export async function updatePracticePlan(
  planId: string,
  payload: { status?: string; title?: string },
): Promise<PracticePlan> {
  const response = await apiFetch<ApiEnvelope<PracticePlan>>(`/practice/plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return response.data;
}

export async function getPracticeDiary(): Promise<PracticeDiaryEntry[]> {
  const response = await apiFetch<ApiEnvelope<PracticeDiaryEntry[]>>("/practice/diary", {
    method: "GET",
  });
  return response.data;
}

export async function createPracticeDiary(payload: {
  practice_plan_id?: string;
  source_insight_id?: string;
  entry_date: string;
  title: string;
  body: string;
  category?: string;
  tags?: string[];
  confidence?: string;
}): Promise<PracticeDiaryEntry> {
  const response = await apiFetch<ApiEnvelope<PracticeDiaryEntry>>("/practice/diary", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data;
}

export async function getGoals(): Promise<RoundGoal[]> {
  const response = await apiFetch<ApiEnvelope<RoundGoal[]>>("/goals", { method: "GET" });
  return response.data;
}

export async function createGoal(payload: {
  source_insight_id?: string;
  practice_plan_id?: string;
  title: string;
  description?: string;
  category?: string;
  metric_key: string;
  target_operator: string;
  target_value?: number;
  applies_to?: string;
  due_date?: string;
}): Promise<RoundGoal> {
  const response = await apiFetch<ApiEnvelope<RoundGoal>>("/goals", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return response.data;
}

export async function evaluateGoal(goalId: string, roundId?: string): Promise<GoalEvaluation> {
  const response = await apiFetch<ApiEnvelope<GoalEvaluation>>(`/goals/${goalId}/evaluate`, {
    method: "POST",
    body: JSON.stringify({ round_id: roundId ?? null }),
  });
  return response.data;
}

export async function manuallyEvaluateGoal(
  goalId: string,
  payload: { evaluation_status: string; note?: string },
): Promise<GoalEvaluation> {
  const response = await apiFetch<ApiEnvelope<GoalEvaluation>>(
    `/goals/${goalId}/manual-evaluation`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
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
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail
        .map((item: unknown) => {
          if (typeof item === "object" && item !== null && "msg" in item) {
            const message = (item as { msg?: unknown }).msg;
            if (typeof message === "string") return message;
          }
          if (typeof item === "string") return item;
          return JSON.stringify(item);
        })
        .join(", ");
    }
    return payload.error?.message ?? fallback;
  } catch {
    return fallback;
  }
}
