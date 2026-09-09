"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import NextLink from "next/link";
import {
  LayoutDashboard,
  Upload,
  FolderOpen,
  Scissors,
  Subtitles,
  Film,
  BarChart3,
  Video,
  Settings,
  Play,
  RefreshCw,
  Sparkles,
  Loader2,
  X,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileVideo,
  PlaySquare,
  Link,
  Plus,
  Menu,
} from "lucide-react";

const API =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ProjectStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | string;

type Project = {
  id: string;
  name: string;
  source_type?: string;
  source_url?: string | null;
  original_filename?: string | null;
  status?: ProjectStatus;
  created_at?: string;
  updated_at?: string;
};

type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
};

type TranscriptResponse = {
  text?: string;
  language?: string;
  status?: string;
  segments?: TranscriptSegment[];
};

const navItems = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Create", icon: Plus },
  { label: "Projects", icon: FolderOpen },
  { label: "Shorts", icon: Scissors },
  { label: "Long Form", icon: Film },
  { label: "AI Studio", icon: Sparkles },
  { label: "Analytics", icon: BarChart3 },
  { label: "My Channel", icon: PlaySquare },
  { label: "Settings", icon: Settings },
];

function navHref(label: string) {
  return { Dashboard: "/", Create: "/#create", Projects: "/", Shorts: "/shorts", "Long Form": "/long-form", "AI Studio": "/ai-studio", Analytics: "/analytics", "My Channel": "/channel", Settings: "/settings" }[label] || "/";
}

function formatDate(value?: string) {
  if (!value) return "Just now";

  try {
    return new Date(value).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "Just now";
  }
}

function formatTime(seconds: number) {
  if (!Number.isFinite(seconds)) return "00:00";

  const total = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(
      2,
      "0"
    )}:${String(secs).padStart(2, "0")}`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(
    2,
    "0"
  )}`;
}

function statusIcon(status?: ProjectStatus) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4" />;
    case "failed":
      return <AlertCircle className="h-4 w-4" />;
    case "processing":
      return <Loader2 className="h-4 w-4 animate-spin" />;
    default:
      return <Clock className="h-4 w-4" />;
  }
}

function statusLabel(status?: ProjectStatus) {
  switch (status) {
    case "completed":
      return "Completed";
    case "processing":
      return "Processing";
    case "failed":
      return "Failed";
    case "queued":
      return "Queued";
    default:
      return status || "Queued";
  }
}

