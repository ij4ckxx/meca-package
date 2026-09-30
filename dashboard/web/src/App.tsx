import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  Activity,
  LayoutDashboard,
  BookOpen,
  FileText,
  ClipboardList,
  BarChart3,
  ScrollText,
  Settings,
  History,
  GitCompare,
  HeartPulse,
  Moon,
  Sun,
  ShieldCheck,
  Scale,
} from "lucide-react";
import { HomePage } from "./pages/HomePage";
import { JournalsPage } from "./pages/JournalsPage";
import { ArticlesPage } from "./pages/ArticlesPage";
import { ArticleDetailPage } from "./pages/ArticleDetailPage";
import { MigrationAuditPage } from "./pages/MigrationAuditPage";
import { ManualReviewPage } from "./pages/ManualReviewPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { RulesPage } from "./pages/RulesPage";
import { ControlCenterPage } from "./pages/ControlCenterPage";
import { LogsPage } from "./pages/LogsPage";
import { ConfigurationPage } from "./pages/ConfigurationPage";
import { BatchHistoryPage } from "./pages/BatchHistoryPage";
import { BatchComparisonPage } from "./pages/BatchComparisonPage";
import { JournalHealthPage } from "./pages/JournalHealthPage";
import { BatchSelector } from "./components/BatchSelector";
import { useTheme } from "./context/ThemeContext";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [
      { to: "/", label: "Control Center", end: true, icon: Activity },
      { to: "/home", label: "Home", icon: LayoutDashboard },
    ],
  },
  {
    label: "Batches",
    items: [
      { to: "/batches", label: "Batch History", icon: History },
      { to: "/compare", label: "Batch Comparison", icon: GitCompare },
    ],
  },
  {
    label: "Content",
    items: [
      { to: "/articles", label: "Articles", icon: FileText },
      { to: "/journals", label: "Per Journal", icon: BookOpen },
      { to: "/manual-review", label: "Manual Review", icon: ClipboardList },
    ],
  },
  {
    label: "Quality",
    items: [
      { to: "/migration-audit", label: "Migration Audit", icon: ShieldCheck },
      { to: "/journal-health", label: "Journal Health", icon: HeartPulse },
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/rules", label: "Rules", icon: Scale },
    ],
  },
  {
    label: "System",
    items: [
      { to: "/logs", label: "Logs", icon: ScrollText },
      { to: "/configuration", label: "Configuration", icon: Settings },
    ],
  },
];

function useBreadcrumb(): { group: string; page: string } {
  const { pathname } = useLocation();
  for (const group of NAV_GROUPS) {
    for (const item of group.items) {
      const matches = item.end ? pathname === item.to : pathname === item.to || pathname.startsWith(`${item.to}/`);
      if (matches) return { group: group.label, page: item.label };
    }
  }
  if (pathname.startsWith("/articles/")) return { group: "Content", page: "Article Detail" };
  return { group: "", page: "" };
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const breadcrumb = useBreadcrumb();

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">M</span>
          <span>
            MECA
            <span className="brand-sub">Archive Migration Platform</span>
          </span>
        </div>
        <div className="nav-groups">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-section-label">{group.label.toUpperCase()}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
                >
                  <item.icon size={15} />
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>
        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === "light" ? <Moon size={15} /> : <Sun size={15} />}
            {theme === "light" ? "Dark mode" : "Light mode"}
          </button>
        </div>
      </aside>
      <div className="content-area">
        <div className="topbar">
          <div className="breadcrumb">
            {breadcrumb.group && <span className="breadcrumb-group">{breadcrumb.group}</span>}
            {breadcrumb.group && <span className="breadcrumb-sep">/</span>}
            <span className="breadcrumb-page">{breadcrumb.page || "MECA Dashboard"}</span>
          </div>
          <div style={{ marginLeft: "auto" }}>
            <BatchSelector />
          </div>
        </div>
        <main className="content">
          <Routes>
            <Route path="/" element={<ControlCenterPage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/batches" element={<BatchHistoryPage />} />
            <Route path="/compare" element={<BatchComparisonPage />} />
            <Route path="/journals" element={<JournalsPage />} />
            <Route path="/journal-health" element={<JournalHealthPage />} />
            <Route path="/articles" element={<ArticlesPage />} />
            <Route path="/migration-audit" element={<MigrationAuditPage />} />
            <Route path="/articles/:id" element={<ArticleDetailPage />} />
            <Route path="/manual-review" element={<ManualReviewPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/rules" element={<RulesPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/configuration" element={<ConfigurationPage />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
