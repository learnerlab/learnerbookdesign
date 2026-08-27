import { z } from "zod";
import instrumentJson from "@/config/instrument.json";
import bandsJson from "@/config/bands.json";
import profilesJson from "@/config/profiles.json";
import contentJson from "@/config/content.json";
import normsJson from "@/config/norms.json";

export const SECTION_KEYS = ["growth", "stress", "actions"] as const;
export type SectionKey = (typeof SECTION_KEYS)[number];

export const BEHAVIOR_KEYS = [
  "challenge",
  "arena",
  "feedback",
  "experiment",
  "reflect",
  "teach",
  "resources",
  "avoidance",
  "comfort",
] as const;
export type BehaviorKey = (typeof BEHAVIOR_KEYS)[number];

const directionSchema = z.enum(["higher_is_better", "lower_is_better"]);

const scaleOptionSchema = z.object({
  value: z.number().int(),
  label: z.string().min(1),
});

const scaleSchema = z
  .object({
    type: z.enum(["agreement", "frequency"]),
    options: z.array(scaleOptionSchema).min(2),
  })
  .refine(
    (scale) => {
      const values = scale.options.map((o) => o.value);
      return new Set(values).size === values.length;
    },
    { message: "scale option values must be unique" },
  );

const itemSchema = z.object({
  id: z.string().min(1),
  text: z.string().min(1),
  direction: directionSchema,
  behavior: z.enum(BEHAVIOR_KEYS).optional(),
  note: z.string().optional(),
});

const sectionSchema = z.object({
  key: z.enum(SECTION_KEYS),
  name: z.string().min(1),
  intro: z.string().min(1),
  scale: scaleSchema,
  items: z.array(itemSchema).min(1),
});

const bonusSchema = z.object({
  id: z.literal("bonus"),
  prompt: z.string().min(1),
  options: z
    .array(z.object({ key: z.enum(["easy", "hard"]), label: z.string().min(1) }))
    .length(2),
});

export const instrumentSchema = z
  .object({
    version: z.string().min(1),
    sections: z.array(sectionSchema).length(SECTION_KEYS.length),
    bonus: bonusSchema,
  })
  .refine(
    (instrument) => {
      const ids = instrument.sections.flatMap((s) => s.items.map((i) => i.id));
      return new Set(ids).size === ids.length;
    },
    { message: "item ids must be unique across the instrument" },
  );

export type Instrument = z.infer<typeof instrumentSchema>;
export type Section = z.infer<typeof sectionSchema>;
export type Item = z.infer<typeof itemSchema>;
export type Scale = z.infer<typeof scaleSchema>;
export type Direction = z.infer<typeof directionSchema>;

export const BAND_KEYS = ["low", "mid", "high"] as const;
export type BandKey = (typeof BAND_KEYS)[number];

export const bandsConfigSchema = z.object({
  bands: z
    .array(
      z.object({
        key: z.enum(BAND_KEYS),
        min: z.number().int().min(0),
        max: z.number().int().max(100),
        name: z.string().min(1),
      }),
    )
    .length(3),
});
export type BandsConfig = z.infer<typeof bandsConfigSchema>;

// Profile rules are data (§6): conditions present in `when` are ANDed;
// an empty `when` always matches, so the last profile is the catch-all.
export const profileRuleSchema = z.object({
  all_at_least: z.number().optional(),
  weakest: z.enum(SECTION_KEYS).optional(),
  others_mean_minus_weakest_at_least: z.number().optional(),
  min_scores: z.record(z.enum(SECTION_KEYS), z.number()).optional(),
});

export const profilesConfigSchema = z.object({
  profiles: z
    .array(
      z.object({
        key: z.string().min(1),
        name: z.string().min(1),
        when: profileRuleSchema,
      }),
    )
    .min(1),
});
export type ProfilesConfig = z.infer<typeof profilesConfigSchema>;
export type ProfileRule = z.infer<typeof profileRuleSchema>;

export const contentLinkSchema = z.object({
  title: z.string().min(1),
  url: z.string().min(1),
  format: z.enum(["video", "article", "podcast", "essay", "book-chapter"]),
  section: z.enum(SECTION_KEYS).nullable(),
  behavior: z.enum(BEHAVIOR_KEYS).nullable(),
  band: z.enum(BAND_KEYS).nullable(),
  priority: z.number().int(),
});
export const contentConfigSchema = z.array(contentLinkSchema);
export type ContentLink = z.infer<typeof contentLinkSchema>;

export const normsConfigSchema = z.object({ min_n: z.number().int().positive() });

// Parsed once at module load — a bad config fails the build, not a request.
export const instrument: Instrument = instrumentSchema.parse(instrumentJson);
export const bandsConfig: BandsConfig = bandsConfigSchema.parse(bandsJson);
export const profilesConfig: ProfilesConfig =
  profilesConfigSchema.parse(profilesJson);
export const contentConfig: ContentLink[] =
  contentConfigSchema.parse(contentJson);
export const normsConfig = normsConfigSchema.parse(normsJson);

export function sectionByKey(key: SectionKey): Section {
  const section = instrument.sections.find((s) => s.key === key);
  if (!section) throw new Error(`unknown section: ${key}`);
  return section;
}

export function allItems(): { section: Section; item: Item }[] {
  return instrument.sections.flatMap((section) =>
    section.items.map((item) => ({ section, item })),
  );
}
