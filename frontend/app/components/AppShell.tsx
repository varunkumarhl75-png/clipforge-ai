"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, Film, FolderOpen, LayoutDashboard, Menu, PlaySquare, Scissors, Settings, Sparkles, X } from "lucide-react";
import { ReactNode, useState } from "react";

const navigation = [["Dashboard", "/", LayoutDashboard], ["Create", "/#create", Sparkles], ["Projects", "/projects", FolderOpen], ["Shorts", "/shorts", Scissors], ["Long Form", "/long-form", Film], ["AI Studio", "/ai-studio", Sparkles], ["Analytics", "/analytics", BarChart3], ["My Channel", "/channel", PlaySquare], ["Settings", "/settings", Settings]] as const;

export function AppShell({ children, active }: { children: ReactNode; active?: string }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return <div className="app-shell">
    <button aria-label={open ? "Close navigation" : "Open navigation"} className="mobile-menu" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
    {open && <button aria-label="Close navigation overlay" className="sidebar-overlay" onClick={() => setOpen(false)} />}
    <aside className={`app-sidebar ${open ? "is-open" : ""}`}>
      <div className="brand-lockup"><div className="brand-mark"><Scissors /></div><div><p className="brand-name"><span>Nyxar</span>Clip AI</p><p className="brand-tagline">Turn one video into an entire content package.</p></div></div>
      <nav className="app-nav" aria-label="Main navigation">{navigation.map(([label, href, Icon]) => { const selected = active === label || (!active && (href === pathname || (href === "/projects" && pathname.startsWith("/projects")))); return <Link key={label} href={href} onClick={() => setOpen(false)} className={`app-nav-item ${selected ? "is-active" : ""}`}><Icon />{label}</Link>; })}</nav>
      <div className="sidebar-note"><Sparkles /><div><strong>Local studio</strong><p>Media analysis runs in your configured workspace.</p></div></div>
      <div className="creator-signature"><span>VARUN KUMAR HL</span><small>PES UNIVERSITY</small></div>
    </aside>
    <div className="app-content">{children}</div>
  </div>;
}
