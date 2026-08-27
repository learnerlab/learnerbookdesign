"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import instrumentJson from "@/config/instrument.json";
import { clearDraft, loadDraft, type QuizDraft } from "@/lib/draft";
import { readAttribution } from "@/components/AttributionCapture";

const version = instrumentJson.version;
const totalItems = instrumentJson.sections.reduce(
  (n, s) => n + s.items.length,
  0,
);

export default function FinishPage() {
  const router = useRouter();
  const [draft, setDraft] = useState<QuizDraft | null | "loading">("loading");
  const [firstName, setFirstName] = useState("");
  const [email, setEmail] = useState("");
  // Consent default is an open launch decision (§8 [FILL: confirm]) —
  // unchecked until Trevor decides, with EU/UK geo handling in phase 2.
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(loadDraft(version));
  }, []);

  if (draft === "loading") {
    return <div className="mx-auto max-w-xl px-5 py-16" aria-busy="true" />;
  }

  const complete =
    draft &&
    Object.keys(draft.answers).length >= totalItems &&
    draft.bonus_choice;

  if (!complete) {
    return (
      <div className="mx-auto max-w-xl px-5 py-16">
        <h1 className="font-display text-2xl font-semibold">
          Almost — a few questions are still open.
        </h1>
        <p className="mt-4">
          Your answers are saved on this device. Pick up where you left off.
        </p>
        <Link
          href="/quiz"
          className="mt-8 inline-block border border-ink bg-yellow px-8 py-4 text-lg font-semibold hover:brightness-95"
        >
          Back to the questions
        </Link>
      </div>
    );
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!draft || draft === "loading") return;
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answers: Object.entries(draft.answers).map(([item_id, value]) => ({
            item_id,
            value,
          })),
          bonus_choice: draft.bonus_choice,
          email: email.trim(),
          first_name: firstName.trim() || undefined,
          consent_newsletter: consent,
          utm: readAttribution(),
        }),
      });
      const data = (await response.json()) as { id?: string; error?: string };
      if (!response.ok || !data.id) {
        throw new Error(data.error ?? "Something went wrong. Try again.");
      }
      clearDraft(version);
      router.push(`/r/${data.id}`);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Something went wrong. Try again.",
      );
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-5 py-16">
      <h1 className="font-display text-3xl font-semibold leading-snug">
        Done. Where should we send your Learner Report?
      </h1>
      <p className="mt-3 text-ink-muted">
        Your results page is ready — the email is your permanent link to it.
      </p>
      <form onSubmit={submit} className="mt-8 flex flex-col gap-5">
        <label className="flex flex-col gap-1">
          <span className="text-sm text-ink-muted">First name (optional)</span>
          <input
            type="text"
            name="first_name"
            autoComplete="given-name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="border border-ink bg-transparent px-4 py-3 text-lg"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm text-ink-muted">Email</span>
          <input
            type="email"
            name="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-ink bg-transparent px-4 py-3 text-lg"
          />
        </label>
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1 h-5 w-5 accent-ink"
          />
          <span>Also send me The Learner Lab newsletter.</span>
        </label>
        {/* Phase 2: Cloudflare Turnstile widget renders here before submit. */}
        {error && (
          <p role="alert" className="border border-ink bg-yellow/30 px-4 py-3">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="border border-ink bg-yellow px-8 py-4 text-lg font-semibold hover:brightness-95 disabled:opacity-60"
        >
          {submitting ? "One second…" : "Show my results"}
        </button>
        <p className="text-sm text-ink-muted">
          We use your email to send this one report{" "}
          <Link href="/privacy" className="underline">
            (privacy)
          </Link>
          . The newsletter only comes if you check the box.
        </p>
      </form>
    </div>
  );
}
