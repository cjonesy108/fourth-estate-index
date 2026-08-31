import graph from "@/data/ownership.json";
import additions from "@/data/ownership-additions.json";
import groups from "@/data/ownership-groups.json";
import contributionsFile from "@/data/contributions.json";
import contributionAdds from "@/data/contributions-additions.json";
import peopleFile from "@/data/people.json";

export type EntityType =
  | "outlet"
  | "division"
  | "operating_company"
  | "public_issuer"
  | "private_company"
  | "institution"
  | "family"
  | "trust"
  | "individual";

export type EdgeType =
  | "operates"
  | "wholly_owns"
  | "economic_equity"
  | "voting_control"
  | "beneficial_owner";

export interface OwnershipEntity {
  slug: string;
  name: string;
  type: EntityType;
  is_outlet: boolean;
  ticker?: string | null;
  cik?: string | null;
  control_summary: string;
  notes?: string | null;
}

export interface OwnershipEdge {
  holder: string;
  asset: string;
  type: EdgeType;
  pct_economic: number | null;
  pct_voting: number | null;
  as_of: string;
  source_url: string;
  source_label: string;
  confidence: "high" | "medium" | "draft";
  notes?: string | null;
}

export interface OwnershipGraph {
  version: string;
  as_of_economic: string;
  as_of_note: string;
  entities: OwnershipEntity[];
  edges: OwnershipEdge[];
}

export type ContributionLayer = "controller" | "parent_pac" | "individual";

export interface ContributionRecord {
  entity: string;
  layer: ContributionLayer;
  cycle: string;
  amount_usd: number | null;
  amount_label: string;
  party_lean: "D" | "R" | "mixed";
  summary: string;
  source_url: string;
  source_label: string;
}

export interface Affiliation {
  person: string;
  org: string;
  role: string;
}

export interface ControlSnapshot {
  kind: "controller" | "institutional" | "closed";
  label: string;
  detail: string;
  href?: string;
  topHolders: { entity: OwnershipEntity; pct: number | null }[];
  top3Economic: number | null;
}

export interface PowerLink {
  entity: OwnershipEntity;
  via: "voting" | "economic" | "office";
  role: string;
}

const groupsFile = groups as {
  entities: OwnershipEntity[];
  edges: OwnershipEdge[];
  affiliations: Affiliation[];
};

const people = {
  affiliations: [
    ...(peopleFile as { affiliations: Affiliation[] }).affiliations,
    ...groupsFile.affiliations,
  ],
  entities: [
    ...(peopleFile as { entities: OwnershipEntity[] }).entities,
  ],
};

const data: OwnershipGraph = {
  ...(graph as OwnershipGraph),
  entities: [
    ...(graph as OwnershipGraph).entities,
    ...(additions.entities as OwnershipEntity[]),
    ...groupsFile.entities,
    ...people.entities,
  ],
  edges: [
    ...(graph as OwnershipGraph).edges,
    ...(additions.edges as OwnershipEdge[]),
    ...groupsFile.edges,
  ],
};

const contributions = {
  as_of: (contributionsFile as { as_of: string }).as_of,
  rule:
    "Firm PAC, controller, and named officer are three different checkbooks. Opening CNN does not open Fink. Clicking through BlackRock does.",
  records: [
    ...(contributionsFile as { records: ContributionRecord[] }).records,
    ...(contributionAdds as { records: ContributionRecord[] }).records,
  ],
};

const entitiesBySlug = new Map(data.entities.map((e) => [e.slug, e]));

export function getGraph(): OwnershipGraph {
  return data;
}

export function getContributionsMeta() {
  return { as_of: contributions.as_of, rule: contributions.rule };
}

export function officersOf(orgSlug: string): { person: OwnershipEntity; role: string }[] {
  return people.affiliations
    .filter((a) => a.org === orgSlug)
    .map((a) => ({ person: getEntity(a.person)!, role: a.role }))
    .filter((row) => row.person);
}

export function orgsOf(personSlug: string): { org: OwnershipEntity; role: string }[] {
  return people.affiliations
    .filter((a) => a.person === personSlug)
    .map((a) => ({ org: getEntity(a.org)!, role: a.role }))
    .filter((row) => row.org);
}

