"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const STEPS = [
  { href: "/", icon: "check_box_outline_blank", label: "Selection" },
  { href: "/requirements", icon: "fact_check", label: "Requirements" },
  { href: "/verification", icon: "analytics", label: "Verification" },
  { href: "/decision", icon: "rule", label: "Decision" },
];

const BOTTOM_LINKS = [
  { href: "/settings", icon: "settings", label: "Settings" },
  { href: "/settings", icon: "help_outline", label: "Support" },
];

export default function SideNav() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full flex flex-col z-40 w-64 bg-slate-100 border-r border-slate-200/50">
      {/* Logo */}
      <div className="px-6 py-8 flex flex-col items-start gap-1 border-b border-slate-200/50">
        <span className="text-xl font-black tracking-tight text-slate-800 leading-none">Agnes</span>
        <span className="text-[0.65rem] font-bold tracking-widest uppercase text-slate-500">Procurement Intelligence</span>
      </div>

      {/* New Analysis */}
      <div className="px-4 py-4">
        <Link href="/">
          <button className="w-full primary-gradient text-on-primary py-2.5 px-4 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 shadow-sm hover:opacity-90 transition-opacity">
            <span className="material-symbols-outlined text-[18px]">add</span>
            New Analysis
          </button>
        </Link>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 flex flex-col gap-0.5 px-2">
        {STEPS.map((step) => {
          const isActive = pathname === step.href;
          return (
            <Link
              key={step.href}
              href={step.href}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-150 ${
                isActive
                  ? "bg-white text-slate-900 font-bold shadow-sm border-l-4 border-primary"
                  : "text-slate-500 hover:bg-slate-200 font-medium"
              }`}
            >
              <span
                className="material-symbols-outlined text-[20px]"
                style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
              >
                {step.icon}
              </span>
              <span className="text-[0.75rem] tracking-wider uppercase">{step.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="mt-auto border-t border-slate-200/50 py-4 flex flex-col gap-0.5 px-2">
        {BOTTOM_LINKS.map((link) => (
          <Link
            key={link.label}
            href={link.href}
            className="flex items-center gap-3 text-slate-500 px-4 py-2.5 hover:bg-slate-200 rounded-lg transition-colors duration-150"
          >
            <span className="material-symbols-outlined text-[20px]">{link.icon}</span>
            <span className="text-[0.75rem] font-medium tracking-wider uppercase">{link.label}</span>
          </Link>
        ))}
      </div>
    </aside>
  );
}
