import { useState } from "react";
import { GlassButton } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import Dropzone from "../components/Dropzone";
import ProgressBar from "../components/ProgressBar";
import PillField from "../components/PillField";
import { apiUrl, postForm, waitForJob } from "../api";

const PRESETS = {
  grayscale: [{ type: "filter", name: "grayscale" }],
  sharpen: [{ type: "sharpen", amount: 1.5 }],
  enhance: [{ type: "auto_contrast" }, { type: "sharpen", amount: 1.0 }],
  "remove-bg": null, // handled by the background-removal batch endpoint
};

/** Batch processing across many files at once — image pipeline or background removal. */
export default function BatchProcessor() {
  const [files, setFiles] = useState([]);
  const [preset, setPreset] = useState("enhance");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  function onFiles(fileList) {
    setFiles(fileList);
    setResult(null);
    setError(null);
  }

  async function run() {
    if (!files.length) return;
    setBusy(true);
    setError(null);
    setProgress(null);
    setResult(null);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      let jobRes;
      if (preset === "remove-bg") {
        fd.append("model", "u2net");
        jobRes = await postForm("/api/background/batch", fd);
      } else {
        fd.append("ops", JSON.stringify(PRESETS[preset]));
        fd.append("format", "PNG");
        jobRes = await postForm("/api/images/batch", fd);
      }
      const res = await waitForJob(jobRes.job_id, setProgress);
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const downloadBase = preset === "remove-bg" ? "/api/background/batch" : "/api/images/batch";

  return (
    <Panel title="Batch Processor" subtitle="Apply one operation across many files at once, with live progress">
      {!files.length && (
        <Dropzone accept="image/*" multiple onFiles={onFiles} hint={`Up to 20 images per batch`} />
      )}
      {!!files.length && (
        <div className="studio-controls">
          <div className="meta-row">{files.length} file(s) selected</div>
          <label className="field">
            <span>Operation preset</span>
            <PillField
              options={Object.keys(PRESETS)}
              value={preset}
              onChange={setPreset}
            />
          </label>

          {busy && progress && <ProgressBar progress={progress.progress} message={progress.message} />}

          <div className="row-actions">
            <GlassButton variant="glass" onClick={() => { setFiles([]); setResult(null); }}>
              Change files
            </GlassButton>
            <GlassButton variant="filled" onClick={run} disabled={busy}>
              {busy ? "Processing…" : `Process ${files.length} files`}
            </GlassButton>
          </div>

          {error && <div className="error-box">{error}</div>}

          {result && (
            <ul className="batch-list">
              {result.files.map((f, i) => (
                <li key={i} className={f.ok ? "ok" : "fail"}>
                  <span>{f.filename}</span>
                  {f.ok ? (
                    <a href={apiUrl(`${downloadBase}/${result.dir.split("/").pop()}/download/${f.output}`)} download>
                      Download
                    </a>
                  ) : (
                    <span className="err">{f.error}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Panel>
  );
}
