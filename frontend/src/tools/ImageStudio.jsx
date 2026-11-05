import { useMemo, useState } from "react";
import { GlassButton, GlassSlider, GlassSwitch } from "@zakisheriff/liquid-glass";
import Panel from "../components/Panel";
import Dropzone from "../components/Dropzone";
import PillField from "../components/PillField";
import { postForm } from "../api";

const FILTERS = ["none", "grayscale", "blur", "edge", "sepia", "sketch", "emboss"];
const FORMATS = ["PNG", "JPEG", "WEBP"];

/** Image manipulation (Pillow) + enhancement (scikit-image / OpenCV) in one pipeline editor. */
export default function ImageStudio() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [resultUrl, setResultUrl] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [width, setWidth] = useState(0);
  const [resizeMode, setResizeMode] = useState("fit");
  const [rotateDeg, setRotateDeg] = useState(0);
  const [autoContrast, setAutoContrast] = useState(false);
  const [sharpen, setSharpen] = useState(0);
  const [denoise, setDenoise] = useState(0);
  const [brightness, setBrightness] = useState(0);
  const [contrast, setContrast] = useState(0);
  const [filter, setFilter] = useState("none");
  const [format, setFormat] = useState("PNG");

  function onFiles(files) {
    const f = files[0];
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setResultUrl(null);
    setError(null);
  }

  const ops = useMemo(() => {
    const list = [];
    if (width > 0) list.push({ type: "resize", width, mode: resizeMode });
    if (rotateDeg !== 0) list.push({ type: "rotate", degrees: rotateDeg });
    if (autoContrast) list.push({ type: "auto_contrast" });
    if (sharpen > 0) list.push({ type: "sharpen", amount: sharpen });
    if (denoise > 0) list.push({ type: "denoise", strength: denoise });
    if (brightness !== 0 || contrast !== 0) list.push({ type: "brightness_contrast", brightness, contrast });
    if (filter !== "none") list.push({ type: "filter", name: filter });
    return list;
  }, [width, resizeMode, rotateDeg, autoContrast, sharpen, denoise, brightness, contrast, filter]);

  async function run() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("ops", JSON.stringify(ops));
      fd.append("format", format);
      const blob = await postForm("/api/images/process", fd);
      setResultUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title="Image Studio" subtitle="Resize, crop, rotate, filter, denoise & sharpen — Pillow + scikit-image + OpenCV">
      {!file && <Dropzone accept="image/*" onFiles={onFiles} hint="JPG, PNG, WEBP, BMP, TIFF up to 25MB" />}

      {file && (
        <div className="studio-grid">
          <div className="studio-preview">
            <div className="preview-pair">
              <figure>
                <figcaption>Original</figcaption>
                <img src={previewUrl} alt="original" />
              </figure>
              <figure>
                <figcaption>Result</figcaption>
                {resultUrl ? <img src={resultUrl} alt="result" /> : <div className="preview-empty">Run to preview</div>}
              </figure>
            </div>
            <div className="row-actions">
              <GlassButton variant="glass" onClick={() => { setFile(null); setResultUrl(null); }}>
                Change file
              </GlassButton>
              {resultUrl && (
                <a className="glass-link-btn" href={resultUrl} download={`edited.${format.toLowerCase()}`}>
                  Download
                </a>
              )}
            </div>
            {error && <div className="error-box">{error}</div>}
          </div>

          <div className="studio-controls">
            <label className="field">
              <span>Resize width (px)</span>
              <GlassSlider value={width} onChange={setWidth} min={0} max={2000} aria-label="Width" />
              <small>{width || "unchanged"}</small>
            </label>
            <label className="field">
              <span>Resize mode</span>
              <PillField options={["fit", "fill", "stretch"]} value={resizeMode} onChange={setResizeMode} />
            </label>
            <label className="field">
              <span>Rotate (°)</span>
              <GlassSlider value={rotateDeg} onChange={setRotateDeg} min={-180} max={180} aria-label="Rotate" />
              <small>{rotateDeg}°</small>
            </label>
            <label className="field toggle-field">
              <span>Auto contrast (CLAHE)</span>
              <GlassSwitch checked={autoContrast} onChange={setAutoContrast} />
            </label>
            <label className="field">
              <span>Sharpen</span>
              <GlassSlider value={sharpen * 10} onChange={(v) => setSharpen(v / 10)} min={0} max={30} aria-label="Sharpen" />
            </label>
            <label className="field">
              <span>Denoise</span>
              <GlassSlider value={denoise * 10} onChange={(v) => setDenoise(v / 10)} min={0} max={20} aria-label="Denoise" />
            </label>
            <label className="field">
              <span>Brightness</span>
              <GlassSlider value={brightness} onChange={setBrightness} min={-100} max={100} aria-label="Brightness" />
            </label>
            <label className="field">
              <span>Contrast</span>
              <GlassSlider value={contrast} onChange={setContrast} min={-100} max={100} aria-label="Contrast" />
            </label>
            <label className="field">
              <span>Filter</span>
              <PillField options={FILTERS} value={filter} onChange={setFilter} />
            </label>
            <label className="field">
              <span>Output format</span>
              <PillField options={FORMATS} value={format} onChange={setFormat} />
            </label>

            <GlassButton variant="filled" onClick={run} disabled={busy}>
              {busy ? "Processing…" : "Apply & Preview"}
            </GlassButton>
          </div>
        </div>
      )}
    </Panel>
  );
}
