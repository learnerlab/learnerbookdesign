import { describe, expect, it } from "vitest";
import {
  bandsConfig,
  instrument,
  instrumentSchema,
  profilesConfig,
  type Instrument,
} from "./instrument";
import {
  arithmeticMeanAggregator,
  bandFor,
  normalizeAnswer,
  profileFor,
  scoreResponse,
  validateAnswers,
  weakestSection,
  type Answer,
  type SectionScores,
} from "./scoring";

// A fixture with the same shape as the real instrument but fixed wording and
// directions, so numeric expectations here never depend on [FILL] content.
const fixture: Instrument = instrumentSchema.parse({
  version: "test",
  sections: [
    {
      key: "growth",
      name: "Growth mindset",
      intro: "intro",
      scale: {
        type: "agreement",
        options: [1, 2, 3, 4, 5, 6].map((value) => ({
          value,
          label: `label ${value}`,
        })),
      },
      items: ["g1", "g2", "g3"].map((id) => ({
        id,
        text: `${id} text`,
        direction: "higher_is_better",
      })),
    },
    {
      key: "stress",
      name: "Stress mindset",
      intro: "intro",
      scale: {
        type: "agreement",
        options: [0, 1, 2, 3, 4].map((value) => ({
          value,
          label: `label ${value}`,
        })),
      },
      items: ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"].map((id, i) => ({
        id,
        text: `${id} text`,
        direction: i % 2 === 0 ? "lower_is_better" : "higher_is_better",
      })),
    },
    {
      key: "actions",
      name: "Learner actions",
      intro: "intro",
      scale: {
        type: "frequency",
        options: [0, 1, 2, 3, 4].map((value) => ({
          value,
          label: `label ${value}`,
        })),
      },
      items: [
        { id: "a1", behavior: "challenge", direction: "higher_is_better" },
        { id: "a2", behavior: "arena", direction: "higher_is_better" },
        { id: "a3", behavior: "feedback", direction: "higher_is_better" },
        { id: "a4", behavior: "experiment", direction: "higher_is_better" },
        { id: "a5", behavior: "reflect", direction: "higher_is_better" },
        { id: "a6", behavior: "teach", direction: "higher_is_better" },
        { id: "a7", behavior: "resources", direction: "higher_is_better" },
        { id: "a8", behavior: "avoidance", direction: "lower_is_better" },
      ].map((item) => ({ ...item, text: `${item.id} text` })),
    },
  ],
  bonus: {
    id: "bonus",
    prompt: "Pick your bonus:",
    options: [
      { key: "easy", label: "easy" },
      { key: "hard", label: "hard" },
    ],
  },
});

const growthScale = fixture.sections[0].scale;
const stressScale = fixture.sections[1].scale;

/** Answers for the fixture: one flat value per section, plus per-item overrides. */
function answersFor(
  perSection: { growth: number; stress: number; actions: number },
  overrides: Record<string, number> = {},
): Answer[] {
  return fixture.sections.flatMap((section) =>
    section.items.map((item) => ({
      item_id: item.id,
      value: overrides[item.id] ?? perSection[section.key],
    })),
  );
}

function score(answers: Answer[]) {
  return scoreResponse(fixture, answers, bandsConfig, profilesConfig);
}

describe("normalizeAnswer", () => {
  it("maps the scale endpoints to 0 and 1 when higher is better", () => {
    expect(normalizeAnswer(1, growthScale, "higher_is_better")).toBe(0);
    expect(normalizeAnswer(6, growthScale, "higher_is_better")).toBe(1);
  });

  it("interpolates linearly between the endpoints", () => {
    expect(normalizeAnswer(2, stressScale, "higher_is_better")).toBeCloseTo(0.5);
    expect(normalizeAnswer(3, growthScale, "higher_is_better")).toBeCloseTo(0.4);
  });

  it("reverses when lower is better", () => {
    expect(normalizeAnswer(0, stressScale, "lower_is_better")).toBe(1);
    expect(normalizeAnswer(4, stressScale, "lower_is_better")).toBe(0);
    expect(normalizeAnswer(1, stressScale, "lower_is_better")).toBeCloseTo(0.75);
  });

  it("rejects values that are not on the scale", () => {
    expect(() => normalizeAnswer(7, growthScale, "higher_is_better")).toThrow();
    expect(() => normalizeAnswer(0.5, stressScale, "higher_is_better")).toThrow();
  });
});

