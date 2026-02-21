"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./theme-toggle";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "grid" },
  { href: "/servers", label: "Servers", icon: "server" },
  { href: "/tools", label: "Tools", icon: "wrench" },
  { href: "/activity", label: "Activity", icon: "clock" },
  { href: "/api-reference", label: "API Reference", icon: "book" },
  { href: "/settings", label: "Settings", icon: "cog" },
] as const;

const ICONS: Record<string, string> = {
  grid: "M3 3h7v7H3V3zm11 0h7v7h-7V3zm0 11h7v7h-7v-7zM3 14h7v7H3v-7z",
  server:
    "M4 6h16M4 6a2 2 0 01-2-2V4a2 2 0 012-2h16a2 2 0 012 2v0a2 2 0 01-2 2M4 6v6m16-6v6M4 12h16M4 12a2 2 0 00-2 2v0a2 2 0 002 2h16a2 2 0 002-2v0a2 2 0 00-2-2M6 4h.01M6 12h.01",
  wrench:
    "M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z",
  clock: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  book: "M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25",
  cog: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
};

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="flex w-56 flex-col border-r"
      style={{
        background: "var(--bg-secondary)",
        borderColor: "var(--border)",
      }}
    >
      <div
        className="flex items-center justify-between border-b px-5 py-4"
        style={{ borderColor: "var(--border)" }}
      >
        <Link href="/" className="text-lg font-bold text-gradient">
          MCPFarm.ai
        </Link>
        <ThemeToggle />
      </div>
      <nav className="flex-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`mb-1 flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-neural-500/10 text-neural-400"
                  : "hover:bg-[var(--bg-tertiary)]"
              }`}
              style={active ? {} : { color: "var(--text-secondary)" }}
            >
              <svg
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d={ICONS[item.icon]}
                />
              </svg>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div
        className="border-t px-5 py-3"
        style={{ borderColor: "var(--border)" }}
      >
        <span style={{ color: "var(--text-tertiary)" }} className="text-xs">
          v0.1.0
        </span>
      </div>
    </aside>
  );
}
