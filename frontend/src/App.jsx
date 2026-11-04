import { useEffect, useState } from "react";
import ImageStudio from "./tools/ImageStudio";
import BackgroundRemover from "./tools/BackgroundRemover";
import DetectionStudio from "./tools/DetectionStudio";
import VideoStudio from "./tools/VideoStudio";
import WebExtractor from "./tools/WebExtractor";
import MediaDownloader from "./tools/MediaDownloader";
import BatchProcessor from "./tools/BatchProcessor";
import { getJSON } from "./api";

const TOOLS = [
  { id: "image", label: "Image Studio", icon: "🖼️", component: ImageStudio },
  { id: "bg", label: "Background Remover", icon: "✂️", component: BackgroundRemover },
  { id: "detect", label: "Detection & Tracking", icon: "🎯", component: DetectionStudio },
  { id: "video", label: "Video Studio", icon: "🎬", component: VideoStudio },
  { id: "batch", label: "Batch Processor", icon: "📦", component: BatchProcessor },
  { id: "web", label: "Web Extractor", icon: "📰", component: WebExtractor },
  { id: "download", label: "Media Downloader", icon: "⬇️", component: MediaDownloader },
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
          <span className="brand__mark">◆</span>
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
        <ActiveTool />
      </main>
    </div>
  );
}
