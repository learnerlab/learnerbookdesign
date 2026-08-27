"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { Instrument, Item, Scale, Section } from "@/lib/instrument";
import { loadDraft, saveDraft, type QuizDraft } from "@/lib/draft";

type Screen =
  | { type: "intro"; section: Section }
  | { type: "item"; section: Section; item: Item; itemNumber: number }
  | { type: "bonus" };

function buildScreens(instrument: Instrument): Screen[] {
  const screens: Screen[] = [];
  let itemNumber = 0;
  for (const section of instrument.sections) {
    screens.push({ type: "intro", section });
    for (const item of section.items) {
      itemNumber += 1;
      screens.push({ type: "item", section, item, itemNumber });
    }
  }
  screens.push({ type: "bonus" });
  return screens;
}

export function QuizApp({ instrument }: { instrument: Instrument }) {
  const router = useRouter();
  const screens = useMemo(() => buildScreens(instrument), [instrument]);
  const totalItems = useMemo(
    () => instrument.sections.reduce((n, s) => n + s.items.length, 0),
    [instrument],
  );

  const [screenIndex, setScreenIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore a saved draft once on mount so a refresh doesn't lose progress.
  useEffect(() => {
    const draft = loadDraft(instrument.version);
    if (draft && Object.keys(draft.answers).length > 0) {
      setAnswers(draft.answers);
      setScreenIndex(Math.min(draft.screen_index, screens.length - 1));
    }
  }, [instrument.version, screens.length]);

  const persist = useCallback(
    (next: Partial<QuizDraft> & { screen_index: number }) => {
      saveDraft(instrument.version, {
        answers,
        ...next,
      });
    },
    [instrument.version, answers],
  );

  const goTo = useCallback(
    (index: number) => {
      const clamped = Math.max(0, Math.min(index, screens.length - 1));
      setScreenIndex(clamped);
      persist({ screen_index: clamped });
    },
    [screens.length, persist],
  );

  const screen = screens[screenIndex];

  const answerItem = useCallback(
    (item: Item, value: number) => {
      const nextAnswers = { ...answers, [item.id]: value };
      setAnswers(nextAnswers);
      const nextIndex = Math.min(screenIndex + 1, screens.length - 1);
      saveDraft(instrument.version, {
        answers: nextAnswers,
        screen_index: nextIndex,
      });
      // A beat of selected-state feedback before the next question.
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      advanceTimer.current = setTimeout(() => setScreenIndex(nextIndex), 160);
    },
    [answers, screenIndex, screens.length, instrument.version],
  );

  const chooseBonus = useCallback(
    (choice: "easy" | "hard") => {
      saveDraft(instrument.version, {
        answers,
        bonus_choice: choice,
        screen_index: screenIndex,
      });
      router.push("/quiz/finish");
    },
    [answers, screenIndex, instrument.version, router],
  );

  // Keyboard: 1–6 answers the current question (§7.1).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      if (screen.type === "item") {
        const index = Number.parseInt(event.key, 10) - 1;
        if (index >= 0 && index < screen.section.scale.options.length) {
          answerItem(screen.item, screen.section.scale.options[index].value);
        }
      } else if (screen.type === "intro" && event.key === "Enter") {
        goTo(screenIndex + 1);
      } else if (screen.type === "bonus") {
        if (event.key === "1" || event.key.toLowerCase() === "a") chooseBonus("easy");
        if (event.key === "2" || event.key.toLowerCase() === "b") chooseBonus("hard");
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [screen, screenIndex, answerItem, chooseBonus, goTo]);

  useEffect(
    () => () => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
    },
    [],
  );

  const answeredCount = Object.keys(answers).length;
  const progress = Math.min(1, answeredCount / (totalItems + 1));

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col px-5 pb-16">
      <div
        role="progressbar"
        aria-label="Quiz progress"
        aria-valuemin={0}
        aria-valuemax={totalItems + 1}
        aria-valuenow={answeredCount}
        className="mt-2 h-px w-full bg-rule"
      >
        <div
          className="h-px bg-ink transition-[width] duration-300"
          style={{ width: `${progress * 100}%` }}
        />
      </div>

      <div className="flex min-h-[65vh] flex-col justify-center py-8">
        {screen.type === "intro" && (
          <div>
            <p className="text-sm uppercase tracking-wide text-ink-muted">
              {screen.section.name}
            </p>
            <h2 className="mt-3 font-display text-2xl font-semibold leading-snug sm:text-3xl">
              {screen.section.intro}
            </h2>
            <button
              type="button"
              onClick={() => goTo(screenIndex + 1)}
              className="mt-8 border border-ink bg-yellow px-8 py-4 text-lg font-semibold hover:brightness-95"
            >
              Continue
            </button>
          </div>
        )}

        {screen.type === "item" && (
          <div>
            <p className="text-sm text-ink-muted">
              {screen.itemNumber} of {totalItems}
            </p>
            <h2 className="mt-3 font-display text-2xl font-semibold leading-snug sm:text-3xl">
              {screen.item.text}
            </h2>
            <div className="mt-8 flex flex-col gap-2">
              {screen.section.scale.options.map((option, index) => {
                const selected = answers[screen.item.id] === option.value;
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => answerItem(screen.item, option.value)}
                    aria-pressed={selected}
                    className={`flex items-center justify-between border border-ink px-5 py-4 text-left text-lg ${
                      selected ? "bg-yellow" : "bg-transparent hover:bg-yellow/30"
                    }`}
                  >
                    <span>{option.label}</span>
                    <span aria-hidden="true" className="text-sm text-ink-muted">
                      {index + 1}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {screen.type === "bonus" && (
          <div>
            <h2 className="font-display text-2xl font-semibold leading-snug sm:text-3xl">
              {instrument.bonus.prompt}
            </h2>
            <div className="mt-8 flex flex-col gap-3">
              {instrument.bonus.options.map((option, index) => (
                <button
                  key={option.key}
                  type="button"
                  onClick={() => chooseBonus(option.key)}
                  className="border border-ink px-5 py-5 text-left text-lg hover:bg-yellow/30"
                >
                  <span className="mr-3 font-display font-semibold">
                    {index === 0 ? "A." : "B."}
                  </span>
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-sm text-ink-muted">
        <button
          type="button"
          onClick={() => goTo(screenIndex - 1)}
          disabled={screenIndex === 0}
          className="underline disabled:invisible"
        >
          Back
        </button>
        <span aria-hidden="true">
          {screen.type === "item" ? "Tap an answer or press its number" : ""}
        </span>
      </div>
    </div>
  );
}
