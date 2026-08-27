// Content link selection per §9 — everything comes from config/content.json,
// nothing is hardcoded.
import {
  contentConfig,
  type BandKey,
  type BehaviorKey,
  type ContentLink,
  type SectionKey,
} from "./instrument";

function byPriority(a: ContentLink, b: ContentLink): number {
  return a.priority - b.priority;
}

function defaultLinks(): ContentLink[] {
  return contentConfig
    .filter((link) => link.section === null && link.behavior === null)
    .sort(byPriority);
}

/**
 * Links for the biggest-opportunity card: section = weakest (respecting a
 * link's band when it sets one), top 3 by priority; fall back to the section
 * regardless of band, then to the default link.
 */
export function opportunityLinks(
  weakest: SectionKey,
  band: BandKey,
  count = 3,
): ContentLink[] {
  const matching = contentConfig
    .filter(
      (link) =>
        link.section === weakest && (link.band === null || link.band === band),
    )
    .sort(byPriority);
  const pool = matching.length > 0 ? matching : defaultLinks();
  return pool.slice(0, count);
}

/** One link for a behavior, falling back to its section, then the default. */
export function behaviorLink(
  behavior: BehaviorKey,
  section: SectionKey = "actions",
): ContentLink | null {
  const direct = contentConfig
    .filter((link) => link.behavior === behavior)
    .sort(byPriority);
  if (direct.length > 0) return direct[0];
  const sectionFallback = contentConfig
    .filter((link) => link.section === section && link.band === null)
    .sort(byPriority);
  if (sectionFallback.length > 0) return sectionFallback[0];
  return defaultLinks()[0] ?? null;
}

/** Never show the same link twice on a page (§9). */
export function dedupeLinks<T extends ContentLink | null>(
  links: T[],
  alreadyShown: ContentLink[],
): T[] {
  const seen = new Set(alreadyShown.map((l) => l.url));
  return links.filter((link) => {
    if (!link) return false;
    if (seen.has(link.url)) return false;
    seen.add(link.url);
    return true;
  });
}
