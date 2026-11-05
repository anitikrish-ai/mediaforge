import { lazy, Suspense, useEffect, useState } from "react";
import { getJSON } from "./api";

// Each tool panel is its own chunk — only the active tool's code (and its
// slice of the liquid-glass library) downloads on first paint; switching
// tabs fetches the next chunk on demand instead of shipping all seven
// upfront.
const ImageStudio = lazy(() => import("./tools/ImageStudio"));
const BackgroundRemover = lazy(() => import("./tools/BackgroundRemover"));
const DetectionStudio = lazy(() => import("./tools/DetectionStudio"));
const VideoStudio = lazy(() => import("./tools/VideoStudio"));
const MediaDownloader = lazy(() => import("./tools/MediaDownloader"));
const BatchProcessor = lazy(() => import("./tools/BatchProcessor"));
const WebExtractor = lazy(() => import("./tools/WebExtractor"));

const TOOLS = [
  { id: "image", label: "Image Studio", icon: "🖼", component: ImageStudio },
  { id: "bg", label: "Background Remover", icon: "✂", component: BackgroundRemover },
  { id: "detect", label: "Detection & Tracking", icon: "🎯", component: DetectionStudio },
  { id: "video", label: "Video Studio", icon: "🎬", component: VideoStudio },
  { id: "batch", label: "Batch Processor", icon: "📦", component: BatchProcessor },
  { id: "web", label: "Web Extractor", icon: "📰", component: WebExtractor },
  { id: "download", label: "Media Downloader", icon: "⬇", component: MediaDownloader },
];

export default function App() {
  const [active, setActive] = useState("image");
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getJSON("/api/health").then(setHealth).catch(() => setHealth({ status: "offline" }));
  }, []);

  const ActiveTool = TOOLS.find((t) => t.id === active)?.component ?? ImageStudio;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">M</span>
          <span className="brand__name">MediaForge</span>
        </div>
        <nav className="nav">
          {TOOLS.map((t) => (
            <button
              key={t.id}
              className={`nav__item ${active === t.id ? "nav__item--active" : ""}`}
              onClick={() => setActive(t.id)}
            >
              <span className="nav__icon">{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </nav>
        <div className={`status-pill status-pill--${health?.status === "ok" ? "ok" : "off"}`}>
          {health?.status === "ok" ? "Backend connected" : "Connecting…"}
        </div>
      </aside>

      <main className="main">
        <Suspense fallback={<div className="tool-loading">Loading tool…</div>}>
          <ActiveTool />
        </Suspense>
      </main>

      <nav className="bottom-nav" aria-label="Tools">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            className={`bottom-nav__item ${active === t.id ? "bottom-nav__item--active" : ""}`}
            onClick={() => setActive(t.id)}
          >
            <span className="bottom-nav__icon">{t.icon}</span>
            <span>{t.label.split(" ")[0]}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