export function contributionsFor(slug: string): ContributionRecord[] {
  const slugs = new Set([slug]);
  for (const step of controlChain(slug)) slugs.add(step.entity.slug);
  const parent = publicParent(slug);
  if (parent) slugs.add(parent.slug);
  for (const { person } of officersOf(slug)) slugs.add(person.slug);
  for (const { org } of orgsOf(slug)) slugs.add(org.slug);
  return contributions.records.filter((r) => slugs.has(r.entity));
}

export function allContributions(): ContributionRecord[] {
  return contributions.records;
}

export function getEntity(slug: string): OwnershipEntity | undefined {
  return entitiesBySlug.get(slug);
}

export function listOutlets(): OwnershipEntity[] {
  return data.entities.filter((e) => e.is_outlet).sort((a, b) => a.name.localeCompare(b.name));
}

export function listInstitutions(): OwnershipEntity[] {
  return data.entities.filter((e) => e.type === "institution").sort((a, b) => a.name.localeCompare(b.name));
}

export function listControllers(): OwnershipEntity[] {
  const slugs = new Set(
    data.edges.filter((e) => e.type === "voting_control" || e.type === "beneficial_owner").map((e) => e.holder)
  );
  return data.entities.filter((e) => slugs.has(e.slug)).sort((a, b) => a.name.localeCompare(b.name));
}

const CONTROL_EDGES: EdgeType[] = ["operates", "wholly_owns", "voting_control", "beneficial_owner"];

export function controlChain(outletSlug: string): { entity: OwnershipEntity; via: OwnershipEdge | null }[] {
  const chain: { entity: OwnershipEntity; via: OwnershipEdge | null }[] = [];
  const start = getEntity(outletSlug);
  if (!start) return chain;
  chain.push({ entity: start, via: null });
  const seen = new Set<string>([outletSlug]);
  let current = outletSlug;
  for (let i = 0; i < 8; i++) {
    const incoming = data.edges.filter((e) => e.asset === current && CONTROL_EDGES.includes(e.type));
    if (!incoming.length) break;
    const next = incoming[0];
    if (seen.has(next.holder)) break;
    const holder = getEntity(next.holder);
    if (!holder) break;
    chain.push({ entity: holder, via: next });
    seen.add(next.holder);
    current = next.holder;
  }
  return chain;
}

export function publicParent(outletSlug: string): OwnershipEntity | undefined {
  return controlChain(outletSlug)
    .map((c) => c.entity)
    .find((e) => e.type === "public_issuer");
}

export function economicHolders(entitySlug: string): { entity: OwnershipEntity; edge: OwnershipEdge }[] {
  return data.edges
    .filter((e) => e.asset === entitySlug && e.type === "economic_equity")
    .map((edge) => ({ entity: getEntity(edge.holder)!, edge }))
    .filter((row) => row.entity)
    .sort((a, b) => (b.edge.pct_economic ?? 0) - (a.edge.pct_economic ?? 0));
}

export function descendantOutlets(slug: string): OwnershipEntity[] {
  const out: OwnershipEntity[] = [];
  const seen = new Set<string>();
  const stack = [slug];
  while (stack.length) {
    const cur = stack.pop()!;
    for (const edge of data.edges.filter((e) => e.holder === cur && (e.type === "operates" || e.type === "wholly_owns"))) {
      if (seen.has(edge.asset)) continue;
      seen.add(edge.asset);
      const entity = getEntity(edge.asset);
      if (!entity) continue;
      if (entity.is_outlet) out.push(entity);
      stack.push(edge.asset);
    }
  }
  return out.sort((a, b) => a.name.localeCompare(b.name));
}

export function clickThrough(slug: string): PowerLink[] {
  const links: PowerLink[] = [];
  const seen = new Set<string>([slug]);
  const add = (entity: OwnershipEntity | undefined, via: PowerLink["via"], role: string) => {
    if (!entity || seen.has(entity.slug)) return;
    seen.add(entity.slug);
    links.push({ entity, via, role });
  };

  for (const step of controlChain(slug)) {
    if (["family", "individual", "trust"].includes(step.entity.type) && step.entity.slug !== slug) {
      add(step.entity, "voting", "voting / beneficial control");
      for (const { person, role } of officersOf(step.entity.slug)) add(person, "voting", role);
    }
  }

  const focus =
    publicParent(slug) ??
    (getEntity(slug)?.type === "public_issuer" || getEntity(slug)?.type === "institution"
      ? getEntity(slug)
      : undefined);

  if (focus) {
    for (const { person, role } of officersOf(focus.slug)) add(person, "office", `${role}, ${focus.name}`);
    for (const h of economicHolders(focus.slug)) {
      add(h.entity, "economic", `${formatPct(h.edge.pct_economic)} of ${focus.ticker ?? focus.name}`);
      for (const { person, role } of officersOf(h.entity.slug)) {
        add(person, "office", `${role}, ${h.entity.name}`);
      }
    }
  }

  for (const { person, role } of officersOf(slug)) add(person, "office", role);
  return links;
}

