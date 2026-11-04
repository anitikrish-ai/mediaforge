import { useState } from "react";
import { GlassButton, GlassSlider } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import Dropzone from "../components/Dropzone";
import ProgressBar from "../components/ProgressBar";
import SegmentedField from "../components/SegmentedField";
import { apiUrl, postForm, waitForJob } from "../api";

/** Video processing: probe, trim, resize, and frame extraction — all OpenCV-backed. */
export default function VideoStudio() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [info, setInfo] = useState(null);
  const [op, setOp] = useState("trim");
  const [start, setStart] = useState(0);
  const [end, setEnd] = useState(5);
  const [width, setWidth] = useState(1280);
  const [height, setHeight] = useState(720);
  const [everyN, setEveryN] = useState(30);
  const [maxFrames, setMaxFrames] = useState(30);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function onFiles(files) {
    const f = files[0];
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResult(null);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const probeInfo = await postForm("/api/video/probe", fd);
      setInfo(probeInfo);
      setEnd(Math.min(5, probeInfo.duration_sec || 5));
    } catch (e) {
      setError(e.message);
    }
  }

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      let endpoint;
      if (op === "trim") {
        fd.append("start_sec", start);
        fd.append("end_sec", end);
        endpoint = "/api/video/trim";
      } else if (op === "resize") {
        fd.append("width", width);
        fd.append("height", height);
        endpoint = "/api/video/resize";
      } else {
        fd.append("every_n", everyN);
        fd.append("max_frames", maxFrames);
        endpoint = "/api/video/extract-frames";
      }
      const { job_id } = await postForm(endpoint, fd);
      const res = await waitForJob(job_id, setProgress);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Video Studio" subtitle="Trim, resize & extract frames with OpenCV — runs as a background job">
      {!file && <Dropzone accept="video/*" onFiles={onFiles} hint="MP4, MOV, AVI, MKV, WEBM up to 500MB" />}
      {file && (
        <div className="studio-grid">
          <div className="studio-preview">
            <video src={previewUrl} controls />
            {info && (
              <div className="meta-row">
                {info.width}×{info.height} · {info.fps.toFixed(1)}fps · {info.duration_sec.toFixed(1)}s
              </div>
            )}
            {busy && progress && <ProgressBar progress={progress.progress} message={progress.message} />}

            {result && op !== "extract" && result.download_url && (
              <video src={apiUrl(result.download_url)} controls className="result-video" />
            )}
            {result && op === "extract" && (
              <div className="frame-grid">
                {result.frame_urls.map((u) => (
                  <img key={u} src={apiUrl(u)} alt="frame" />
                ))}
              </div>
            )}

            <div className="row-actions">
              <GlassButton variant="glass" onClick={() => { setFile(null); setResult(null); setInfo(null); }}>
                Change file
              </GlassButton>
              {result?.download_url && (
                <a className="glass-link-btn" href={apiUrl(result.download_url)} download>
                  Download
                </a>
              )}
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>

          <div className="studio-controls">
            <label className="field">
              <span>Operation</span>
              <SegmentedField options={["trim", "resize", "extract"]} value={op} onChange={setOp} />
            </label>

            {op === "trim" && (
              <>
                <label className="field">
                  <span>Start (sec)</span>
                  <GlassSlider value={start} onChange={setStart} min={0} max={info?.duration_sec || 60} />
                  <small>{start.toFixed(1)}s</small>
                </label>
                <label className="field">
                  <span>End (sec)</span>
                  <GlassSlider value={end} onChange={setEnd} min={0} max={info?.duration_sec || 60} />
                  <small>{end.toFixed(1)}s</small>
                </label>
              </>
            )}

            {op === "resize" && (
              <>
                <label className="field">
                  <span>Width</span>
                  <GlassSlider value={width} onChange={setWidth} min={64} max={3840} />
                  <small>{width}px</small>
                </label>
                <label className="field">
                  <span>Height</span>
                  <GlassSlider value={height} onChange={setHeight} min={64} max={2160} />
                  <small>{height}px</small>
                </label>
              </>
            )}

            {op === "extract" && (
              <>
                <label className="field">
                  <span>Every N frames</span>
                  <GlassSlider value={everyN} onChange={setEveryN} min={1} max={120} />
                  <small>{everyN}</small>
                </label>
                <label className="field">
                  <span>Max frames</span>
                  <GlassSlider value={maxFrames} onChange={setMaxFrames} min={1} max={200} />
                  <small>{maxFrames}</small>
                </label>
              </>
            )}

            <GlassButton variant="filled" onClick={run} disabled={busy}>
              {busy ? "Processing…" : "Run"}
            </GlassButton>
          </div>
        </div>
      )}
    </Panel>
  );
}
