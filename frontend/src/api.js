// Thin fetch wrapper for the MediaForge API. Every tool panel goes through
// this module so error handling and job-polling stay consistent.
//
// The backend is a separate deployment (see README — it doesn't fit Vercel's
// serverless function size limit, so it's hosted elsewhere, e.g. Railway).
// VITE_API_BASE is a build-time env var pointing at that backend's public
// origin, e.g. "https://mediaforge-backend.up.railway.app" (no trailing
// slash). Left unset, it falls back to same-origin relative paths, which is
// what the local `vite dev` proxy expects.
const API_BASE = import.meta.env.VITE_API_BASE || "";

/** Prefix any backend-relative path (including one returned inside a JSON
 * response, e.g. result.download_url) with the backend's origin. Every <img>,
 * <video>, and <a href> that points at a backend-served file must go through
 * this — only requests made via postForm/getJSON below are prefixed for you. */
export function apiUrl(path) {
  if (!path) return path;
  if (/^https?:\/\//i.test(path)) return path; // already absolute (e.g. yt-dlp thumbnail)
  return `${API_BASE}${path}`;
}

async function request(path, options = {}) {
  const res = await fetch(apiUrl(path), options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* non-JSON error body, keep statusText */
    }
    throw new Error(detail);
  }
  return res;
}

export async function postForm(path, formData) {
  const res = await request(path, { method: "POST", body: formData });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.blob();
}

export async function getJSON(path) {
  const res = await request(path);
  return res.json();
}

/** Poll /api/jobs/{id} until done/error, calling onProgress with each update. */
export async function waitForJob(jobId, onProgress, intervalMs = 700) {
  while (true) {
    const job = await getJSON(`/api/jobs/${jobId}`);
    onProgress?.(job);
    if (job.status === "done") return job.result;
    if (job.status === "error") throw new Error(job.error || "Job failed");
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}

export function blobDownloadUrl(blob) {
  return URL.createObjectURL(blob);
}
