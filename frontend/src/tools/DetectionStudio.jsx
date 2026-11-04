import { useState } from "react";
import { GlassButton, GlassSwitch } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import Dropzone from "../components/Dropzone";
import ProgressBar from "../components/ProgressBar";
import SegmentedField from "../components/SegmentedField";
import { postForm, waitForJob } from "../api";

const IMAGE_MODES = ["people", "face", "eye"];
const VIDEO_MODES = ["motion", "people", "face"];

/** Object detection (OpenCV) + bounding-box / trace annotation and tracking (supervision). */
export default function DetectionStudio() {
  const [kind, setKind] = useState("image"); // image | video
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [mode, setMode] = useState("people");
  const [track, setTrack] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  function onFiles(files) {
    const f = files[0];
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResult(null);
    setError(null);
    setKind(f.type.startsWith("video") ? "video" : "image");
    setMode(f.type.startsWith("video") ? "motion" : "people");
  }

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("mode", mode);
      if (kind === "image") {
        const r = await postForm("/api/detect/image", fd);
        setResult({ type: "image", ...r });
      } else {
        fd.append("track", track);
        const r = await postForm("/api/detect/video", fd);
        const res = await waitForJob(r.job_id, setProgress);
        setResult({ type: "video", ...res });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const modes = kind === "image" ? IMAGE_MODES : VIDEO_MODES;

  return (
    <Panel title="Detection & Tracking" subtitle="OpenCV detectors annotated and tracked with supervision (ByteTrack)">
      {!file && (
        <Dropzone
          accept="image/*,video/*"
          onFiles={onFiles}
          hint="Images: instant detection. Videos: frame-by-frame tracking as a background job."
        />
      )}
      {file && (
        <div className="studio-grid">
          <div className="studio-preview">
            {kind === "image" ? (
              <div className="preview-pair">
                <figure>
                  <figcaption>Original</figcaption>
                  <img src={previewUrl} alt="original" />
                </figure>
                <figure>
                  <figcaption>Annotated ({result?.count ?? 0} found)</figcaption>
                  {result?.image_url ? (
                    <img src={result.image_url} alt="annotated" />
                  ) : (
                    <div className="preview-empty">Run to preview</div>
                  )}
                </figure>
              </div>
            ) : (
              <div className="preview-pair">
                <figure>
                  <figcaption>Original</figcaption>
                  <video src={previewUrl} controls />
                </figure>
                <figure>
                  <figcaption>Tracked{result ? ` — ${result.unique_tracks} unique tracks` : ""}</figcaption>
                  {result?.download_url ? (
                    <video src={result.download_url} controls />
                  ) : (
                    <div className="preview-empty">Run to process</div>
                  )}
                </figure>
              </div>
            )}

            {busy && progress && <ProgressBar progress={progress.progress} message={progress.message} />}

            <div className="row-actions">
              <GlassButton variant="glass" onClick={() => { setFile(null); setResult(null); }}>
                Change file
              </GlassButton>
              {result?.download_url && (
                <a className="glass-link-btn" href={result.download_url} download>
                  Download video
                </a>
              )}
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>

          <div className="studio-controls">
            <label className="field">
              <span>Detection mode</span>
              <SegmentedField options={modes} value={mode} onChange={setMode} />
            </label>
            {kind === "video" && (
              <label className="field toggle-field">
                <span>Track objects across frames (ByteTrack)</span>
                <GlassSwitch checked={track} onChange={setTrack} />
              </label>
            )}
            <GlassButton variant="filled" onClick={run} disabled={busy}>
              {busy ? "Processing…" : "Run Detection"}
            </GlassButton>
          </div>
        </div>
      )}
    </Panel>
  );
}
