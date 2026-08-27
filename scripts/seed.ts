// Phase 1 seed data: 500 realistic fake responses written to a local JSON
// file (no database yet). Mindsets skew high, actions spread lower (§13).
// Deterministic: same seed → same file.
import fs from "node:fs";
import path from "node:path";
import { bandsConfig, instrument, profilesConfig } from "../lib/instrument";
import { scoreResponse, type Answer } from "../lib/scoring";

const COUNT = 500;
const SEED = 20260827;
const OUT_PATH = path.join(process.cwd(), "data", "seed-responses.json");

// mulberry32 — small deterministic PRNG, plenty for fake data.
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(SEED);

function clamp01(n: number): number {
  return Math.min(1, Math.max(0, n));
}

// Sum of uniforms ≈ normal, shifted to a target mean.
function latent(mean: number, spread: number): number {
  const noise = (rand() + rand() + rand()) / 3 - 0.5;
  return clamp01(mean + noise * spread * 2);
}

const ID_ALPHABET =
  "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_";

function seededId(length = 12): string {
  let id = "";
  for (let i = 0; i < length; i++) {
    id += ID_ALPHABET[Math.floor(rand() * ID_ALPHABET.length)];
  }
  return id;
}

// Per-section population shape: mindsets skew high, actions lower and wider.
const SECTION_LATENTS = {
  growth: { mean: 0.68, spread: 0.35 },
  stress: { mean: 0.58, spread: 0.4 },
  actions: { mean: 0.45, spread: 0.55 },
} as const;

function answerFor(
  trait: number,
  scaleValues: number[],
  direction: "higher_is_better" | "lower_is_better",
): number {
  // Item-level noise around the person's trait, then map 0–1 "toward
  // learner" back onto the raw scale respecting the item's direction.
  const n = clamp01(trait + (rand() - 0.5) * 0.45);
  const min = Math.min(...scaleValues);
  const max = Math.max(...scaleValues);
  const towardLearnerRaw =
    direction === "higher_is_better"
      ? min + n * (max - min)
      : max - n * (max - min);
  return Math.round(towardLearnerRaw);
}

type SeedResponse = ReturnType<typeof scoreResponse> & {
  id: string;
  created_at: string;
  instrument_version: string;
  answers: Answer[];
  bonus_choice: "easy" | "hard";
};

const responses: SeedResponse[] = [];
const usedIds = new Set<string>();
// Fixed base date so the output is stable; timestamps spread over ~60 days.
const baseTime = Date.parse("2026-08-01T12:00:00Z");

for (let i = 0; i < COUNT; i++) {
  const traits = {
    growth: latent(SECTION_LATENTS.growth.mean, SECTION_LATENTS.growth.spread),
    stress: latent(SECTION_LATENTS.stress.mean, SECTION_LATENTS.stress.spread),
    actions: latent(
      SECTION_LATENTS.actions.mean,
      SECTION_LATENTS.actions.spread,
    ),
  };

  const answers: Answer[] = instrument.sections.flatMap((section) =>
    section.items.map((item) => ({
      item_id: item.id,
      value: answerFor(
        traits[section.key],
        section.scale.options.map((o) => o.value),
        item.direction,
      ),
    })),
  );

  const scored = scoreResponse(instrument, answers, bandsConfig, profilesConfig);

  // Challenge-seekers pick the hard bonus more often — mirrors the validity
  // check the admin dashboard will run (§4.5).
  const bonusChoice = rand() < 0.2 + 0.5 * traits.actions ? "hard" : "easy";

  let id = seededId();
  while (usedIds.has(id)) id = seededId();
  usedIds.add(id);

  responses.push({
    id,
    created_at: new Date(
      baseTime - Math.floor(rand() * 60 * 24 * 60 * 60 * 1000),
    ).toISOString(),
    instrument_version: instrument.version,
    answers,
    section_scores: scored.section_scores,
    overall_score: scored.overall_score,
    behavior_scores: scored.behavior_scores,
    weakest: scored.weakest,
    lowest_behaviors: scored.lowest_behaviors,
    bands: scored.bands,
    profile: scored.profile,
    bonus_choice: bonusChoice,
  });
}

fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
fs.writeFileSync(OUT_PATH, JSON.stringify({ responses }, null, 1) + "\n");

const meanOf = (key: "growth" | "stress" | "actions") =>
  responses.reduce((sum, r) => sum + r.section_scores[key], 0) / COUNT;
console.log(`wrote ${COUNT} responses to ${path.relative(process.cwd(), OUT_PATH)}`);
console.log(
  `means — growth ${meanOf("growth").toFixed(1)}, stress ${meanOf(
    "stress",
  ).toFixed(1)}, actions ${meanOf("actions").toFixed(1)}`,
);
const byProfile = responses.reduce<Record<string, number>>((acc, r) => {
  acc[r.profile] = (acc[r.profile] ?? 0) + 1;
  return acc;
}, {});
console.log("profiles:", byProfile);
console.log(
  "sample ids:",
  responses.slice(0, 5).map((r) => r.id),
);
