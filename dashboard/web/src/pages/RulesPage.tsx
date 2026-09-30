import { useMemo, useState, type ReactNode } from "react";
import { Scale, Search, ChevronDown } from "lucide-react";
import { BUSINESS_RULES, BUSINESS_RULE_SECTIONS } from "../data/businessRules";
import { RECOVERY_RULES } from "../data/recoveryRules";
import { EmptyState } from "../components/States";

function renderRichText(text: string): ReactNode {
  const parts = text.split("`");
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code key={i} className="rule-inline-code">
        {part}
      </code>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

function priorityBadgeClass(priority: string): string {
  const normalized = priority.toLowerCase();
  if (normalized.includes("critical")) return "badge-red";
  if (normalized.includes("high")) return "badge-orange";
  if (normalized.includes("medium")) return "badge-yellow";
  return "badge-neutral";
}

function confidenceBadgeClass(confidence: string): string {
  const normalized = confidence.toLowerCase();
  if (normalized.includes("confirmed")) return "badge-green";
  if (normalized.includes("strongly")) return "badge-blue";
  return "badge-neutral";
}

const FIELD_LABELS: { key: "inputSource" | "outputTarget" | "transformationLogic" | "validationRule" | "dependencies" | "evidence"; label: string }[] = [
  { key: "inputSource", label: "Input Source" },
  { key: "outputTarget", label: "Output Target" },
  { key: "transformationLogic", label: "How It Works" },
  { key: "validationRule", label: "Validation Rule" },
  { key: "dependencies", label: "Depends On" },
  { key: "evidence", label: "Evidence" },
];

function BusinessRuleItem({ rule }: { rule: (typeof BUSINESS_RULES)[number] }) {
  return (
    <details className="rule-item">
      <summary className="rule-summary">
        <ChevronDown size={15} className="rule-chevron" />
        <span className="rule-id">{rule.id}</span>
        <span className="rule-title">{renderRichText(rule.title)}</span>
        <span className="rule-summary-badges">
          {rule.priority && <span className={`badge ${priorityBadgeClass(rule.priority)}`}>{rule.priority}</span>}
        </span>
      </summary>
      <div className="rule-body">
        {rule.description && (
          <div className="rule-field">
            <span className="rule-field-label">What this rule does</span>
            <p>{renderRichText(rule.description)}</p>
          </div>
        )}
        {rule.purpose && (
          <div className="rule-field">
            <span className="rule-field-label">Why it exists</span>
            <p>{renderRichText(rule.purpose)}</p>
          </div>
        )}
        {FIELD_LABELS.map(
          ({ key, label }) =>
            rule[key] && (
              <div className="rule-field" key={key}>
                <span className="rule-field-label">{label}</span>
                <p>{renderRichText(rule[key])}</p>
              </div>
            ),
        )}
        <div className="rule-summary-badges" style={{ marginTop: 4 }}>
          {rule.confidence && <span className={`badge ${confidenceBadgeClass(rule.confidence)}`}>Confidence: {rule.confidence}</span>}
        </div>
      </div>
    </details>
  );
}

function RecoveryRuleItem({ rule }: { rule: (typeof RECOVERY_RULES)[number] }) {
  return (
    <details className="rule-item">
      <summary className="rule-summary">
        <ChevronDown size={15} className="rule-chevron" />
        <span className="rule-id">{rule.id}</span>
        <span className="rule-title">{rule.name}</span>
      </summary>
      <div className="rule-body">
        <div className="rule-field">
          <span className="rule-field-label">What happens</span>
          <p>{rule.description}</p>
        </div>
      </div>
    </details>
  );
}

export function RulesPage() {
  const [tab, setTab] = useState<"business" | "recovery">("business");
  const [search, setSearch] = useState("");
  const [section, setSection] = useState<string>("all");

  const filteredBusinessRules = useMemo(() => {
    const q = search.trim().toLowerCase();
    return BUSINESS_RULES.filter((r) => {
      if (section !== "all" && r.section !== section) return false;
      if (!q) return true;
      return (
        r.id.toLowerCase().includes(q) ||
        r.title.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        r.purpose.toLowerCase().includes(q)
      );
    });
  }, [search, section]);

  const sectionCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const r of BUSINESS_RULES) counts.set(r.section, (counts.get(r.section) ?? 0) + 1);
    return counts;
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>
            <Scale size={20} /> Rules
          </h1>
          <p className="subtitle">
            Every deterministic Business Rule and Recovery Rule the migration engine enforces — what each one does and why it was
            created. Reference-only: nothing here changes package generation.
          </p>
        </div>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "business" ? "tab-active" : ""}`} onClick={() => setTab("business")}>
          Business Rules ({BUSINESS_RULES.length})
        </button>
        <button className={`tab ${tab === "recovery" ? "tab-active" : ""}`} onClick={() => setTab("recovery")}>
          Recovery Rules ({RECOVERY_RULES.length})
        </button>
      </div>

      {tab === "business" && (
        <div className="tab-panel">
          <p className="subtitle" style={{ marginTop: 0 }}>
            Business Rules describe the ideal, target output the engine produces from source data. Each rule below was derived from
            comparing real source packages against the generated MECA output and the JATS/MECA DTDs.
          </p>
          <div className="search-row">
            <div className="search-input" style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-faint)" }} />
              <input
                style={{ width: "100%", paddingLeft: 30 }}
                placeholder="Search rules by ID, title, or description..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
          <div className="filter-row">
            <button className={`badge ${section === "all" ? "badge-blue" : "badge-neutral"}`} onClick={() => setSection("all")}>
              All ({BUSINESS_RULES.length})
            </button>
            {BUSINESS_RULE_SECTIONS.map((s) => (
              <button
                key={s.key}
                className={`badge ${section === s.key ? "badge-blue" : "badge-neutral"}`}
                onClick={() => setSection(s.key)}
                title={s.title.replace(/`/g, "")}
              >
                {s.key} ({sectionCounts.get(s.key) ?? 0})
              </button>
            ))}
          </div>

          {filteredBusinessRules.length === 0 ? (
            <EmptyState title="No rules match your search" description="Try a different keyword or clear the section filter." />
          ) : (
            <div className="rule-list">
              {filteredBusinessRules.map((rule) => (
                <BusinessRuleItem key={rule.id} rule={rule} />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "recovery" && (
        <div className="tab-panel">
          <p className="subtitle" style={{ marginTop: 0 }}>
            Recovery Rules describe the fallback the engine takes when a Business Rule can't be fully satisfied by the source data —
            without ever fabricating information. Every recovery is applied only when it can't cause an invalid package, and every
            application is recorded as a visible warning rather than applied silently.
          </p>
          <div className="rule-list">
            {RECOVERY_RULES.map((rule) => (
              <RecoveryRuleItem key={rule.id} rule={rule} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