function statusClasses(status?: ProjectStatus) {
  switch (status) {
    case "completed":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    case "processing":
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    case "failed":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    default:
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  }
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadingProjects, setLoadingProjects] = useState(true);

  const [activeNav, setActiveNav] = useState("Dashboard");
  const [mobileMenu, setMobileMenu] = useState(false);

  const [dragging, setDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [projectName, setProjectName] = useState("");

  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [selectedProject, setSelectedProject] =
    useState<Project | null>(null);

  const [transcript, setTranscript] =
    useState<TranscriptResponse | null>(null);

  const [loadingTranscript, setLoadingTranscript] =
    useState(false);

  const [generatingTranscript, setGeneratingTranscript] =
    useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const completedCount = useMemo(
    () => projects.filter((p) => p.status === "completed").length,
    [projects]
  );

  const processingCount = useMemo(
    () =>
      projects.filter(
        (p) => p.status === "processing" || p.status === "queued"
      ).length,
    [projects]
  );

  async function loadProjects() {
    try {
      setLoadingProjects(true);

      const response = await fetch(`${API}/api/projects`);

      if (!response.ok) {
        throw new Error("Failed to load projects");
      }

      const data = await response.json();

      setProjects(Array.isArray(data) ? data : data.projects || []);
    } catch (error) {
      console.error(error);

      setMessage({
        type: "error",
        text: "Could not connect to the backend. Make sure FastAPI is running on port 8000.",
      });
    } finally {
      setLoadingProjects(false);
    }
  }

  useEffect(() => {
    const initialLoad = window.setTimeout(() => {
      void loadProjects();
    }, 0);

    const interval = setInterval(() => {
      loadProjects();
    }, 5000);

    return () => {
      window.clearTimeout(initialLoad);
      clearInterval(interval);
    };
  }, []);

  function showMessage(
    type: "success" | "error",
    text: string
  ) {
    setMessage({ type, text });

    setTimeout(() => {
      setMessage(null);
    }, 5000);
  }

  function handleFile(file?: File) {
    if (!file) return;

    const allowedExtensions = [
      ".mp4",
      ".mov",
      ".mkv",
      ".avi",
      ".webm",
      ".m4v",
    ];

    const extension =
      "." + file.name.split(".").pop()?.toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      showMessage(
        "error",
        "Unsupported video format. Please select MP4, MOV, MKV, AVI, WEBM or M4V."
      );
      return;
    }

    const maxSize = 2 * 1024 * 1024 * 1024;

    if (file.size > maxSize) {
      showMessage(
        "error",
        "File is too large. Maximum allowed size is 2 GB."
      );
      return;
    }

    setSelectedFile(file);

    if (!projectName) {
      setProjectName(
        file.name.replace(/\.[^/.]+$/, "")
      );
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);

    const file = event.dataTransfer.files?.[0];

    handleFile(file);
  }

  async function createProject() {
    if (!projectName.trim()) {
      showMessage(
        "error",
        "Please enter a project name."
      );
      return null;
    }

    try {
      setCreating(true);

      const body: Record<string, string> = {
        name: projectName.trim(),
      };

      if (youtubeUrl.trim()) {
        body.source_type = "youtube_url";
        body.source_url = youtubeUrl.trim();
      } else if (selectedFile) {
        body.source_type = "upload";
        body.original_filename = selectedFile.name;
      } else {
        body.source_type = "upload";
      }

      const response = await fetch(`${API}/api/projects`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Project creation failed");
      }

      const project = await response.json();

      setProjects((previous) => [
        project,
        ...previous.filter((p) => p.id !== project.id),
      ]);

      return project as Project;
    } catch (error) {
      console.error(error);

      showMessage(
        "error",
        error instanceof Error
          ? error.message
          : "Could not create project."
      );

      return null;
    } finally {
      setCreating(false);
    }
  }

  async function handleCreate() {
    if (!selectedFile && !youtubeUrl.trim()) {
      showMessage(
        "error",
        "Choose a video file or enter an authorized YouTube URL."
      );
      return;
    }

    const project = await createProject();

    if (!project) return;

    if (selectedFile) {
      await uploadFile(project.id, selectedFile);
    } else {
      try {
        const response = await fetch(`${API}/api/projects/${project.id}/youtube`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: youtubeUrl.trim() }),
        });
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || "Authorized YouTube import failed.");
        }
        showMessage("success", "Authorized YouTube import queued.");
      } catch (error) {
        showMessage("error", error instanceof Error ? error.message : "YouTube import failed.");
      }

      setProjectName("");
      setYoutubeUrl("");

      await loadProjects();
    }
  }

  async function uploadFile(
    projectId: string,
    file: File
  ) {
    try {
      setUploading(true);

      const formData = new FormData();

      formData.append("file", file);

      const response = await fetch(
        `${API}/api/projects/${projectId}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || "Video upload failed"
        );
      }

      const data = await response.json();

      showMessage(
        "success",
        data.message || "Video uploaded successfully."
      );

      setSelectedFile(null);
      setProjectName("");

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      await loadProjects();
    } catch (error) {
      console.error(error);

      showMessage(
        "error",
        error instanceof Error
          ? error.message
          : "Video upload failed."
      );
    } finally {
      setUploading(false);
    }
  }

  async function loadTranscript(project: Project) {
    try {
      setLoadingTranscript(true);
      setSelectedProject(project);
      setTranscript(null);

      const response = await fetch(
        `${API}/api/projects/${project.id}/transcript`
      );

      if (!response.ok) {
        throw new Error("Could not load transcript.");
      }

      const data = await response.json();

      setTranscript(data);
    } catch (error) {
      console.error(error);

      showMessage(
        "error",
        "Could not load transcript."
      );
    } finally {
      setLoadingTranscript(false);
    }
  }

  async function generateTranscript(project: Project) {
    try {
      setGeneratingTranscript(true);
      setSelectedProject(project);

      const response = await fetch(
        `${API}/api/projects/${project.id}/transcribe`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          errorText || "Transcript generation failed."
        );
      }

      const data: TranscriptResponse =
        await response.json();

      setTranscript(data);

      showMessage(
        "success",
        "AI transcript generated successfully."
      );
    } catch (error) {
      console.error(error);

      showMessage(
        "error",
        error instanceof Error
          ? error.message
          : "Transcript generation failed."
      );
    } finally {
      setGeneratingTranscript(false);
    }
  }

  function clearSelection() {
    setSelectedFile(null);
    setProjectName("");
    setYoutubeUrl("");

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  return (
    <div className="min-h-screen bg-obsidian text-white">
      {/* Mobile Header */}
      <div className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 shadow-sm backdrop-blur md:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-amber-500 text-white shadow-md shadow-violet-500/20">
            <Scissors className="h-5 w-5" />
          </div>

          <span className="font-semibold">
            NyxarClip AI
          </span>
        </div>

        <button
          onClick={() => setMobileMenu(!mobileMenu)}
          className="rounded-lg p-2 hover:bg-white/10"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200/80 bg-white/85 p-4 shadow-[0_10px_30px_-15px_rgba(0,0,0,0.12)] backdrop-blur-2xl transition-transform md:translate-x-0 ${
            mobileMenu
              ? "translate-x-0"
              : "-translate-x-full"
          }`}
        >
          <div className="mb-8 flex items-center gap-3 px-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-amber-500 text-white shadow-md shadow-violet-500/20">
              <Scissors className="h-5 w-5" />
            </div>

            <div>
              <div className="font-semibold">
                NyxarClip AI
              </div>
              <div className="text-xs text-slate-500">
                Creator workspace
              </div>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active =
                activeNav === item.label;

              return (
                <NextLink
                  key={item.label}
                  href={navHref(item.label)}
                  onClick={() => { setActiveNav(item.label); setMobileMenu(false); }}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                    active
                      ? "border-l-2 border-violet-600 bg-gradient-to-r from-violet-100 to-amber-50 text-violet-800 shadow-[0_0_24px_rgba(124,58,237,0.12)]"
                      : "border-l-2 border-transparent text-slate-600 hover:border-amber-500/50 hover:bg-slate-50 hover:text-slate-900"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </NextLink>
              );
            })}
          </nav>

          <div className="mt-auto rounded-2xl border border-amber-200/80 bg-amber-50/70 p-4 shadow-sm">
            <div className="mb-2 flex items-center gap-2 text-xs font-medium text-slate-800">
              <Sparkles className="h-4 w-4" />
              Local processing
            </div>

              <p className="text-xs leading-5 text-zinc-500">
              Local media analysis is available now. Optional providers can be configured in the backend environment.
            </p>
            <div className="mt-4 border-t border-amber-200/70 pt-3 text-[11px] uppercase tracking-wider text-slate-500">
              <div className="text-amber-700">Developed by VARUN KUMAR H L • PES UNIVERSITY</div>
            </div>
          </div>
        </aside>

        {/* Main */}
        <main className="min-h-screen w-full md:ml-64">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            {/* Header */}
            <header className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
              <div>
                <p className="mb-1 text-sm uppercase tracking-widest text-amber-700/70">
                  Dashboard
                </p>

                <h1 className="luxury-title text-2xl font-semibold tracking-tight sm:text-3xl">
                  Turn one video into an entire content package.
                </h1>

                <p className="mt-2 text-sm text-slate-600">
                  Upload a video and prepare it for AI-powered
                  content repurposing.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={loadProjects}
                disabled={loadingProjects}
                className="flex w-fit items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2.5 text-sm text-zinc-300 transition hover:bg-white/[0.07]"
              >
                <RefreshCw
                  className={`h-4 w-4 ${
                    loadingProjects
                      ? "animate-spin"
                      : ""
                  }`}
                />
                Refresh
              </button>
              </div>
            </header>

            {/* Toast */}
            {message && (
              <div
                className={`mb-6 flex items-center justify-between rounded-xl border px-4 py-3 text-sm ${
                  message.type === "success"
                    ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                    : "border-red-500/20 bg-red-500/10 text-red-300"
                }`}
              >
                <div className="flex items-center gap-2">
                  {message.type === "success" ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}

                  {message.text}
                </div>

                <button
                  onClick={() => setMessage(null)}
                  className="ml-4 rounded-lg p-1 hover:bg-white/10"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            {/* Stats */}
            <section className="mb-6 grid gap-4 sm:grid-cols-3">
              <StatCard
                icon={FolderOpen}
                label="Projects"
                value={projects.length}
              />

              <StatCard
                icon={Loader2}
                label="Processing"
                value={processingCount}
              />

              <StatCard
                icon={CheckCircle2}
                label="Completed"
                value={completedCount}
              />
            </section>

            {/* Create Card */}
            <section id="create" className="luxury-panel mb-8 rounded-2xl p-5 sm:p-7">
              <div className="mb-6">
                <div className="mb-2 flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-violet-600" />

                  <h2 className="text-lg font-semibold">
                    Create a project
                  </h2>
                </div>

                <p className="text-sm text-zinc-500">
                  Start with a video upload or an authorized
                  YouTube URL.
                </p>
              </div>

              <div className="grid gap-6 lg:grid-cols-2">
                {/* Upload */}
                <div>
                  <div className="mb-3 flex items-center justify-between">
                    <label className="text-sm font-medium">
                      Upload Video
                    </label>

                    {selectedFile && (
                      <button
                        onClick={clearSelection}
                        className="text-xs text-zinc-500 hover:text-white"
                      >
                        Clear
                      </button>
                    )}
                  </div>

                  <div
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() =>
                      setDragging(false)
                    }
                    onDrop={handleDrop}
                    onClick={() =>
                      fileInputRef.current?.click()
                    }
                    className={`cursor-pointer rounded-xl border border-dashed p-8 text-center transition ${
                      dragging
                        ? "border-white bg-white/10"
                        : "border-white/15 bg-black/20 hover:border-white/30 hover:bg-white/[0.03]"
                    }`}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="video/*"
                      className="hidden"
                      onChange={(event) =>
                        handleFile(
                          event.target.files?.[0]
                        )
                      }
                    />

                    {selectedFile ? (
                      <>
                        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10">
                          <FileVideo className="h-6 w-6 text-emerald-400" />
                        </div>

                        <p className="truncate px-4 text-sm font-medium">
                          {selectedFile.name}
                        </p>

                        <p className="mt-1 text-xs text-zinc-500">
                          {(
                            selectedFile.size /
                            1024 /
                            1024
                          ).toFixed(1)}{" "}
                          MB
                        </p>
                      </>
                    ) : (
                      <>
                        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5">
                          <Upload className="h-6 w-6 text-zinc-300" />
                        </div>

                        <p className="text-sm font-medium">
                          Drop your video here
                        </p>

                        <p className="mt-1 text-xs text-zinc-500">
                          or click to browse files
                        </p>

                        <p className="mt-3 text-[11px] text-zinc-600">
                          MP4, MOV, MKV, AVI, WEBM • Max 2 GB
                        </p>
                      </>
                    )}
                  </div>
                </div>

                {/* YouTube */}
                <div>
                  <label className="mb-3 block text-sm font-medium">
                    Authorized YouTube URL
                  </label>

                  <div className="rounded-xl border border-stone-200 bg-[#fbf9f6] p-5">
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5">
                      <PlaySquare className="h-6 w-6 text-zinc-300" />
                    </div>

                    <div className="relative">
                      <Link className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" />

                      <input
                        value={youtubeUrl}
                        onChange={(event) =>
                          setYoutubeUrl(event.target.value)
                        }
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="w-full rounded-xl border border-white/10 bg-white/[0.03] py-3 pl-10 pr-3 text-sm outline-none transition placeholder:text-zinc-600 focus:border-white/30"
                      />
                    </div>

                    <p className="mt-3 text-xs leading-5 text-zinc-600">
                      The URL is validated and stored for now.
                      Unrestricted YouTube downloading is not
                      implemented.
                    </p>
                  </div>
                </div>
              </div>

              {/* Project name */}
              <div className="mt-6">
                <label className="mb-2 block text-sm font-medium">
                  Project Name
                </label>

                <input
                  value={projectName}
                  onChange={(event) =>
                    setProjectName(event.target.value)
                  }
                  placeholder="My video project"
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-4 py-3 text-sm outline-none transition placeholder:text-zinc-600 focus:border-white/30"
                />
              </div>

              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-zinc-600">
                  Local workspace
                </p>

                <button
                  onClick={handleCreate}
                  disabled={
                    creating ||
                    uploading ||
                    (!selectedFile &&
                      !youtubeUrl.trim())
                  }
                  className="luxury-action flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {creating || uploading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      {uploading
                        ? "Uploading..."
                        : "Creating..."}
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      Create Project
                    </>
                  )}
                </button>
              </div>
            </section>

            {/* Recent Projects */}
            <section>
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">
                    Recent Projects
                  </h2>

                  <p className="mt-1 text-sm text-zinc-500">
                    Your latest video projects.
                  </p>
                </div>

                <span className="text-xs text-zinc-600">
                  {projects.length} project
                  {projects.length === 1 ? "" : "s"}
                </span>
              </div>

              {loadingProjects &&
              projects.length === 0 ? (
                <div className="rounded-2xl border border-stone-200 bg-white p-10 text-center shadow-sm">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-zinc-500" />
                  <p className="mt-3 text-sm text-zinc-500">
                    Loading projects...
                  </p>
                </div>
              ) : projects.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-stone-300 bg-white p-10 text-center">
                  <FolderOpen className="mx-auto h-8 w-8 text-zinc-700" />

                  <p className="mt-4 text-sm font-medium">
                    No projects yet
                  </p>

                  <p className="mt-1 text-xs text-zinc-600">
                    Upload your first video to get started.
                  </p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {projects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onTranscript={() =>
                        loadTranscript(project)
                      }
                      onGenerateTranscript={() =>
                        generateTranscript(project)
                      }
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        </main>
      </div>

      {/* Transcript Modal */}
      {selectedProject && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="flex max-h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-3xl border border-white/10 bg-[#101116] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="font-semibold">
                  {selectedProject.name}
                </h3>

                <p className="mt-1 text-xs text-zinc-500">
                  Transcript
                </p>
              </div>

              <button
                onClick={() => {
                  setSelectedProject(null);
                  setTranscript(null);
                }}
                className="rounded-xl p-2 text-zinc-500 hover:bg-white/5 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="overflow-y-auto p-5">
              {loadingTranscript ||
              generatingTranscript ? (
                <div className="py-16 text-center">
                  <Loader2 className="mx-auto h-7 w-7 animate-spin text-zinc-400" />

                  <p className="mt-4 text-sm text-zinc-400">
                    {generatingTranscript
                      ? "Generating transcript with AI..."
                      : "Loading transcript..."}
                  </p>
                </div>
              ) : transcript &&
                transcript.segments &&
                transcript.segments.length > 0 ? (
                <div className="space-y-3">
                  <div className="mb-5 rounded-2xl border border-white/10 bg-white/[0.025] p-4">
                    <div className="flex flex-wrap gap-4 text-xs text-zinc-500">
                      <span>
                        Language:{" "}
                        <strong className="text-zinc-300">
                          {transcript.language || "en"}
                        </strong>
                      </span>

                      <span>
                        Segments:{" "}
                        <strong className="text-zinc-300">
                          {transcript.segments.length}
                        </strong>
                      </span>
                    </div>
                  </div>

                  {transcript.segments.map(
                    (segment, index) => (
                      <div
                        key={`${segment.start}-${index}`}
                        className="flex gap-4 rounded-2xl border border-white/5 bg-white/[0.02] p-4 hover:bg-white/[0.04]"
                      >
                        <div className="flex shrink-0 items-start gap-2">
                          <span className="rounded-lg bg-white/5 px-2.5 py-1 font-mono text-xs text-zinc-300">
                            {formatTime(segment.start)}
                          </span>

                          <span className="pt-1 text-zinc-700">
                            →
                          </span>

                          <span className="rounded-lg bg-white/5 px-2.5 py-1 font-mono text-xs text-zinc-500">
                            {formatTime(segment.end)}
                          </span>
                        </div>

                        <p className="text-sm leading-6 text-zinc-300">
                          {segment.text}
                        </p>
                      </div>
                    )
                  )}
                </div>
              ) : transcript ? (
                <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <Subtitles className="h-5 w-5 text-zinc-400" />

                    <span className="text-sm font-medium">
                      Transcript generated
                    </span>
                  </div>

                  {transcript.text ? (
                    <p className="whitespace-pre-wrap text-sm leading-7 text-zinc-300">
                      {transcript.text}
                    </p>
                  ) : (
                    <p className="text-sm text-zinc-600">
                      The transcript contains no recognized
                      speech.
                    </p>
                  )}
                </div>
              ) : (
                <div className="py-16 text-center">
                  <Subtitles className="mx-auto h-8 w-8 text-zinc-700" />

                  <p className="mt-4 text-sm text-zinc-500">
                    No transcript loaded.
                  </p>

                  <button
                    onClick={() =>
                      generateTranscript(
                        selectedProject
                      )
                    }
                    className="mt-4 rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black hover:bg-zinc-200"
                  >
                    Generate AI Transcript
                  </button>
                </div>
              )}
            </div>

            <div className="flex flex-col gap-3 border-t border-white/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-xs text-zinc-600">
                Timestamps are generated from Whisper segment
                boundaries.
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() =>
                    generateTranscript(selectedProject)
                  }
                  disabled={generatingTranscript}
                  className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-sm text-zinc-300 hover:bg-white/5 disabled:opacity-40"
                >
                  {generatingTranscript ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  Regenerate
                </button>

                <button
                  onClick={() => {
                    setSelectedProject(null);
                    setTranscript(null);
                  }}
                  className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-black hover:bg-zinc-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof FolderOpen;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white/5">
          <Icon className="h-4 w-4 text-zinc-400" />
        </div>
      </div>

      <div className="text-2xl font-semibold">
        {value}
      </div>

      <div className="mt-1 text-xs text-zinc-500">
        {label}
      </div>
    </div>
  );
}

function ProjectCard({
  project,
  onTranscript,
  onGenerateTranscript,
}: {
  project: Project;
  onTranscript: () => void;
  onGenerateTranscript: () => void;
}) {
  const sourceIsYoutube =
    project.source_type === "youtube_url" || project.source_type === "youtube";

  return (
    <div className="group overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-violet-200 hover:shadow-md">
      <div className="relative flex h-36 items-center justify-center bg-[#f1ede8]">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-100 bg-white">
          {sourceIsYoutube ? (
            <PlaySquare className="h-6 w-6 text-zinc-400" />
          ) : (
            <Video className="h-6 w-6 text-zinc-400" />
          )}
        </div>

        <div
          className={`absolute right-3 top-3 flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11px] ${statusClasses(
            project.status
          )}`}
        >
          {statusIcon(project.status)}
          {statusLabel(project.status)}
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-sm font-medium">
              {project.name}
            </h3>

            <p className="mt-1 truncate text-xs text-zinc-600">
              {project.original_filename ||
                project.source_url ||
                "Video project"}
            </p>
          </div>

          <NextLink
            href={`/projects/${project.id}`}
            className="rounded-lg p-1.5 text-zinc-600 hover:bg-white/5 hover:text-white"
            title="Open project"
          >
            <Play className="h-4 w-4" />
          </NextLink>
        </div>

        <div className="mt-4 flex items-center justify-between text-xs text-zinc-600">
          <span>
            {formatDate(project.created_at)}
          </span>

          <span>
            {sourceIsYoutube
              ? "YouTube"
              : "Uploaded video"}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            onClick={onTranscript}
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 px-3 py-2.5 text-xs text-zinc-300 transition hover:bg-white/5 hover:text-white"
          >
            <Subtitles className="h-4 w-4" />
            Transcript
          </button>

          <button
            onClick={onGenerateTranscript}
            disabled={
              project.status === "processing"
            }
            className="flex items-center justify-center gap-2 rounded-xl bg-white px-3 py-2.5 text-xs font-semibold text-black transition hover:bg-zinc-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Sparkles className="h-4 w-4" />
            Generate AI
          </button>
        </div>
      </div>
    </div>
  );
}