import { useState } from "react";
import { GlassButton, GlassInput } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import ProgressBar from "../components/ProgressBar";
import SegmentedField from "../components/SegmentedField";
import { apiUrl, postForm, waitForJob } from "../api";

/** Video/audio downloading with format & quality selection via yt-dlp. */
export default function MediaDownloader() {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState("video");
  const [quality, setQuality] = useState("best");
  const [audioFormat, setAudioFormat] = useState("mp3");
  const [probeInfo, setProbeInfo] = useState(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function probe() {
    if (!url.trim()) return;
    setBusy(true);
    setError(null);
    setProbeInfo(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("url", url.trim());
      const r = await postForm("/api/download/probe", fd);
      setProbeInfo(r);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function startDownload() {
    setBusy(true);
    setError(null);
    setProgress(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("url", url.trim());
      fd.append("mode", mode);
      fd.append("quality", quality);
      fd.append("audio_format", audioFormat);
      const { job_id } = await postForm("/api/download/start", fd);
      const res = await waitForJob(job_id, setProgress);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const resolutions = Array.from(
    new Set(
      (probeInfo?.formats || [])
        .map((f) => f.resolution?.split("x")[1])
        .filter(Boolean)
    )
  ).sort((a, b) => Number(b) - Number(a));

  return (
    <Panel title="Media Downloader" subtitle="Download video/audio with quality selection — yt-dlp, 1000+ sites">
      <div className="url-row">
        <GlassInput
          type="search"
          placeholder="Paste a video URL…"
          value={url}
          onChange={(e) => setUrl(e.target?.value ?? e)}
        />
        <GlassButton variant="glass" onClick={probe} disabled={busy}>
          Check
        </GlassButton>
      </div>

      {error && <div className="error-box">{error}</div>}

      {probeInfo && (
        <div className="probe-result">
          {probeInfo.thumbnail && <img className="thumb" src={probeInfo.thumbnail} alt="" />}
          <div>
            <strong>{probeInfo.title}</strong>
            <div className="meta-row">
              {probeInfo.uploader} · {probeInfo.duration ? `${Math.round(probeInfo.duration)}s` : ""}
            </div>
          </div>
        </div>
      )}

      <div className="studio-controls">
        <label className="field">
          <span>Mode</span>
          <SegmentedField options={["video", "audio"]} value={mode} onChange={setMode} />
        </label>
        {mode === "video" ? (
          <label className="field">
            <span>Quality</span>
            <div className="pill-list">
              {["best", ...resolutions, "worst"].map((q) => (
                <button
                  key={q}
                  type="button"
                  className={`pill ${quality === q ? "pill--active" : ""}`}
                  onClick={() => setQuality(q)}
                >
                  {q === "best" || q === "worst" ? q : `${q}p`}
                </button>
              ))}
            </div>
          </label>
        ) : (
          <label className="field">
            <span>Audio format</span>
            <SegmentedField options={["mp3", "m4a", "wav", "opus"]} value={audioFormat} onChange={setAudioFormat} />
          </label>
        )}

        {busy && progress && <ProgressBar progress={progress.progress} message={progress.message} />}

        <GlassButton variant="filled" onClick={startDownload} disabled={busy || !url.trim()}>
          {busy ? "Downloading…" : "Download"}
        </GlassButton>

        {result?.download_url && (
          <a className="glass-link-btn" href={apiUrl(result.download_url)} download>
            Save {result.title ? `"${result.title}"` : "file"}
          </a>
        )}
      </div>
    </Panel>
  );
}
