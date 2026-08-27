import Link from "next/link";
import { notFound } from "next/navigation";
import { LearnerShape } from "@/components/LearnerShape";
import { ShareButtons } from "@/components/ShareButtons";
import { behaviorLink, dedupeLinks, opportunityLinks } from "@/lib/content";
import { loadCopy } from "@/lib/copy";
import {
  bandsConfig,
  profilesConfig,
  sectionByKey,
  SECTION_KEYS,
  type BandKey,
  type BehaviorKey,
  type ContentLink,
} from "@/lib/instrument";
import { getResponse } from "@/lib/store";

export const dynamic = "force-dynamic";

export const metadata = { title: "Your Learner Report" };

function bandName(key: BandKey): string {
  return bandsConfig.bands.find((b) => b.key === key)!.name;
}

function CopyParagraphs({ name }: { name: string }) {
  const copy = loadCopy(name);
  return (
    <>
      {copy.paragraphs.map((paragraph, i) => (
        <p key={i} className="mt-2 leading-relaxed">
          {paragraph}
        </p>
      ))}
    </>
  );
}

function ContentLinkItem({ link }: { link: ContentLink }) {
  return (
    <li>
      <a href={link.url} className="underline hover:text-ink-muted">
        {link.title}
      </a>{" "}
      <span className="text-sm text-ink-muted">({link.format})</span>
    </li>
  );
}

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const response = getResponse(id);
  if (!response) notFound();

  const sectionNames = Object.fromEntries(
    SECTION_KEYS.map((key) => [key, sectionByKey(key).name]),
  ) as Record<(typeof SECTION_KEYS)[number], string>;

  const profile = profilesConfig.profiles.find(
    (p) => p.key === response.profile,
  );

  // Behavior bars, lowest first (§7.3.4). Labels come from the copy bank.
  const behaviors = (
    Object.entries(response.behavior_scores) as [BehaviorKey, number][]
  ).sort((a, b) => a[1] - b[1]);

  const oppLinks = opportunityLinks(
    response.weakest,
    response.bands[response.weakest],
  );
  const repLinks = dedupeLinks(
    response.lowest_behaviors.map((key) => behaviorLink(key)),
    oppLinks,
  );

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
  const shareUrl = `${siteUrl}/r/${response.id}`;

  return (
    <article className="mx-auto w-full max-w-2xl px-5 py-12">
      {/* 1 — the number */}
      <header className="text-center">
        <p className="text-sm uppercase tracking-wide text-ink-muted">
          Your Learner Score
        </p>
        <p className="font-display text-8xl font-semibold leading-none">
          {response.overall_score}
        </p>
        <p className="mt-2 text-lg text-ink-muted">
          {bandName(response.bands.overall)}
        </p>
      </header>

      {/* 2 — the shape */}
      <section className="mt-12">
        <LearnerShape
          scores={response.section_scores}
          labels={sectionNames}
          weakest={response.weakest}
        />
      </section>

      {/* 3 — three measures */}
      <section className="mt-12 space-y-8">
        {SECTION_KEYS.map((key) => (
          <div key={key} className="border-t border-rule pt-6">
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-xl font-semibold">
                {sectionNames[key]}
              </h2>
              <p>
                <span className="font-display text-2xl font-semibold">
                  {Math.round(response.section_scores[key])}
                </span>{" "}
                <span className="text-sm text-ink-muted">
                  · {bandName(response.bands[key])}
                </span>
              </p>
            </div>
            <CopyParagraphs name={`${key}-${response.bands[key]}`} />
          </div>
        ))}
      </section>

      {/* 4 — your reps */}
      <section className="mt-12 border-t border-rule pt-6">
        <h2 className="font-display text-xl font-semibold">Your reps</h2>
        <p className="mt-1 text-sm text-ink-muted">
          The eight learner actions from the last 30 days, lowest first.
        </p>
        <ul className="mt-6 space-y-4">
          {behaviors.map(([key, score], index) => {
            const label = loadCopy(`behavior-${key}`).title ?? key;
            const flagged = response.lowest_behaviors.includes(key);
            const link = flagged
              ? repLinks[response.lowest_behaviors.indexOf(key)]
              : undefined;
            return (
              <li key={key}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span>{label}</span>
                  <span className="text-ink-muted">{Math.round(score)}</span>
                </div>
                <div className="mt-1 h-2 w-full border border-ink/40">
                  <div
                    className={`h-full ${index < 2 ? "bg-yellow" : "bg-ink/70"}`}
                    style={{ width: `${Math.max(2, score)}%` }}
                  />
                </div>
                {flagged && (
                  <p className="mt-1 text-sm">
                    <span className="font-hand text-lg">add this rep</span>
                    {link && (
                      <>
                        {" — "}
                        <a href={link.url} className="underline">
                          {link.title}
                        </a>
                      </>
                    )}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      </section>

      {/* 5 — biggest opportunity */}
      <section className="mt-12 border border-ink p-6">
        <h2 className="font-display text-xl font-semibold">
          Your biggest opportunity: {sectionNames[response.weakest].toLowerCase()}
        </h2>
        {profile && (
          <p className="mt-2 text-sm uppercase tracking-wide text-ink-muted">
            Profile: {profile.name}
          </p>
        )}
        <CopyParagraphs name={`profile-${response.profile}`} />
        {oppLinks.length > 0 && (
          <>
            <h3 className="mt-5 text-sm font-semibold uppercase tracking-wide text-ink-muted">
              Start here
            </h3>
            <ul className="mt-2 space-y-1">
              {oppLinks.map((link) => (
                <ContentLinkItem key={link.url} link={link} />
              ))}
            </ul>
          </>
        )}
      </section>

      {/* 6 — the bonus */}
      <section className="mt-12 border-t border-rule pt-6">
        <h2 className="font-display text-xl font-semibold">
          {loadCopy(`bonus-${response.bonus_choice}`).title ?? "Your bonus"}
        </h2>
        <CopyParagraphs name={`bonus-${response.bonus_choice}`} />
        <p className="mt-3 text-sm text-ink-muted">
          {response.bonus_choice === "hard"
            ? "You picked the hard one. People who do that tend to be the ones already doing the reps."
            : "You picked the quick tips. No judgment — just notice which one you'd have picked on your best day."}
        </p>
      </section>

      {/* 7 — share */}
      <section className="mt-12 border-t border-rule pt-6">
        <h2 className="font-display text-xl font-semibold">Share your shape</h2>
        <div className="mt-4">
          <ShareButtons url={shareUrl} score={response.overall_score} />
        </div>
      </section>

      {/* 8 — retake */}
      <section className="mt-12 border-t border-rule pt-6 text-sm text-ink-muted">
        <p>
          Scores move — that's the whole premise. Retake this in 30 days and
          your report will show what changed.
        </p>
        <p className="mt-2">
          <Link href="/quiz" className="underline">
            Retake in 30 days
          </Link>
        </p>
      </section>
    </article>
  );
}
