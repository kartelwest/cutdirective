"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_URL, Asset, Job, Project } from "@/lib/api";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const [rendering, setRendering] = useState(false);

  async function refresh() {
    const [p, a] = await Promise.all([
      fetch(`${API_URL}/projects/${id}`).then((r) => r.json()),
      fetch(`${API_URL}/projects/${id}/assets`).then((r) => r.json()),
    ]);
    setProject(p);
    setAssets(a);
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

  async function render() {
    if (assets.length === 0) return;
    setRendering(true);
    const plan = {
      plan_version: "1.0",
      project_id: id,
      intent: {
        platform: project?.preset || "instagram_reel",
        target_seconds: 5,
        ratio: "9:16",
        goal: "Vertical slice test",
      },
      timeline: assets.slice(0, 2).map((a) => ({
        asset_id: a.id,
        source_in: 0,
        source_out: 2,
      })),
      exports: [{ name: "main", resolution: "1080x1920", container: "mp4", video_codec: "h264" }],
    };
    const res = await fetch(`${API_URL}/projects/${id}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan, output_name: "vertical_slice_v01.mp4" }),
    });
    const j = await res.json();
    setJob(j);
    setRendering(false);
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

      <section className="mt-6 rounded-xl border border-zinc-200 p-6">
        <h2 className="mb-4 font-semibold">Render</h2>
        <button
          onClick={render}
          disabled={assets.length === 0 || rendering}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {rendering ? "Rendering…" : "Render vertical slice"}
        </button>

        {job && (
          <div className="mt-4 rounded-lg bg-zinc-50 p-4 text-sm">
            <p>
              <span className="font-medium">Status:</span> {job.status}
            </p>
            <p>
              <span className="font-medium">Stage:</span> {job.stage}
            </p>
            {job.outputs.map((o, i) => (
              <p key={i} className="mt-1 break-all text-zinc-600">
                {JSON.stringify(o)}
              </p>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
