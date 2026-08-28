import graph from "@/data/ownership.json";

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

const data = graph as OwnershipGraph;

const entitiesBySlug = new Map(data.entities.map((e) => [e.slug, e]));

export function getGraph(): OwnershipGraph {
  return data;
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

export function edgesFrom(slug: string): OwnershipEdge[] {
  return data.edges.filter((e) => e.holder === slug);
}

export function edgesTo(slug: string): OwnershipEdge[] {
  return data.edges.filter((e) => e.asset === slug);
}

const CONTROL_EDGES: EdgeType[] = ["operates", "wholly_owns", "voting_control", "beneficial_owner"];

/** Walk holders of an asset along operating/control edges (not 13F). */
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

/** Ultimate public issuer on the control chain, if any. */
export function publicParent(outletSlug: string): OwnershipEntity | undefined {
  return controlChain(outletSlug).map((c) => c.entity).find((e) => e.type === "public_issuer");
}

/** Who holds economic equity in this entity (13F / economic_equity edges only). */
export function economicHolders(entitySlug: string): { entity: OwnershipEntity; edge: OwnershipEdge }[] {
  return data.edges
    .filter((e) => e.asset === entitySlug && e.type === "economic_equity")
    .map((edge) => ({ entity: getEntity(edge.holder)!, edge }))
    .filter((row) => row.entity)
    .sort((a, b) => (b.edge.pct_economic ?? 0) - (a.edge.pct_economic ?? 0));
}

/** Outlets reachable downward from an issuer/holder via operates/wholly_owns. */
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

export interface HolderPosition {
  issuer: OwnershipEntity;
  edge: OwnershipEdge;
  outlets: OwnershipEntity[];
}

/** Media issuers an institution holds, plus the outlets under each issuer. */
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
