"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [preset, setPreset] = useState("instagram_reel");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const res = await fetch(`${API_URL}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, client_name: client, preset }),
    });
    const project = await res.json();
    router.push(`/projects/${project.id}`);
  }

  return (
    <main className="mx-auto w-full max-w-xl px-6 py-12">
      <h1 className="mb-6 text-2xl font-bold">Create a project</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Project name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Client / creator</label>
          <input
            value={client}
            onChange={(e) => setClient(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Preset</label>
          <select
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          >
            <option value="instagram_reel">Instagram Reel 9:16</option>
            <option value="horizontal_social">Horizontal Social 16:9</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-zinc-900 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
        >
          {submitting ? "Creating…" : "Create project"}
        </button>
      </form>
    </main>
  );
}
