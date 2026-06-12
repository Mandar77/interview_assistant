/**
 * CultureScraper — crawl public culture pages to ground question generation.
 * Location: frontend/src/pages/employer/CultureScraper.tsx
 */

import { useEffect, useState } from "react";
import { Globe, Sparkles } from "lucide-react";
import { cultureApi } from "../../api/platform";
import AppShell from "../../ui/AppShell";
import { Badge, Button, Card, Input } from "../../ui";
import { EMPLOYER_NAV } from "./nav";

export default function CultureScraper() {
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [summary, setSummary] = useState<any | null>(null);

  useEffect(() => {
    cultureApi.summary().then(setSummary).catch(() => {});
  }, []);

  const crawl = async () => {
    if (!url.trim()) return;
    setBusy(true);
    setResult(null);
    try {
      setResult(await cultureApi.crawl(url.trim()));
      setSummary(await cultureApi.summary());
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Crawl failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AppShell nav={EMPLOYER_NAV} title="Culture Scraper" maxWidth="max-w-3xl">
      <div className="mb-6 flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-[var(--radius-md)] bg-[var(--accent-soft)] text-[var(--accent)]">
          <Sparkles size={18} />
        </div>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--text)]">Culture Scraper</h1>
          <p className="text-sm text-[var(--text-muted)]">Ground question generation in your company's values.</p>
        </div>
      </div>

      <Card elevated>
        <div className="px-6 py-5">
          <p className="mb-4 text-sm leading-relaxed text-[var(--text-secondary)]">
            Crawl your company's <strong className="text-[var(--text)]">public</strong> culture pages — about,
            values, careers, blog. The extracted text grounds generated questions so interviews align with
            your tone and principles. Respects <code className="rounded bg-[var(--surface-3)] px-1 py-0.5 text-xs">robots.txt</code>.
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && crawl()}
              placeholder="https://yourcompany.com"
              className="flex-1"
            />
            <Button onClick={crawl} loading={busy} leftIcon={<Globe size={16} />}>
              Crawl
            </Button>
          </div>

          {result && (
            <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--success-soft)] px-4 py-3 text-sm text-[var(--success)]">
              Indexed {result.chunks_indexed} chunks from {result.sources_crawled.length} page(s).{" "}
              {result.embedded ? "Semantic embeddings built." : "Keyword index (embeddings offline)."}
            </div>
          )}

          {summary && summary.chunk_count > 0 && (
            <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-2)] px-4 py-3">
              <div className="mb-1.5 flex items-center gap-2">
                <Badge tone="accent">{summary.chunk_count} chunks indexed</Badge>
                {summary.embedded && <Badge tone="success">embedded</Badge>}
              </div>
              <p className="line-clamp-3 text-xs leading-relaxed text-[var(--text-muted)]">{summary.preview}</p>
            </div>
          )}
        </div>
      </Card>
    </AppShell>
  );
}
