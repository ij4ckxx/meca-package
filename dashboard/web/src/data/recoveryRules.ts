export interface RecoveryRule {
  id: string;
  name: string;
  description: string;
}

export const RECOVERY_RULES: RecoveryRule[] = [
  {
    id: "RR-001",
    name: "Filename recovered from path basename",
    description:
      "A declared file's name was empty but its declared path was usable; the filename is derived from the path's basename for generation purposes only.",
  },
  {
    id: "RR-002",
    name: "Missing supporting file skipped",
    description:
      "A declared, non-manuscript file (e.g. a license form, cover letter, or figure) had no matching physical file anywhere in the staged submission; the entry is skipped and the package is generated without it. The manuscript file itself is never skipped.",
  },
  {
    id: "RR-003",
    name: "Missing reviewer identity omitted",
    description:
      "A reviewer scorecard has real recommendation/comment content but no name or email; the content is kept and the identity is omitted.",
  },
  {
    id: "RR-004",
    name: "File resolved via filename tolerance matching",
    description:
      "A declared filename was resolved to a physical file via a non-exact match (stem-only, prefix, or whitespace/underscore-normalized) rather than a literal name match.",
  },
  {
    id: "RR-005",
    name: "Duplicate round-version snapshot deduplicated",
    description:
      "Multiple article-version elements shared the same sequence number and label (repeated autosave/snapshot events of one round); collapsed to a single round index entry.",
  },
  {
    id: "RR-006",
    name: "Malformed round-version metadata skipped",
    description:
      "An article-version element had an unrecognized/missing vocab-identifier or article-version-type; excluded from the round index rather than failing resolution for every round.",
  },
  {
    id: "RR-007",
    name: "Optional XML section omitted",
    description:
      "An optional article.xml section could not be populated from a configuration or source gap (e.g. no license template configured for a resolved License Type); the section is omitted rather than fabricated.",
  },
];
