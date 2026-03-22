export type ScrapedSignals = {
  company_name: string | null;
  description: string | null;
  industry: string | null;
  location: string | null;
  emails: string[];
  phones: string[];
  social_urls: Record<string, string>;
  funding_or_size_hint: string | null;
  source_url: string;
  scraped_at: string;
  coverage_score: number;
  extraction_method: "heuristic" | "llm" | "hybrid";
};

export type PreviewResponse = {
  signals: ScrapedSignals;
  robots_allowed: boolean;
  robots_message: string | null;
  llm_used: boolean;
};

export type PushResponse = PreviewResponse & {
  notion_page_id: string | null;
  notion_url: string | null;
};

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(text || res.statusText || "Invalid JSON");
  }
}

export async function preview(body: {
  url: string;
  company_hint?: string | null;
  use_llm: boolean;
  coverage_threshold: number;
}): Promise<PreviewResponse> {
  const res = await fetch("/api/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: string }).detail ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return parseJson<PreviewResponse>(res);
}

export async function push(body: {
  url: string;
  company_hint?: string | null;
  use_llm: boolean;
  coverage_threshold: number;
}): Promise<PushResponse> {
  const res = await fetch("/api/push", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = (err as { detail?: string }).detail ?? res.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return parseJson<PushResponse>(res);
}
