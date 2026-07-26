"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AnalysisResult, API_URL, Asset, Job, Project } from "@/lib/api";

interface EditPlan {
  plan_version: string;
  project_id: string;
  intent: Record<string, unknown>;
  assumptions: string[];
  timeline: Array<Record<string, unknown>>;
  audio: Record<string, unknown>;
  graphics: Record<string, unknown>;
  exports: Array<Record<string, unknown>>;
  expected_qa: string[];
  confidence: number;
  review_flags: string[];
}

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [plan, setPlan] = useState<EditPlan | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  async function refresh() {
    const [p, a, an] = await Promise.all([
      fetch(`${API_URL}/projects/${id}`).then((r) => r.json()),
      fetch(`${API_URL}/projects/${id}/assets`).then((r) => r.json()),
      fetch(`${API_URL}/projects/${id}/analysis`).then((r) => r.json()).catch(() => []),
    ]);
    setProject(p);
    setAssets(a);
    setAnalysis(an);
  }

  useEffect(() => {
    refresh().catch(console.error);
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [id]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("asset_type", "video");
    await fetch(`${API_URL}/projects/${id}/assets`, { method: "POST", body: form });
    setFile(null);
    setUploading(false);
    await refresh();
  }

  async function analyze() {
    setLoading("analyzing");
    const res = await fetch(`${API_URL}/projects/${id}/analyze`, { method: "POST" });
    const j = await res.json();
    setJob(j);
    setLoading(null);
    await refresh();
  }

  async function generatePlan() {
    setLoading("planning");
    const res = await fetch(`${API_URL}/projects/${id}/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_seconds: 4 }),
    });
    const p = await res.json();
    setPlan(p);
    setLoading(null);
  }

  async function render(preview: boolean) {
    if (!plan) return;
    setLoading(preview ? "rendering-preview" : "rendering-final");
    const res = await fetch(`${API_URL}/projects/${id}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        plan,
        output_name: preview ? "preview" : "final",
        preview,
      }),
    });
    const j = await res.json();
    setJob(j);
    setLoading(null);
  }

  if (!project) return <p className="p-8">Loading…</p>;

  return (
    <main className="mx-auto w-full max-w-4xl px-6 py-12">
      <h1 className="text-2xl font-bold">{project.name}</h1>
      <p className="text-zinc-500">{project.client_name || "No client"} · {project.preset}</p>

      <section className="mt-8 rounded-xl border border-zinc-200 p-6">
        <h2 className="mb-4 font-semibold">Assets</h2>
        {assets.length === 0 ? (
          <p className="text-zinc-500">No assets yet.</p>
        ) : (
          <ul className="mb-4 space-y-2">
            {assets.map((a) => (
              <li key={a.id} className="rounded-lg bg-zinc-50 px-3 py-2 text-sm">
                {a.filename} · {a.status} · {a.sha256.slice(0, 16)}…
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={upload} className="flex items-end gap-3">
          <div className="flex-1">
            <input
              type="file"
              accept="video/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={!file || uploading}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {uploading ? "Uploading…" : "Upload"}
          </button>
        </form>
      </section>

      {analysis.length > 0 && (
        <section className="mt-6 rounded-xl border border-zinc-200 p-6">
          <h2 className="mb-4 font-semibold">Analysis</h2>
          <ul className="space-y-2">
            {analysis.map((r) => (
              <li key={r.id} className="rounded-lg bg-zinc-50 px-3 py-2 text-sm">
                {String(r.quality?.resolution || "")} · scenes: {r.scenes?.length || 0} · transcript words: {" "}
                {Array.isArray(r.transcript?.words) ? r.transcript.words.length : 0} · {r.status}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-6 rounded-xl border border-zinc-200 p-6">
        <h2 className="mb-4 font-semibold">AI Director</h2>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={analyze}
            disabled={assets.length === 0 || loading === "analyzing"}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
          >
            {loading === "analyzing" ? "Analyzing…" : "Analyze assets"}
          </button>
          <button
            onClick={generatePlan}
            disabled={assets.length === 0 || loading === "planning"}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading === "planning" ? "Planning…" : "Generate plan"}
          </button>
          <button
            onClick={() => render(true)}
            disabled={!plan || loading === "rendering-preview"}
            className="rounded-lg bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-500 disabled:opacity-50"
          >
            {loading === "rendering-preview" ? "Rendering preview…" : "Render preview"}
          </button>
          <button
            onClick={() => render(false)}
            disabled={!plan || loading === "rendering-final"}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {loading === "rendering-final" ? "Rendering final…" : "Render final"}
          </button>
        </div>

        {plan && (
          <div className="mt-4 rounded-lg bg-zinc-50 p-4 text-sm">
            <p><span className="font-medium">Confidence:</span> {plan.confidence}</p>
            <p><span className="font-medium">Review flags:</span> {plan.review_flags.join(", ") || "none"}</p>
            <p><span className="font-medium">Timeline:</span> {plan.timeline.length} segments</p>
            <pre className="mt-2 max-h-48 overflow-auto rounded bg-zinc-100 p-2 text-xs">
              {JSON.stringify(plan, null, 2)}
            </pre>
          </div>
        )}

        {job && (
          <div className="mt-4 rounded-lg bg-zinc-50 p-4 text-sm">
            <p><span className="font-medium">Status:</span> {job.status}</p>
            <p><span className="font-medium">Stage:</span> {job.stage}</p>
            {job.outputs.map((o, i) => (
              <div key={i} className="mt-2 border-t border-zinc-200 pt-2">
                <p className="font-medium">{String(o.name || "")} · {String(o.resolution || "")} · {Number(o.duration || 0).toFixed(2)}s · {String(o.kind || "")}</p>
                {o.thumbnail_path ? <p className="text-zinc-500">thumb: {String(o.thumbnail_path)}</p> : null}
                {o.caption_path ? <p className="text-zinc-500">caption: {String(o.caption_path)}</p> : null}
                <p className="break-all text-zinc-600">{String(o.path || "")}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
