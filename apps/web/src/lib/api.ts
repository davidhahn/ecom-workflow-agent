import type { components } from "shared";

export type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];
export type RefundEvaluateResponse = components["schemas"]["RefundEvaluateResponse"];
export type RequestLogRow = components["schemas"]["RequestLogRow"];

export type RateLimitInfo = {
  limit: number | null;
  remaining: number | null;
};

export class RateLimitedError extends Error {
  retryAfterSeconds: number | null;

  constructor(message: string, retryAfterSeconds: number | null) {
    super(message);
    this.name = "RateLimitedError";
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

function readRateLimit(headers: Headers): RateLimitInfo {
  const limit = headers.get("X-RateLimit-Limit");
  const remaining = headers.get("X-RateLimit-Remaining");
  return {
    limit: limit !== null ? Number(limit) : null,
    remaining: remaining !== null ? Number(remaining) : null,
  };
}

async function postJson<T>(path: string, body: unknown): Promise<{ data: T; rateLimit: RateLimitInfo }> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (res.status === 429) {
    const detail = (await res.json()) as { message?: string; retry_after_seconds?: number | null };
    throw new RateLimitedError(
      detail.message ?? "Rate limit exceeded.",
      detail.retry_after_seconds ?? null
    );
  }
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${path} failed (${res.status}): ${detail}`);
  }

  const data = (await res.json()) as T;
  return { data, rateLimit: readRateLimit(res.headers) };
}

export function analyzeQuestion(
  question: string
): Promise<{ data: AnalyzeResponse; rateLimit: RateLimitInfo }> {
  return postJson<AnalyzeResponse>("/query/analyze", { question });
}

export function evaluateRefund(
  requestText: string
): Promise<{ data: RefundEvaluateResponse; rateLimit: RateLimitInfo }> {
  return postJson<RefundEvaluateResponse>("/refund/evaluate", { request_text: requestText });
}

export function formatRetryAfter(seconds: number | null): string {
  if (seconds === null) return "Please try again later.";
  if (seconds < 60) return `Try again in ${seconds} second${seconds === 1 ? "" : "s"}.`;
  const minutes = Math.ceil(seconds / 60);
  return `Try again in ${minutes} minute${minutes === 1 ? "" : "s"}.`;
}

export async function listRequestLogs(): Promise<RequestLogRow[]> {
  const res = await fetch("/api/observability/requests");
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`/observability/requests failed (${res.status}): ${detail}`);
  }
  const data = (await res.json()) as components["schemas"]["RequestLogListResponse"];
  return data.requests;
}