describe("section scores", () => {
  it("scores a perfect learner at 100 everywhere", () => {
    // Growth: all 6 (max disagreement). Stress: enhancing items 4, debilitating 0.
    // Actions: everything very often except avoidance never.
    const result = score(
      answersFor(
        { growth: 6, stress: 4, actions: 4 },
        { s1: 0, s3: 0, s5: 0, s7: 0, a8: 0 },
      ),
    );
    expect(result.section_scores).toEqual({ growth: 100, stress: 100, actions: 100 });
    expect(result.overall_score).toBe(100);
  });

  it("scores the anti-learner at 0 everywhere", () => {
    const result = score(
      answersFor(
        { growth: 1, stress: 0, actions: 0 },
        { s1: 4, s3: 4, s5: 4, s7: 4, a8: 4 },
      ),
    );
    expect(result.section_scores).toEqual({ growth: 0, stress: 0, actions: 0 });
    expect(result.overall_score).toBe(0);
  });

  it("takes the mean of item scores within a section, stored at two decimals", () => {
    // Growth answers 6, 6, 1 → (1 + 1 + 0) / 3 = 66.67 after rounding.
    const result = score(
      answersFor(
        { growth: 6, stress: 4, actions: 4 },
        { g3: 1, s1: 0, s3: 0, s5: 0, s7: 0, a8: 0 },
      ),
    );
    expect(result.section_scores.growth).toBe(66.67);
  });

  it("handles reverse-scored items through direction, not special cases", () => {
    // All stress answers "strongly agree": the four enhancing items score 1,
    // the four debilitating items score 0 → section lands at 50.
    const result = score(answersFor({ growth: 6, stress: 4, actions: 4 }));
    expect(result.section_scores.stress).toBe(50);
  });
});

describe("overall score", () => {
  it("is the equal-weight arithmetic mean, rounded to a whole number", () => {
    expect(
      arithmeticMeanAggregator({ growth: 100, stress: 50, actions: 0 }),
    ).toBe(50);
    expect(
      arithmeticMeanAggregator({ growth: 66.67, stress: 50, actions: 25 }),
    ).toBe(47);
    expect(
      arithmeticMeanAggregator({ growth: 100, stress: 100, actions: 50.5 }),
    ).toBe(84); // 83.5 rounds up
  });
});

describe("weakest section", () => {
  it("picks the lowest-scoring section", () => {
    expect(weakestSection({ growth: 20, stress: 60, actions: 80 })).toBe("growth");
  });

  it("breaks a full tie toward actions", () => {
    expect(weakestSection({ growth: 50, stress: 50, actions: 50 })).toBe("actions");
  });

  it("breaks a stress/growth tie toward stress", () => {
    expect(weakestSection({ growth: 40, stress: 40, actions: 80 })).toBe("stress");
  });

  it("breaks an actions/growth tie toward actions", () => {
    expect(weakestSection({ growth: 30, stress: 90, actions: 30 })).toBe("actions");
  });
});

describe("bands", () => {
  it("uses the config thresholds", () => {
    expect(bandFor(0, bandsConfig)).toBe("low");
    expect(bandFor(49, bandsConfig)).toBe("low");
    expect(bandFor(50, bandsConfig)).toBe("mid");
    expect(bandFor(74, bandsConfig)).toBe("mid");
    expect(bandFor(75, bandsConfig)).toBe("high");
    expect(bandFor(100, bandsConfig)).toBe("high");
  });

  it("bands by the displayed whole number, so 49.6 is mid", () => {
    expect(bandFor(49.6, bandsConfig)).toBe("mid");
    expect(bandFor(74.5, bandsConfig)).toBe("high");
    expect(bandFor(49.4, bandsConfig)).toBe("low");
  });
});

