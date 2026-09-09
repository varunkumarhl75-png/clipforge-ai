"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Quality = "1080p" | "4k" | "8k";

type Project = {
  id: string;
  name: string;
  video_file_path?: string | null;
};

type Short = {
  id: string;
  title: string;
  start: number;
  end: number;
  duration: number;
  hook?: string;
  score?: number;
  reason?: string;
  category?: string;
  subcategories?: string[];
  confidence?: number;
  signals?: Record<string, number>;
  detected_events?: string[];
  warnings?: string[];
  analysis_source?: string;
  status: string;
  video_url?: string | null;
};

const qualityOptions: [Quality, string, string][] = [
  ["1080p", "1080p (Standard)", "Fast local export"],
  ["4k", "4K (Ultra HD)", "2160 x 3840 portrait"],
  ["8k", "8K (Extreme AI Upscale)", "4320 x 7680 portrait"],
];

function ShortCard({ short }: { short: Short }) {
  const [expanded, setExpanded] = useState(false);
  const scorePercent = short.score ? Math.round(short.score) : 0;
  const confidencePercent = short.confidence ? Math.round(short.confidence * 100) : 0;

  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="font-semibold text-slate-900">{short.title}</h3>
          <p className="mt-1 text-xs text-slate-500">{short.hook}</p>
        </div>
        <div className="text-right">
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold text-violet-700">{scorePercent}</span>
            <span className="text-xs text-slate-500">/100</span>
          </div>
          {short.category && (
            <span className="mt-1 inline-block rounded-full bg-violet-50 px-2 py-1 text-xs font-medium text-violet-800">
              {short.category}
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-600">
        <span>
          <strong>{Math.floor(short.start / 60)}:{String(Math.floor(short.start % 60)).padStart(2, "0")}</strong>–
          <strong>{Math.floor(short.end / 60)}:{String(Math.floor(short.end % 60)).padStart(2, "0")}</strong>
        </span>
        <span>{short.duration.toFixed(1)}s</span>
        {confidencePercent > 0 && <span className="text-emerald-700">Confidence: {confidencePercent}%</span>}
        {short.status && (
          <span
            className={`rounded-full px-2 py-1 font-medium ${
              short.status === "completed"
                ? "bg-emerald-100 text-emerald-800"
                : short.status === "processing" || short.status === "queued"
                  ? "bg-amber-100 text-amber-800"
                  : "bg-red-100 text-red-800"
            }`}
          >
            {short.status}
          </span>
        )}
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-4 flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
      >
        <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? "rotate-180" : ""}`} />
        {expanded ? "Hide" : "Show"} Analysis Details
      </button>

      {expanded && (
        <div className="mt-4 space-y-4 border-t border-slate-200 pt-4">
          {short.reason && (
            <div>
              <p className="text-xs font-medium text-slate-700">Why Selected</p>
              <p className="mt-1 text-sm text-slate-600">{short.reason}</p>
            </div>
          )}

          {short.detected_events && short.detected_events.length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700">Detected Events</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {short.detected_events.map((event) => (
                  <span key={event} className="rounded-full bg-blue-100 px-2.5 py-1 text-xs text-blue-800">
                    {event}
                  </span>
                ))}
              </div>
            </div>
          )}

          {short.signals && Object.keys(short.signals).length > 0 && (
            <div>
              <p className="text-xs font-medium text-slate-700">Signal Breakdown</p>
              <div className="mt-2 grid gap-2 text-xs">
                {Object.entries(short.signals)
                  .filter(([, val]) => typeof val === "number" && val > 0)
                  .sort(([, a], [, b]) => (b as number) - (a as number))
                  .slice(0, 8)
                  .map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="capitalize text-slate-600">{key.replace(/_/g, " ")}</span>
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-32 rounded-full bg-slate-200">
                          <div
                            className="h-1.5 rounded-full bg-violet-500"
                            style={{ width: `${Math.min(100, ((value as number) / 20) * 100)}%` }}
                          />
                        </div>
                        <span className="w-8 text-right font-medium text-slate-700">{(value as number).toFixed(1)}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {short.warnings && short.warnings.length > 0 && (
            <div>
              <p className="text-xs font-medium text-amber-700">Observations</p>
              <div className="mt-2 space-y-1 rounded-lg bg-amber-50 p-3">
                {short.warnings.map((warning, idx) => (
                  <p key={idx} className="text-xs text-amber-800">
                    • {warning}
                  </p>
                ))}
              </div>
            </div>
          )}

          <div className="text-xs text-slate-500">
            {short.analysis_source && <p>Analysis: {short.analysis_source}</p>}
            {short.subcategories && short.subcategories.length > 0 && <p>Tags: {short.subcategories.join(", ")}</p>}
          </div>
        </div>
      )}

      {short.video_url && (
        <a
          href={short.video_url}
          download
          className="mt-4 block rounded-lg border border-slate-200 bg-white px-3 py-2 text-center text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Download Clip
        </a>
      )}
    </div>
  );
}

export default function Shorts() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState("");
  const [shorts, setShorts] = useState<Short[]>([]);
  const [quality, setQuality] = useState<Quality>("1080p");
  const [burn, setBurn] = useState(false);
  const [silence, setSilence] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadShorts(id: string) {
    const r = await fetch(`${API}/api/projects/${id}/shorts`);
    if (!r.ok) throw new Error("Could not load Shorts");
    setShorts(await r.json());
  }

  useEffect(() => {
    fetch(`${API}/api/projects`)
      .then(async (r) => {
        if (!r.ok) throw new Error("Could not load projects");
        return r.json();
      })
      .then((data: Project[]) => {
        setProjects(data);
        if (data[0]) setSelected(data[0].id);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!selected) return;
    const load = window.setTimeout(
      () => {
        loadShorts(selected).catch((e: Error) => setError(e.message));
      },
      0
    );
    return () => window.clearTimeout(load);
  }, [selected]);

  useEffect(() => {
    if (!selected || !shorts.some((s) => s.status === "queued" || s.status === "processing")) return;
    const timer = window.setInterval(() => {
      loadShorts(selected).catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [selected, shorts]);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/projects/${selected}/shorts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          count: 10,
          burn_captions: burn,
          remove_silence: silence,
          export_quality: quality,
        }),
      });
      if (!r.ok) throw new Error(await r.text());
      setShorts((await r.json()).shorts || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Rendering failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen p-6 sm:p-10">
      <div className="mx-auto max-w-6xl">
        <Link href="/" className="text-sm text-slate-500 hover:text-violet-700">
          ← Workspace
        </Link>

        <div className="mt-8 flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <p className="luxury-kicker text-xs">Export studio</p>
            <h1 className="mt-2 text-3xl font-semibold">Shorts studio</h1>
            <p className="mt-2 text-slate-500">Multimodal short-form clips with explainable selection analysis.</p>
          </div>

          <div className="flex max-w-2xl flex-wrap items-end gap-2">
            <label className="text-xs font-medium text-slate-600">
              Export quality
              <select
                value={quality}
                onChange={(e) => setQuality(e.target.value as Quality)}
                className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
              >
                {qualityOptions.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>

            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-3 py-2 text-xs text-slate-600">
              <input type="checkbox" checked={burn} onChange={(e) => setBurn(e.target.checked)} />
              Burn captions
            </label>

            <label className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white/80 px-3 py-2 text-xs text-slate-600">
              <input type="checkbox" checked={silence} onChange={(e) => setSilence(e.target.checked)} />
              Remove silence
            </label>

            <button
              onClick={generate}
              disabled={!selected || busy}
              className="luxury-action rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-40"
            >
              {busy ? "Queueing..." : "Generate Shorts"}
            </button>
          </div>
        </div>

        {error && <div className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}

        {shorts.length === 0 && !busy && !error && (
          <div className="mt-12 text-center">
            <p className="text-sm text-slate-500">
              No shorts generated yet. Select a project and click &quot;Generate Shorts&quot;.
            </p>
          </div>
        )}

        {shorts.length > 0 && (
          <div className="mt-8">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900">
                {shorts.length} Candidate{shorts.length !== 1 ? "s" : ""} Generated
              </h2>
              <span className="text-xs text-slate-500">Sorted by Short Potential Score • Local analysis</span>
            </div>

            <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
              {shorts.map((short) => (
                <ShortCard key={short.id} short={short} />
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
