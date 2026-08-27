import Link from "next/link";
import { AttributionCapture } from "@/components/AttributionCapture";

export default function LandingPage() {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col px-5 py-16 sm:py-24">
      <AttributionCapture />
      <h1 className="font-display text-4xl font-semibold leading-tight sm:text-5xl">
        How good are you at getting better?
      </h1>
      <p className="mt-6 max-w-prose text-lg leading-relaxed">
        Answer 24 quick questions — about how you think about ability, how you
        think about stress, and what you actually did in the last 30 days — and
        get your Learner Score, with a picture of where you're strong and the
        one place to work next.
      </p>
      <ul className="mt-6 space-y-1 text-ink-muted">
        <li>3 minutes, one question at a time.</li>
        <li>Built on published mindset research.</li>
        <li>Free, from The Learner Lab.</li>
      </ul>
      <div className="mt-10">
        <Link
          href="/quiz"
          className="inline-block rounded-none border border-ink bg-yellow px-8 py-4 text-lg font-semibold hover:brightness-95"
        >
          Start
        </Link>
      </div>
      <p className="mt-4 text-sm text-ink-muted">
        No email needed to take it. You'll get your Learner Report at the end.
      </p>
    </div>
  );
}
