/**
 * CultureScraper - crawl public culture pages to ground question gen (Phase 12).
 * Location: frontend/src/pages/employer/CultureScraper.tsx
 */

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cultureApi } from "../../api/platform";

export default function CultureScraper() {
  const navigate = useNavigate();
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
      const res = await cultureApi.crawl(url.trim());
      setResult(res);
      setSummary(await cultureApi.summary());
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Crawl failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <button onClick={() => navigate("/employer")} className="text-gray-500">← Back</button>
          <h1 className="text-lg font-bold text-gray-900">Culture Scraper</h1>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8 max-w-2xl">
        <div className="bg-white rounded-xl shadow p-6">
          <p className="text-sm text-gray-600 mb-4">
            Crawl your company's <strong>public</strong> culture pages (about, values, careers,
            blog). The extracted text grounds question generation so interviews align with your
            company's tone and principles. Respects robots.txt.
          </p>
          <div className="flex gap-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://yourcompany.com"
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg"
            />
            <button onClick={crawl} disabled={busy} className="px-6 py-2.5 bg-purple-600 text-white font-semibold rounded-lg disabled:opacity-50">
              {busy ? "Crawling…" : "Crawl"}
            </button>
          </div>

          {result && (
            <div className="mt-4 p-4 bg-green-50 rounded-lg text-sm text-green-800">
              Indexed {result.chunks_indexed} text chunks from {result.sources_crawled.length} page(s).
              {result.embedded ? " Semantic embeddings built." : " (Keyword index — embeddings offline.)"}
            </div>
          )}

          {summary && summary.chunk_count > 0 && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
              <p className="font-semibold mb-1">Currently indexed: {summary.chunk_count} chunks</p>
              <p className="text-xs text-gray-500 line-clamp-3">{summary.preview}</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
