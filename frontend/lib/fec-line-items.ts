import lineFile from "@/data/contributions-line-items.json";

export type LineItemKind = "candidate" | "pac" | "party" | "super_pac";

export interface ContributionLineItem {
  entity: string;
  date: string;
  amount_usd: number;
  recipient: string;
  recipient_type: LineItemKind;
  party: "D" | "R" | "mixed";
  source_url: string;
  source_label: string;
  notes?: string;
}

const file = lineFile as {
  as_of: string;
  rule: string;
  items: ContributionLineItem[];
};

export function lineItemsMeta() {
  return { as_of: file.as_of, rule: file.rule };
}

export function lineItemsFor(entitySlug: string): ContributionLineItem[] {
  return file.items
    .filter((row) => row.entity === entitySlug)
    .sort((a, b) => b.date.localeCompare(a.date) || b.amount_usd - a.amount_usd);
}

export function formatUsd(n: number): string {
  if (n >= 1_000_000) {
    const m = n / 1_000_000;
    return `$${m % 1 === 0 ? m.toFixed(0) : m.toFixed(1)}M`;
  }
  if (n >= 1_000) {
    return `$${Math.round(n / 1_000)}k`;
  }
  return `$${n.toLocaleString("en-US")}`;
}

export const LINE_KIND_LABEL: Record<LineItemKind, string> = {
  candidate: "Candidate",
  pac: "PAC",
  party: "Party / victory fund",
  super_pac: "Super PAC",
};
