import { useMemo, useState } from "react";
import type { PreviewResponse, ScrapedSignals } from "./api";
import { preview, push } from "./api";

function formatSignals(s: ScrapedSignals): { label: string; value: string }[] {
  const rows: { label: string; value: string }[] = [
    { label: "Company", value: s.company_name ?? "—" },
    { label: "Description", value: s.description ?? "—" },
    { label: "Industry", value: s.industry ?? "—" },
    { label: "Location", value: s.location ?? "—" },
    { label: "Emails", value: s.emails.length ? s.emails.join(", ") : "—" },
    { label: "Phones", value: s.phones.length ? s.phones.join(", ") : "—" },
    {
      label: "Social",
      value: Object.keys(s.social_urls).length
        ? Object.entries(s.social_urls)
            .map(([k, v]) => `${k}: ${v}`)
            .join("\n")
        : "—",
    },
    { label: "Funding / size hint", value: s.funding_or_size_hint ?? "—" },
    { label: "Source URL", value: s.source_url || "—" },
    { label: "Coverage score", value: s.coverage_score.toFixed(3) },
    { label: "Method", value: s.extraction_method },
    { label: "Scraped at", value: new Date(s.scraped_at).toLocaleString() },
  ];
  return rows;
}

export default function App() {
  const [url, setUrl] = useState("");
  const [companyHint, setCompanyHint] = useState("");
  const [useLlm, setUseLlm] = useState(false);
  const [threshold, setThreshold] = useState(0.35);
  const [loading, setLoading] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<PreviewResponse | null>(null);
  const [pushNote, setPushNote] = useState<string | null>(null);

  const rows = useMemo(
    () => (previewData ? formatSignals(previewData.signals) : []),
    [previewData]
  );

  async function onPreview() {
    setError(null);
    setPushNote(null);
    setLoading(true);
    setPreviewData(null);
    try {
      const data = await preview({
        url: url.trim(),
        company_hint: companyHint.trim() || null,
        use_llm: useLlm,
        coverage_threshold: threshold,
      });
      setPreviewData(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function onPush() {
    setError(null);
    setPushNote(null);
    setPushing(true);
    try {
      const data = await push({
        url: url.trim(),
        company_hint: companyHint.trim() || null,
        use_llm: useLlm,
        coverage_threshold: threshold,
      });
      setPreviewData(data);
      if (data.notion_url) {
        setPushNote(`Created in Notion: ${data.notion_url}`);
      } else if (!data.robots_allowed) {
        setPushNote("Not pushed — robots.txt disallows this URL.");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPushing(false);
    }
  }

  return (
    <div className="app">
      <h1>CRM Signals</h1>
      <p className="sub">
        Paste a company website URL, run extraction, preview signals, then send the row to Notion.
      </p>

      <div className="card">
        <div className="row">
          <div>
            <label htmlFor="url">Website URL</label>
            <input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              autoComplete="url"
            />
          </div>
          <div>
            <label htmlFor="hint">Company hint (optional)</label>
            <input
              id="hint"
              type="text"
              placeholder="Override detected name"
              value={companyHint}
              onChange={(e) => setCompanyHint(e.target.value)}
            />
          </div>
        </div>
        <div className="row" style={{ marginTop: "0.75rem" }}>
          <div>
            <label htmlFor="thr">Coverage threshold (0–1)</label>
            <input
              id="thr"
              type="text"
              inputMode="decimal"
              value={String(threshold)}
              onChange={(e) => setThreshold(Number(e.target.value) || 0)}
            />
          </div>
          <div className="checkbox" style={{ paddingBottom: "0.35rem" }}>
            <input
              id="llm"
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            <label htmlFor="llm" style={{ margin: 0, fontWeight: 500 }}>
              Use LLM (needs OPENAI_API_KEY in backend .env)
            </label>
          </div>
        </div>
        <div className="actions">
          <button
            type="button"
            className="primary"
            disabled={loading || !url.trim()}
            onClick={() => void onPreview()}
          >
            {loading ? "Running…" : "Run preview"}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={pushing || !url.trim() || loading}
            onClick={() => void onPush()}
          >
            {pushing ? "Sending…" : "Send to Notion"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="alert err" role="alert">
          {error}
        </div>
      ) : null}

      {previewData && !previewData.robots_allowed ? (
        <div className="alert warn" role="status">
          {previewData.robots_message ?? "This URL is blocked by robots.txt."}
        </div>
      ) : null}

      {pushNote ? (
        <div className="alert warn" role="status" style={{ background: "#ecfdf5", borderColor: "#6ee7b7", color: "#065f46" }}>
          {pushNote}
        </div>
      ) : null}

      {previewData && previewData.robots_allowed ? (
        <div className="card">
          <h2 style={{ fontSize: "1.1rem", margin: "0 0 0.75rem" }}>Signals</h2>
          <table>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label}>
                  <th scope="row">{r.label}</th>
                  <td style={{ whiteSpace: "pre-wrap" }}>{r.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="meta">
            LLM used: {previewData.llm_used ? "yes" : "no"}
          </p>
        </div>
      ) : null}
    </div>
  );
}
