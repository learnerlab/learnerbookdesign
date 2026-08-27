import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Learner Score — a 3-minute self-assessment by The Learner Lab",
  description:
    "Answer 24 quick questions and get your Learner Score: how you think about ability, how you think about stress, and whether you're doing the reps.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Caveat:wght@500&family=Fraunces:opsz,wght@9..144,400;9..144,600&family=Libre+Franklin:ital,wght@0,400;0,500;0,600;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="flex min-h-screen flex-col">
        <header className="border-b border-rule">
          <div className="mx-auto flex w-full max-w-2xl items-baseline justify-between px-5 py-4">
            <Link href="/" className="font-display text-lg font-semibold">
              Learner Score
            </Link>
            <a
              href="https://thelearnerlab.com"
              className="text-sm text-ink-muted hover:text-ink"
            >
              by The Learner Lab
            </a>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-rule">
          <div className="mx-auto w-full max-w-2xl space-y-2 px-5 py-6 text-xs text-ink-muted">
            <p>
              Growth mindset items adapted from Dweck, C. S. (2006).{" "}
              <em>Mindset: The New Psychology of Success.</em> Random House.
              Scale distributed by Stanford SPARQ.
            </p>
            <p>
              Stress mindset items: Crum, A. J., Salovey, P., &amp; Achor, S.
              (2013). Rethinking stress: The role of mindsets in determining the
              stress response.{" "}
              <em>Journal of Personality and Social Psychology, 104</em>(4),
              716.
            </p>
            <p>Learner actions developed by The Learner Lab.</p>
            <p>
              <Link href="/privacy" className="underline hover:text-ink">
                Privacy
              </Link>{" "}
              ·{" "}
              <a
                href="https://thelearnerlab.com"
                className="underline hover:text-ink"
              >
                The Learner Lab
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
