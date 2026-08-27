// The quiz draft is the one thing allowed in localStorage (§2): answers so a
// refresh doesn't lose progress. Keyed by instrument version so a version
// bump silently discards stale drafts.
export type QuizDraft = {
  answers: Record<string, number>;
  bonus_choice?: "easy" | "hard";
  screen_index: number;
};

export function draftKey(version: string): string {
  return `learner-score-draft-v${version}`;
}

export function loadDraft(version: string): QuizDraft | null {
  try {
    const raw = localStorage.getItem(draftKey(version));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as QuizDraft;
    if (typeof parsed !== "object" || parsed === null) return null;
    return {
      answers: parsed.answers ?? {},
      bonus_choice: parsed.bonus_choice,
      screen_index: typeof parsed.screen_index === "number" ? parsed.screen_index : 0,
    };
  } catch {
    return null;
  }
}

export function saveDraft(version: string, draft: QuizDraft): void {
  try {
    localStorage.setItem(draftKey(version), JSON.stringify(draft));
  } catch {
    // Storage unavailable — the quiz still works, it just won't survive a refresh.
  }
}

export function clearDraft(version: string): void {
  try {
    localStorage.removeItem(draftKey(version));
  } catch {
    // ignore
  }
}
