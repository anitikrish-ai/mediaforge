# MediaForge

All-in-one, local-first media toolkit. One FastAPI backend wires together seven
open-source media libraries behind a single unified dashboard (React + a liquid-glass
UI kit). No paid APIs, no mandatory database, no cloud dependency — everything runs
on your own machine.

## Tools

| Tool | Library doing the work | What it does |
|---|---|---|
| Image Studio | Pillow, scikit-image, OpenCV | Resize/crop/rotate/flip/format convert (Pillow), auto-contrast/sharpen/denoise (scikit-image: CLAHE, unsharp mask, non-local-means), brightness/contrast + 7 creative filters (OpenCV) |
| Background Remover | rembg | Local AI background removal with 5 selectable ONNX models (u2net, u2netp, u2net_human_seg, isnet-general-use, silueta), optional alpha matting, optional solid background fill |
| Detection & Tracking | OpenCV + supervision | HOG pedestrian / Haar-cascade face & eye detection on images; motion/people/face detection with ByteTrack multi-object tracking on video, annotated with bounding boxes + traces |
| Video Studio | OpenCV | Probe metadata, trim, resize, and frame extraction — streamed as background jobs with live progress |
| Batch Processor | Pillow/scikit-image + rembg | Apply one operation (filter, sharpen, enhance, or background removal) across up to 20 files at once |
| Web Extractor | trafilatura | Clean article text + metadata (title, author, date, reading time) from any URL |
| Media Downloader | yt-dlp | Probe available formats/qualities and download video or audio from 1000+ sites, with live download progress |

All seven libraries are load-bearing — none are decorative. `/api/libraries` confirms
each one imports successfully at runtime.

## Architecture

```
backend/
  app/
    core/        # settings, job manager, storage/cleanup, upload+URL validation
    services/    # one module per library integration (pure functions, no FastAPI)
    routers/     # one router per tool, thin HTTP layer over the services
    main.py      # app wiring + background cleanup loop
frontend/
  src/
    api.js       # fetch wrapper + job polling
    components/  # shared Dropzone, ProgressBar, Panel, SegmentedField
    tools/       # one panel per tool (mirrors backend routers 1:1)
    App.jsx      # sidebar + routing shell
```

- **Async/background processing**: anything that takes more than ~1s (batch image ops,
  video trim/resize/frame-extraction, video detection/tracking, yt-dlp downloads) runs
  as a FastAPI `BackgroundTasks` job tracked by an in-memory job manager. The frontend
  polls `GET /api/jobs/{id}` for live progress.
- **Secure temp storage & cleanup**: uploads land in `backend/storage/tmp`, outputs in
  `backend/storage/outputs`. A background loop purges anything older than
  `MEDIAFORGE_JOB_TTL_SECONDS` (default 1h) every `MEDIAFORGE_CLEANUP_INTERVAL_SECONDS`
  (default 10m).
- **Upload validation**: every upload is checked for extension and size limit before
  touching a library. Every downloader URL is checked against a private/internal-IP
  blocklist before being fetched (basic SSRF guard).
- **No database, no accounts**: job state lives in memory for the life of the process;
  files are the only persistence, and they're self-cleaning.

## Setup

### Backend (local)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Verify: `curl http://localhost:8000/api/libraries` should report `"ok"` for all 7
libraries. `rembg`'s first run per model downloads ONNX weights (a few MB to ~150MB
depending on model) to `~/.u2net/` — one-time, fully local after that, no account needed.

For a real deployment (not local), see **Deployment** below — the backend runs as a
container, not a plain `uvicorn` process on bare metal.

### Frontend

```bash
cd frontend
npm install
npm run dev      # dev server on :5173, proxies /api to :8000
# or
npm run build && npm run preview   # production build
```

Open `http://localhost:5173`.

## Deployment

