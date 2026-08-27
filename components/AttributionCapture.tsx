"use client";

import { useEffect } from "react";

const KEY = "learner-score-attribution";
const UTM_PARAMS = ["utm_source", "utm_medium", "utm_campaign", "utm_content"];

/**
 * Captures UTM params + referrer on landing so they can travel with the
 * submission (§7.1). First touch wins within a browser.
 */
export function AttributionCapture() {
  useEffect(() => {
    try {
      if (localStorage.getItem(KEY)) return;
      const params = new URLSearchParams(window.location.search);
      const attribution: Record<string, string> = {};
      for (const key of UTM_PARAMS) {
        const value = params.get(key);
        if (value) attribution[key] = value.slice(0, 200);
      }
      if (document.referrer) {
        attribution.referrer = document.referrer.slice(0, 500);
      }
      if (Object.keys(attribution).length > 0) {
        localStorage.setItem(KEY, JSON.stringify(attribution));
      }
    } catch {
      // Storage unavailable (private mode etc.) — attribution is best-effort.
    }
  }, []);
  return null;
}

export function readAttribution(): Record<string, string> | undefined {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : undefined;
  } catch {
    return undefined;
  }
}
