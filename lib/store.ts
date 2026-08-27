// Phase 1 response store: seed data plus a local JSON file for new
// submissions. Replaced by Postgres (Drizzle) in phase 2 — keep the read/write
// interface, swap the backing.
import fs from "node:fs";
import path from "node:path";
import type { Answer, ScoredResponse } from "./scoring";

export type StoredResponse = ScoredResponse & {
  id: string;
  created_at: string;
  instrument_version: string;
  answers: Answer[];
  bonus_choice: "easy" | "hard";
  first_name?: string;
  utm?: Record<string, string>;
};

const SEED_PATH = path.join(process.cwd(), "data", "seed-responses.json");
const LOCAL_PATH = path.join(process.cwd(), "data", "responses.local.json");

let seedCache: Map<string, StoredResponse> | null = null;

function seedResponses(): Map<string, StoredResponse> {
  if (!seedCache) {
    seedCache = new Map();
    if (fs.existsSync(SEED_PATH)) {
      const parsed = JSON.parse(fs.readFileSync(SEED_PATH, "utf8")) as {
        responses: StoredResponse[];
      };
      for (const response of parsed.responses) {
        seedCache.set(response.id, response);
      }
    }
  }
  return seedCache;
}

function localResponses(): StoredResponse[] {
  if (!fs.existsSync(LOCAL_PATH)) return [];
  try {
    return JSON.parse(fs.readFileSync(LOCAL_PATH, "utf8")) as StoredResponse[];
  } catch {
    return [];
  }
}

export function getResponse(id: string): StoredResponse | null {
  // Never derive scores here: everything on a results page comes from what
  // was computed and stored at submit time (§5).
  const local = localResponses().find((r) => r.id === id);
  return local ?? seedResponses().get(id) ?? null;
}

export function saveResponse(response: StoredResponse): void {
  const all = localResponses();
  all.push(response);
  fs.mkdirSync(path.dirname(LOCAL_PATH), { recursive: true });
  fs.writeFileSync(LOCAL_PATH, JSON.stringify(all, null, 1));
}

export function anySeedId(): string | null {
  const first = seedResponses().keys().next();
  return first.done ? null : first.value;
}
