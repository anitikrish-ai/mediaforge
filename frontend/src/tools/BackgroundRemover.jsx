import { useEffect, useState } from "react";
import { GlassButton, GlassSwitch } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import Dropzone from "../components/Dropzone";
import { getJSON, postForm } from "../api";

/** AI background removal via rembg — several bundled, fully-local ONNX models. */
export default function BackgroundRemover() {
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("u2net");
  const [alphaMatting, setAlphaMatting] = useState(false);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    getJSON("/api/background/models").then((r) => setModels(r.models)).catch(() => {});
  }, []);

  function onFiles(files) {
    const f = files[0];
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResultUrl(null);
    setError(null);
  }

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("model", model);
      fd.append("alpha_matting", alphaMatting);
      const blob = await postForm("/api/background/remove", fd);
      setResultUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Background Remover" subtitle="Local AI segmentation via rembg — no cloud calls">
      {!file && <Dropzone accept="image/*" onFiles={onFiles} hint="Works best on clear subject/background photos" />}
      {file && (
        <div className="studio-grid">
          <div className="studio-preview">
            <div className="preview-pair">
              <figure>
                <figcaption>Original</figcaption>
                <img src={previewUrl} alt="original" />
              </figure>
              <figure className="checker-bg">
                <figcaption>Cut-out</figcaption>
                {resultUrl ? <img src={resultUrl} alt="result" /> : <div className="preview-empty">Run to preview</div>}
              </figure>
            </div>
            <div className="row-actions">
              <GlassButton variant="glass" onClick={() => { setFile(null); setResultUrl(null); }}>
                Change file
              </GlassButton>
              {resultUrl && (
                <a className="glass-link-btn" href={resultUrl} download="no-background.png">
                  Download PNG
                </a>
              )}
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>
          <div className="studio-controls">
            <label className="field">
              <span>Model</span>
              <div className="pill-list">
                {models.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    className={`pill ${model === m.id ? "pill--active" : ""}`}
                    onClick={() => setModel(m.id)}
                  >
                    {m.id}
                  </button>
                ))}
              </div>
              <small>{models.find((m) => m.id === model)?.description}</small>
            </label>
            <label className="field toggle-field">
              <span>Alpha matting (finer edges, slower)</span>
              <GlassSwitch checked={alphaMatting} onChange={setAlphaMatting} />
            </label>
            <GlassButton variant="filled" onClick={run} disabled={busy}>
              {busy ? "Removing background…" : "Remove Background"}
            </GlassButton>
          </div>
        </div>
      )}
    </Panel>
  );
}
