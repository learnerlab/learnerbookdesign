// Scoring per CLAUDE.md §5. Server-side only — never import from client components.
import type {
  BandKey,
  BandsConfig,
  BehaviorKey,
  Direction,
  Instrument,
  ProfileRule,
  ProfilesConfig,
  Scale,
  SectionKey,
} from "./instrument";
import { SECTION_KEYS } from "./instrument";

export type Answer = { item_id: string; value: number };

export type SectionScores = Record<SectionKey, number>;

export type ScoredResponse = {
  section_scores: SectionScores; // 0–100, two decimals
  overall_score: number; // whole number
  weakest: SectionKey;
  behavior_scores: Partial<Record<BehaviorKey, number>>; // 0–100
  lowest_behaviors: BehaviorKey[]; // the two lowest
  bands: Record<SectionKey | "overall", BandKey>;
  profile: string;
};

// Bias toward the most actionable content when sections tie for weakest (§5).
const WEAKEST_TIE_BREAK: SectionKey[] = ["actions", "stress", "growth"];

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

function mean(values: number[]): number {
  if (values.length === 0) throw new Error("mean of empty list");
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function scaleBounds(scale: Scale): { min: number; max: number } {
  const values = scale.options.map((o) => o.value);
  return { min: Math.min(...values), max: Math.max(...values) };
}

/** Normalize a raw answer to 0–1 "toward learner". */
export function normalizeAnswer(
  value: number,
  scale: Scale,
  direction: Direction,
): number {
  const { min, max } = scaleBounds(scale);
  if (!scale.options.some((o) => o.value === value)) {
    throw new Error(`answer value ${value} is not on the scale`);
  }
  const n = (value - min) / (max - min);
  return direction === "lower_is_better" ? 1 - n : n;
}

/**
 * The v1 aggregator: equal-weight arithmetic mean, rounded to a whole number.
 * Kept as one swappable function so a geometric-mean "Learner Score 2.0"
 * can slot in later without touching anything else (§5).
 */
export type OverallAggregator = (sectionScores: SectionScores) => number;

export const arithmeticMeanAggregator: OverallAggregator = (sectionScores) =>
  Math.round(mean(SECTION_KEYS.map((k) => sectionScores[k])));

/** Band a score by its displayed (whole-number) value. */
export function bandFor(score: number, bandsConfig: BandsConfig): BandKey {
  const rounded = Math.round(score);
  const band = bandsConfig.bands.find(
    (b) => rounded >= b.min && rounded <= b.max,
  );
  if (!band) throw new Error(`no band covers score ${score}`);
  return band.key;
}

export function weakestSection(sectionScores: SectionScores): SectionKey {
  return WEAKEST_TIE_BREAK.reduce((weakest, key) =>
    sectionScores[key] < sectionScores[weakest] ? key : weakest,
  );
}

function ruleMatches(
  rule: ProfileRule,
  sectionScores: SectionScores,
  weakest: SectionKey,
): boolean {
  if (
    rule.all_at_least !== undefined &&
    !SECTION_KEYS.every((k) => sectionScores[k] >= rule.all_at_least!)
  ) {
    return false;
  }
  if (rule.weakest !== undefined && weakest !== rule.weakest) {
    return false;
  }
  if (rule.others_mean_minus_weakest_at_least !== undefined) {
    const others = SECTION_KEYS.filter((k) => k !== weakest).map(
      (k) => sectionScores[k],
    );
    if (
      mean(others) - sectionScores[weakest] <
      rule.others_mean_minus_weakest_at_least
    ) {
      return false;
    }
  }
  if (rule.min_scores !== undefined) {
    for (const [key, min] of Object.entries(rule.min_scores)) {
      if (sectionScores[key as SectionKey] < min) return false;
    }
  }
  return true;
}

/** Evaluated top to bottom, first match wins (§6). */
export function profileFor(
  sectionScores: SectionScores,
  weakest: SectionKey,
  profilesConfig: ProfilesConfig,
): string {
  for (const profile of profilesConfig.profiles) {
    if (ruleMatches(profile.when, sectionScores, weakest)) return profile.key;
  }
  throw new Error("no profile matched — profiles.json must end in a catch-all");
}

/** Every item answered exactly once, with a value that is on its scale. */
export function validateAnswers(
  instrument: Instrument,
  answers: Answer[],
): void {
  const byId = new Map<string, number>();
  for (const answer of answers) {
    if (byId.has(answer.item_id)) {
      throw new Error(`duplicate answer for item ${answer.item_id}`);
    }
    byId.set(answer.item_id, answer.value);
  }
  for (const section of instrument.sections) {
    for (const item of section.items) {
      const value = byId.get(item.id);
      if (value === undefined) {
        throw new Error(`missing answer for item ${item.id}`);
      }
      if (!section.scale.options.some((o) => o.value === value)) {
        throw new Error(`answer value ${value} for ${item.id} is not on the scale`);
      }
      byId.delete(item.id);
    }
  }
  if (byId.size > 0) {
    throw new Error(`answers for unknown items: ${[...byId.keys()].join(", ")}`);
  }
}

export function scoreResponse(
  instrument: Instrument,
  answers: Answer[],
  bandsConfig: BandsConfig,
  profilesConfig: ProfilesConfig,
  aggregator: OverallAggregator = arithmeticMeanAggregator,
): ScoredResponse {
  validateAnswers(instrument, answers);
  const valueById = new Map(answers.map((a) => [a.item_id, a.value]));

  const sectionScores = {} as SectionScores;
  const behaviorScores: Partial<Record<BehaviorKey, number>> = {};
  const behaviorOrder: BehaviorKey[] = [];

  for (const section of instrument.sections) {
    const normalized = section.items.map((item) => {
      const n = normalizeAnswer(
        valueById.get(item.id)!,
        section.scale,
        item.direction,
      );
      if (item.behavior) {
        behaviorScores[item.behavior] = round2(n * 100);
        behaviorOrder.push(item.behavior);
      }
      return n;
    });
    sectionScores[section.key] = round2(mean(normalized) * 100);
  }

  const weakest = weakestSection(sectionScores);
  const lowestBehaviors = [...behaviorOrder]
    .sort((a, b) => behaviorScores[a]! - behaviorScores[b]!) // stable: config order breaks ties
    .slice(0, 2);

  const overall = aggregator(sectionScores);

  return {
    section_scores: sectionScores,
    overall_score: overall,
    weakest,
    behavior_scores: behaviorScores,
    lowest_behaviors: lowestBehaviors,
    bands: {
      growth: bandFor(sectionScores.growth, bandsConfig),
      stress: bandFor(sectionScores.stress, bandsConfig),
      actions: bandFor(sectionScores.actions, bandsConfig),
      overall: bandFor(overall, bandsConfig),
    },
    profile: profileFor(sectionScores, weakest, profilesConfig),
  };
}
