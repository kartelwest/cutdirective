"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL, Project } from "@/lib/api";

export default function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [health, setHealth] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/projects`)
      .then((r) => r.json())
      .then(setProjects)
      .catch(console.error);
    fetch(`${API_URL}/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(console.error);
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl px-6 py-12">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">CutDirective AI</h1>
          <p className="text-zinc-500">Describe the edit. Get the cut.</p>
        </div>
        <Link
          href="/projects/new"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700"
        >
          New project
        </Link>
      </header>

      <section className="mb-10 rounded-xl border border-zinc-200 p-6">
        <h2 className="mb-4 text-lg font-semibold">System health</h2>
        {health ? (
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <dt className="text-xs text-zinc-500">Status</dt>
              <dd className="font-medium">{String(health.status)}</dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">FFmpeg</dt>
              <dd className="font-medium">{health.ffmpeg ? "ok" : "missing"}</dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">Database</dt>
              <dd className="font-medium">{health.database ? "ok" : "down"}</dd>
            </div>
            <div>
              <dt className="text-xs text-zinc-500">Free space</dt>
              <dd className="font-medium">{String(health.free_gb)} GB</dd>
            </div>
          </dl>
        ) : (
          <p className="text-zinc-500">Loading health…</p>
        )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold">Recent projects</h2>
        {projects.length === 0 ? (
          <p className="text-zinc-500">No projects yet. Create one to begin.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p) => (
              <li key={p.id} className="rounded-xl border border-zinc-200 p-5 hover:border-zinc-400">
                <Link href={`/projects/${p.id}`} className="block">
                  <h3 className="font-semibold">{p.name}</h3>
                  <p className="text-sm text-zinc-500">{p.client_name || "No client"} · {p.preset}</p>
                  <p className="mt-2 text-xs text-zinc-400">{p.status}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