The backend is a real CV/ML workload (OpenCV, scikit-image, ONNX inference via rembg,
and `yt-dlp` shelling out to `ffmpeg`). That doesn't fit a serverless platform like
Vercel: its Python functions cap out at 500MB bundled — this backend's dependencies
alone run closer to 900MB — and there's no `ffmpeg` binary available in that runtime
anyway. So the two halves deploy separately:

- **Frontend → Vercel.** Static Vite build, `vercel.json` at the repo root points
  Vercel at `frontend/`. Nothing else needed.
- **Backend → a container host.** Anywhere that builds from `backend/Dockerfile` and
  has no 500MB-style cap works: Railway, Render, Fly.io, Cloud Run, a plain VPS. The
  Dockerfile installs `ffmpeg` + OpenCV's runtime libs and respects `$PORT`.

Wire them together with one env var:

1. Deploy `backend/` to your container host of choice. Note the public URL it gives
   you (e.g. `https://mediaforge-backend.up.railway.app`).
2. In the Vercel project's **Settings → Environment Variables**, add
   `VITE_API_BASE` = that URL (no trailing slash), for the Production (and Preview,
   if you want previews to work too) environment.
3. Redeploy the frontend on Vercel. `VITE_API_BASE` is read at **build time** by Vite
   (`import.meta.env.VITE_API_BASE` in `src/api.js`) and gets baked into the static
   bundle — every API call and every backend-served file link (`apiUrl()` in
   `src/api.js`) resolves against it instead of a relative path.

Left unset, `VITE_API_BASE` falls back to `""` (relative paths), which is what local
`vite dev` wants — that's why `vite.config.js` still proxies `/api` and `/outputs` to
`127.0.0.1:8000` for local-only convenience; it's irrelevant once `VITE_API_BASE` is
set for a real deployment.

The backend's CORS is already open (`allow_origins=["*"]` in `app/core/config.py`),
so it accepts requests from the Vercel domain with no further change. Tighten that to
your actual frontend origin once both are live, if you want.

### Configuration

Backend settings are environment-driven (prefix `MEDIAFORGE_`), see `app/core/config.py`:

| Variable | Default | Meaning |
|---|---|---|
| `MEDIAFORGE_MAX_IMAGE_MB` | 25 | Max single image upload size |
| `MEDIAFORGE_MAX_VIDEO_MB` | 500 | Max single video upload size |
| `MEDIAFORGE_MAX_BATCH_FILES` | 20 | Max files per batch request |
| `MEDIAFORGE_JOB_TTL_SECONDS` | 3600 | How long outputs live before cleanup |
| `MEDIAFORGE_CLEANUP_INTERVAL_SECONDS` | 600 | How often the cleanup sweep runs |

## Notes on model/dependency choices

- Detection uses only what ships inside OpenCV itself (HOG pedestrian detector, Haar
  cascades for face/eye) — zero extra model downloads required to satisfy "no
  unnecessary AI models." An optional path (`detect_yolo_onnx` in
  `detection_service.py`) accepts a user-supplied ONNX YOLO model via OpenCV's DNN
  module for higher-quality multi-class detection — entirely opt-in, never required.
- `rembg` models are the only mandatory AI models, as required by the brief, and all
  five bundled options run fully offline after their one-time local download.
- `supervision` is pinned to `0.26.1` — newer releases (0.27+) dropped the bundled
  `ByteTrack` tracker out of the core package, and tracking is a stated requirement.
- `scikit-image` is pinned to `0.26.0`/Pillow to `12.x` for prebuilt-wheel support on
  modern Python (3.13); earlier pins fail to build from source there.

## Tested

Every endpoint was exercised end-to-end against real files (image pipeline with all 7
filters, background removal with the default model, image + video detection with
tracking, video probe/trim/resize/frame-extraction, batch processing, and the full UI
flows via Playwright). Web extraction and media downloading are implemented and unit-
verified against the libraries directly; outbound internet access was sandboxed in the
build environment, so live-URL runs should be re-verified once deployed with normal
network access.
