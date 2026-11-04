import { useState } from "react";
import { GlassButton, GlassInput, GlassSwitch } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import { postForm } from "../api";

/** Clean article extraction from any URL via trafilatura. */
export default function WebExtractor() {
  const [url, setUrl] = useState("");
  const [includeLinks, setIncludeLinks] = useState(false);
  const [busy, setBusy] = useState(false);
  const [article, setArticle] = useState(null);
  const [error, setError] = useState(null);

  async function run() {
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    setArticle(null);
    try {
      const fd = new FormData();
      fd.append("url", url.trim());
      fd.append("include_links", includeLinks);
      const r = await postForm("/api/extract/article", fd);
      setArticle(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function download() {
    if (!article) return;
    const blob = new Blob([article.text], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `${(article.title || "article").slice(0, 60)}.txt`;
    a.click();
  }

  return (
    <Panel title="Web Extractor" subtitle="Clean article text & metadata from any URL — trafilatura">
      <div className="url-row">
        <GlassInput
          type="search"
          placeholder="https://example.com/article"
          value={url}
          onChange={(e) => setUrl(e.target?.value ?? e)}
        />
        <GlassButton variant="filled" onClick={run} disabled={busy}>
          {busy ? "Extracting…" : "Extract"}
        </GlassButton>
      </div>
      <label className="field toggle-field inline">
        <span>Include links</span>
        <GlassSwitch checked={includeLinks} onChange={setIncludeLinks} />
      </label>

      {error && <div className="error-box">{error}</div>}

      {article && (
        <div className="article-result">
          <h3>{article.title || "Untitled"}</h3>
          <div className="article-meta">
            {article.sitename && <span>{article.sitename}</span>}
            {article.author && <span>by {article.author}</span>}
            {article.date && <span>{article.date}</span>}
            <span>{article.word_count} words · {article.reading_time_min} min read</span>
          </div>
          <div className="article-text">{article.text}</div>
          <div className="row-actions">
            <GlassButton variant="glass" onClick={download}>
              Download as .txt
            </GlassButton>
          </div>
        </div>
      )}
    </Panel>
  );
}
