// Phase 1 submit: validate, score server-side, persist to the local JSON
// store, return the results id. Phase 2 adds Postgres, Turnstile, rate
// limiting, Mailchimp, and the results email — the request/response contract
// stays the same.
import { NextResponse } from "next/server";
import { nanoid } from "nanoid";
import { z } from "zod";
import { bandsConfig, instrument, profilesConfig } from "@/lib/instrument";
import { scoreResponse } from "@/lib/scoring";
import { saveResponse } from "@/lib/store";

const submitSchema = z.object({
  answers: z
    .array(z.object({ item_id: z.string(), value: z.number().int() }))
    .min(1),
  bonus_choice: z.enum(["easy", "hard"]),
  email: z.string().email(),
  first_name: z.string().max(100).optional(),
  consent_newsletter: z.boolean(),
  utm: z.record(z.string(), z.string()).optional(),
});

export async function POST(request: Request) {
  let body: z.infer<typeof submitSchema>;
  try {
    body = submitSchema.parse(await request.json());
  } catch {
    return NextResponse.json(
      { error: "That submission didn't look right. Go back and try again." },
      { status: 400 },
    );
  }

  try {
    const scored = scoreResponse(
      instrument,
      body.answers,
      bandsConfig,
      profilesConfig,
    );
    const id = nanoid(12);
    saveResponse({
      id,
      created_at: new Date().toISOString(),
      instrument_version: instrument.version,
      answers: body.answers,
      bonus_choice: body.bonus_choice,
      first_name: body.first_name?.trim() || undefined,
      utm: body.utm,
      ...scored,
    });
    // Phase 1 stores no email anywhere — the subscribers table arrives with
    // the database in phase 2. Consent is collected so the UI is final.
    return NextResponse.json({ id });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Something went wrong.";
    return NextResponse.json(
      { error: `We couldn't score that: ${message}` },
      { status: 400 },
    );
  }
}
