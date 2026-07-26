"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [client, setClient] = useState("");
  const [preset, setPreset] = useState("instagram_reel");
  const [approvalMode, setApprovalMode] = useState("plan_preview");
  const [goal, setGoal] = useState("");
  const [audience, setAudience] = useState("");
  const [platform, setPlatform] = useState("");
  const [targetSeconds, setTargetSeconds] = useState("");
  const [recipients, setRecipients] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const brief: Record<string, string | number> = {};
    if (goal) brief.goal = goal;
    if (audience) brief.audience = audience;
    if (platform) brief.platform = platform;
    if (targetSeconds) brief.target_seconds = Number(targetSeconds);

    const res = await fetch(`${API_URL}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        client_name: client,
        preset,
        approval_mode: approvalMode,
        brief,
        notification_recipients: recipients.split(",").map((s) => s.trim()).filter(Boolean),
      }),
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
            <option value="tiktok_9x16">TikTok 9:16</option>
            <option value="youtube_shorts">YouTube Shorts 9:16</option>
            <option value="custom">Custom</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Approval mode</label>
          <select
            value={approvalMode}
            onChange={(e) => setApprovalMode(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          >
            <option value="plan_preview">Plan preview (approve before final)</option>
            <option value="preview_then_final">Preview then final</option>
            <option value="automatic">Automatic (final when confidence 0.8+)</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Goal / story</label>
          <textarea
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
            rows={3}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Audience</label>
          <input
            value={audience}
            onChange={(e) => setAudience(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium">Platform</label>
            <input
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              placeholder={preset}
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Target seconds</label>
            <input
              type="number"
              value={targetSeconds}
              onChange={(e) => setTargetSeconds(e.target.value)}
              className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium">Notification recipients (comma-separated emails)</label>
          <input
            value={recipients}
            onChange={(e) => setRecipients(e.target.value)}
            className="mt-1 w-full rounded-lg border border-zinc-300 px-3 py-2"
          />
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
