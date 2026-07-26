export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  client_name: string | null;
  workspace_path: string;
  status: string;
  preset: string;
  approval_mode: string;
  brief: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  filename: string;
  original_path: string;
  workspace_path: string;
  sha256: string;
  asset_type: string;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface AnalysisResult {
  id: string;
  asset_id: string;
  project_id: string;
  status: string;
  transcript: Record<string, unknown>;
  scenes: unknown[];
  audio_events: Record<string, unknown>;
  quality: Record<string, unknown>;
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  stage: string;
  progress: number;
  status: string;
  outputs: Array<Record<string, unknown>>;
  logs: string;
  created_at: string;
  updated_at: string;
}
