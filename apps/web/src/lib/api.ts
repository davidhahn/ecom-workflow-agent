import type { components } from "shared";

export type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];
export type RefundEvaluateResponse = components["schemas"]["RefundEvaluateResponse"];
export type RequestLogRow = components["schemas"]["RequestLogRow"];

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${path} failed (${res.status}): ${detail}`);
  }
  return res.json() as Promise<T>;
}

export function analyzeQuestion(question: string): Promise<AnalyzeResponse> {
  return postJson<AnalyzeResponse>("/query/analyze", { question });
}

export function evaluateRefund(requestText: string): Promise<RefundEvaluateResponse> {
  return postJson<RefundEvaluateResponse>("/refund/evaluate", { request_text: requestText });
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
