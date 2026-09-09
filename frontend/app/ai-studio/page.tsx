"use client";

import Link from "next/link";
import { ArrowLeft, Image as ImageIcon, Loader2, Sparkles, Video } from "lucide-react";
import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

type Mode = "thumbnail" | "video";
type Aspect = "16:9" | "9:16";

const presets = [
  ["Free Fire Action", "Free Fire character in elite armor with glowing shotgun and explosive red/orange lighting", "9:16"],
  ["Spider-Man Skyline", "Spider-Man swinging through a rain-slicked neon city at dusk, dramatic low-angle shot", "9:16"],
  ["GTA Supercar Chase", "GTA V supercar chase at night under neon palm trees with police spotlight effects", "16:9"],
  ["Luxury Tech Review", "Floating futuristic smartphone with glowing circuits and warm gold ambient studio lighting", "16:9"],
] as const;
function thumbnailError(value: unknown) { const message = value instanceof Error ? value.message : ""; if (message.includes("Gemini AI is not configured")) return "Gemini is not configured. Add your Gemini API key in the backend environment settings."; if (message.includes("No Gemini image-generation model")) return "No Gemini image-generation model is configured. Configure GEMINI_IMAGE_MODEL first."; return "Thumbnail generation failed. Please try again."; }

export default function AIStudio() {
  const [mode, setMode] = useState<Mode>("thumbnail");
  const [aspect, setAspect] = useState<Aspect>("16:9");
  const [prompt, setPrompt] = useState("");
  const [generating, setGenerating] = useState(false);
  const [generatedUrl, setGeneratedUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  function choosePreset(value: (typeof presets)[number]) {
    setPrompt(value[1]);
    setAspect(value[2]);
  }

  async function handleGenerateThumbnail() {
    if (!prompt.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/generate/image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim(), aspect_ratio: aspect }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Generation failed");
      const result = await response.json();
      setGeneratedUrl(`${API_BASE}${result.media_url}`);
    } catch (generationError) {
      setError(mode === "thumbnail" ? thumbnailError(generationError) : "Generation failed. Please try again.");
    }
  }

  async function handleGenerateVideo() {
    if (!prompt.trim()) return;
    try {
      const response = await fetch(`${API_BASE}/api/generate/video`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: prompt.trim(), aspect_ratio: aspect }),
      });
      if (!response.ok) throw new Error((await response.json()).detail || "Generation failed");
      const result = await response.json();
      setGeneratedUrl(`${API_BASE}${result.media_url}`);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : "Generation failed");
    }
  }

  async function generate() {
    if (!prompt.trim()) return;
    setGenerating(true);
    setGeneratedUrl(null);
    setError("");
    try {
      if (mode === "thumbnail") await handleGenerateThumbnail();
      else await handleGenerateVideo();
    } finally {
      setGenerating(false);
    }
  }

  return (
    <main className="min-h-screen px-5 py-6 text-slate-900 sm:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="flex items-center justify-between">
          <Link href="/" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-violet-700">
            <ArrowLeft className="h-4 w-4" /> Workspace
          </Link>
        </header>

        <section className="mt-14 max-w-3xl">
          <p className="luxury-kicker text-xs">NyxarClip AI / Creator Studio</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-tight sm:text-6xl">Make the frame impossible to scroll past.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-600">Turn a sharp text direction into a thumbnail or a vertical short concept with a format built for the destination.</p>
        </section>

        <div className="mt-10 grid gap-6 lg:grid-cols-[1.25fr_.75fr]">
          <section className="luxury-panel rounded-3xl p-5 sm:p-7">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex rounded-xl border border-slate-200 bg-slate-100 p-1">
                <button onClick={() => setMode("thumbnail")} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm ${mode === "thumbnail" ? "bg-white text-violet-800 shadow-sm" : "text-slate-600"}`}><ImageIcon className="h-4 w-4" /> AI Thumbnail</button>
                <button onClick={() => setMode("video")} className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm ${mode === "video" ? "bg-white text-violet-800 shadow-sm" : "text-slate-600"}`}><Video className="h-4 w-4" /> Short AI Video</button>
              </div>
              <div className="flex items-center gap-1 rounded-xl border border-slate-200 p-1">
                {(["16:9", "9:16"] as Aspect[]).map((value) => <button key={value} onClick={() => setAspect(value)} className={`rounded-lg px-3 py-2 text-xs font-medium ${aspect === value ? "bg-violet-700 text-white" : "text-slate-500"}`}>{value}</button>)}
              </div>
            </div>

            <div className="mt-8">
              <div className="mb-3 flex items-center justify-between"><label htmlFor="prompt" className="text-sm font-medium text-slate-800">Describe your scene</label><span className="text-xs text-slate-500">{prompt.length}/500</span></div>
              <textarea id="prompt" maxLength={500} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="A cinematic moment, a subject, a mood..." className="min-h-40 w-full resize-none rounded-2xl border border-slate-200 bg-white p-4 text-sm outline-none placeholder:text-slate-400 focus:ring-4 focus:ring-violet-500/15" />
            </div>

            <div className="mt-6"><p className="mb-3 text-xs font-medium uppercase tracking-wider text-slate-600">Quick Preset Example</p><div className="flex flex-wrap gap-2">{presets.map((preset) => <button key={preset[0]} onClick={() => choosePreset(preset)} className="rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-700 hover:border-violet-400 hover:text-violet-700">{preset[0]}</button>)}</div></div>

            <button onClick={generate} disabled={!prompt.trim() || generating} className="luxury-action mt-8 flex w-full items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40">{generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}{generating ? "Composing your concept..." : `Generate ${mode === "thumbnail" ? "Thumbnail" : "Short Video"}`}</button>
            {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          </section>

          <aside className="rounded-3xl border border-slate-200 bg-slate-50 p-5 sm:p-7">
            <div className="flex items-center justify-between"><p className="text-xs uppercase tracking-[0.2em] text-slate-400">Preview canvas</p><span className="text-xs text-amber-700">{aspect}</span></div>
            <div className={`relative mt-5 flex aspect-[16/9] items-center justify-center overflow-hidden rounded-2xl border border-dashed border-slate-300 bg-gradient-to-br from-violet-100 via-white to-amber-50 ${aspect === "9:16" ? "mx-auto max-w-[220px] aspect-[9/16]" : ""}`}>
              {generatedUrl ? mode === "thumbnail" ? <img src={generatedUrl} alt={`Generated thumbnail for ${prompt}`} className="h-full w-full object-cover" /> : <video src={generatedUrl} controls autoPlay loop playsInline className="h-full w-full object-contain" /> : <div className="text-center text-slate-500"><Sparkles className="mx-auto h-6 w-6" /><p className="mt-3 text-xs">Your {mode} preview appears here</p></div>}
            </div>
            {generatedUrl && mode === "thumbnail" && <a href={generatedUrl} download="nyxarclip-thumbnail.png" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-violet-800 hover:text-violet-950">Download Thumbnail</a>}
          </aside>
        </div>
      </div>
    </main>
  );
}
