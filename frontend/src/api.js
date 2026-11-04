// Thin fetch wrapper for the MediaForge API. Every tool panel goes through
// this module so error handling and job-polling stay consistent.

async function request(path, options = {}) {
  const res = await fetch(path, options);
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
