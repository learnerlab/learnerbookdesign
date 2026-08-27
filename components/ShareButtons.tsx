"use client";

import { useState } from "react";

export function ShareButtons({ url, score }: { url: string; score: number }) {
  const [copied, setCopied] = useState(false);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.prompt("Copy your link:", url);
    }
  }

  const text = `My Learner Score is ${score}/100. Three minutes, worth it:`;
  const encodedUrl = encodeURIComponent(url);

  const linkClass =
    "border border-ink px-4 py-2 text-sm hover:bg-yellow/30 text-center";

  return (
    <div className="flex flex-wrap gap-2">
      <a
        href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClass}
      >
        Share on LinkedIn
      </a>
      <a
        href={`https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodeURIComponent(text)}`}
        target="_blank"
        rel="noopener noreferrer"
        className={linkClass}
      >
        Share on X
      </a>
      <button type="button" onClick={copyLink} className={linkClass}>
        {copied ? "Copied" : "Copy link"}
      </button>
    </div>
  );
}