export function controlSnapshot(outletSlug: string): ControlSnapshot {
  const chain = controlChain(outletSlug);
  const controllerStep = [...chain].reverse().find((c) =>
    ["family", "individual", "trust"].includes(c.entity.type)
  );
  const parent = publicParent(outletSlug);
  const holders = parent ? economicHolders(parent.slug) : [];
  const top = holders.slice(0, 3).map((h) => ({ entity: h.entity, pct: h.edge.pct_economic }));
  const top3Economic =
    top.length && top.every((t) => t.pct != null)
      ? top.reduce((s, t) => s + (t.pct ?? 0), 0)
      : null;

  if (controllerStep) {
    const via = controllerStep.via;
    const vote = via?.pct_voting != null ? `${formatPct(via.pct_voting)} voting` : "voting control";
    return {
      kind: "controller",
      label: controllerStep.entity.name,
      detail: vote,
      href: `/ownership/${controllerStep.entity.slug}`,
      topHolders: top,
      top3Economic,
    };
  }

  if (parent) {
    const names = top
      .map((t) => `${t.entity.name}${t.pct != null ? ` ${formatPct(t.pct)}` : ""}`)
      .join(" · ");
    return {
      kind: "institutional",
      label: `1-share-1-vote (${parent.ticker ?? parent.name})`,
      detail: names
        ? `Top holders ${names}${top3Economic != null ? ` · top 3 = ${formatPct(top3Economic)}` : ""}`
        : "No 13F rows in seed yet — widely held, no dual-class controller",
      href: `/ownership/${parent.slug}`,
      topHolders: top,
      top3Economic,
    };
  }

  const tail = chain[chain.length - 1]?.entity;
  return {
    kind: "closed",
    label: tail && tail.slug !== outletSlug ? tail.name : "Private / nonprofit",
    detail: tail?.type === "trust" ? "Trust — no residual shareholders" : "No public float",
    href: tail && tail.slug !== outletSlug ? `/ownership/${tail.slug}` : undefined,
    topHolders: [],
    top3Economic: 100,
  };
}

export interface HolderPosition {
  issuer: OwnershipEntity;
  edge: OwnershipEdge;
  outlets: OwnershipEntity[];
}

export function institutionHoldings(institutionSlug: string): HolderPosition[] {
  return data.edges
    .filter((e) => e.holder === institutionSlug && e.type === "economic_equity")
    .map((edge) => ({
      issuer: getEntity(edge.asset)!,
      edge,
      outlets: descendantOutlets(edge.asset),
    }))
    .filter((row) => row.issuer)
    .sort((a, b) => (b.edge.pct_economic ?? 0) - (a.edge.pct_economic ?? 0));
}

export function controllerHoldings(controllerSlug: string): HolderPosition[] {
  return data.edges
    .filter((e) => e.holder === controllerSlug && (e.type === "voting_control" || e.type === "beneficial_owner"))
    .map((edge) => ({
      issuer: getEntity(edge.asset)!,
      edge,
      outlets: descendantOutlets(edge.asset),
    }))
    .filter((row) => row.issuer);
}

export function formatPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return `${n.toFixed(n >= 10 || Number.isInteger(n) ? 0 : 2)}%`;
}

export const EDGE_LABEL: Record<EdgeType, string> = {
  operates: "operates",
  wholly_owns: "wholly owns",
  economic_equity: "economic stake",
  voting_control: "voting control",
  beneficial_owner: "beneficial owner",
};

export const LAYER_LABEL: Record<ContributionLayer, string> = {
  controller: "Controller / family",
  parent_pac: "Entity PAC / cycle",
  individual: "Named officer (personal)",
};

export const VIA_LABEL: Record<PowerLink["via"], string> = {
  voting: "Voting control",
  economic: "Economic stake",
  office: "Office",
};