describe("profiles", () => {
  function profile(sectionScores: SectionScores) {
    return profileFor(sectionScores, weakestSection(sectionScores), profilesConfig);
  }

  it("learner_mode when all three sections are at least 70", () => {
    expect(profile({ growth: 70, stress: 70, actions: 70 })).toBe("learner_mode");
    expect(profile({ growth: 95, stress: 80, actions: 71 })).toBe("learner_mode");
  });

  it("believer when actions lags the mindsets by 15 or more", () => {
    expect(profile({ growth: 80, stress: 70, actions: 55 })).toBe("believer");
    // Gap of exactly 15 counts.
    expect(profile({ growth: 70, stress: 60, actions: 50 })).toBe("believer");
  });

  it("grinder when stress is weakest but the reps are there", () => {
    expect(profile({ growth: 75, stress: 40, actions: 65 })).toBe("grinder");
    expect(profile({ growth: 75, stress: 40, actions: 60 })).toBe("grinder");
  });

  it("doubter when growth is weakest", () => {
    expect(profile({ growth: 30, stress: 60, actions: 55 })).toBe("doubter");
  });

  it("builder for everything else", () => {
    // Actions weakest but the gap is under 15.
    expect(profile({ growth: 65, stress: 60, actions: 55 })).toBe("builder");
    // Stress weakest and actions under 60.
    expect(profile({ growth: 65, stress: 40, actions: 50 })).toBe("builder");
  });

  it("evaluates top to bottom, so learner_mode beats doubter", () => {
    // Growth is weakest but everything is ≥ 70 → learner_mode wins.
    expect(profile({ growth: 72, stress: 90, actions: 85 })).toBe("learner_mode");
  });
});

describe("behavior scores", () => {
  it("scores each action item 0–100 with direction handled", () => {
    const result = score(
      answersFor(
        { growth: 6, stress: 4, actions: 2 },
        { a1: 4, a3: 0, a8: 4 }, // a8 reversed: "very often avoided" → 0
      ),
    );
    expect(result.behavior_scores.challenge).toBe(100);
    expect(result.behavior_scores.feedback).toBe(0);
    expect(result.behavior_scores.avoidance).toBe(0);
    expect(result.behavior_scores.arena).toBe(50);
  });

  it("flags the two lowest behaviors, config order breaking ties", () => {
    const result = score(
      answersFor(
        { growth: 6, stress: 4, actions: 4 },
        { a3: 0, a5: 1, a8: 0 }, // avoidance reversed → 100, not low
      ),
    );
    expect(result.lowest_behaviors).toEqual(["feedback", "reflect"]);
  });
});

describe("answer validation", () => {
  const complete = answersFor({ growth: 3, stress: 2, actions: 2 });

  it("accepts a complete answer set", () => {
    expect(() => validateAnswers(fixture, complete)).not.toThrow();
  });

  it("rejects a missing answer", () => {
    expect(() =>
      validateAnswers(fixture, complete.slice(0, -1)),
    ).toThrow(/missing answer/);
  });

  it("rejects duplicate answers", () => {
    expect(() =>
      validateAnswers(fixture, [...complete, { item_id: "g1", value: 2 }]),
    ).toThrow(/duplicate/);
  });

  it("rejects values off the item's scale", () => {
    const bad = complete.map((a) =>
      a.item_id === "a1" ? { ...a, value: 6 } : a,
    );
    expect(() => validateAnswers(fixture, bad)).toThrow(/not on the scale/);
  });

  it("rejects answers for unknown items", () => {
    expect(() =>
      validateAnswers(fixture, [...complete, { item_id: "zz", value: 1 }]),
    ).toThrow(/unknown items/);
  });
});

describe("the real config", () => {
  it("parses and has the expected shape", () => {
    expect(instrument.version).toBe("1.0");
    expect(instrument.sections.map((s) => s.key)).toEqual([
      "growth",
      "stress",
      "actions",
    ]);
    expect(instrument.sections[0].items).toHaveLength(3);
    expect(instrument.sections[1].items).toHaveLength(8);
    expect(instrument.sections[2].items).toHaveLength(8);
  });

  it("scores a full response end to end", () => {
    const answers = instrument.sections.flatMap((section) =>
      section.items.map((item, i) => ({
        item_id: item.id,
        value: section.scale.options[i % section.scale.options.length].value,
      })),
    );
    const result = scoreResponse(instrument, answers, bandsConfig, profilesConfig);
    for (const key of ["growth", "stress", "actions"] as const) {
      expect(result.section_scores[key]).toBeGreaterThanOrEqual(0);
      expect(result.section_scores[key]).toBeLessThanOrEqual(100);
    }
    expect(Number.isInteger(result.overall_score)).toBe(true);
    expect(result.lowest_behaviors).toHaveLength(2);
    expect(result.profile).toBeTruthy();
  });
});
