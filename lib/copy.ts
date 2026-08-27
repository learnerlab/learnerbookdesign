// Loads the copy bank (content/copy/*.md) on the server. Files are Trevor's
// to write (§10); until filled they carry clearly marked placeholders.
import fs from "node:fs";
import path from "node:path";

export type CopyBlock = {
  /** Optional display title from a leading `# heading` line. */
  title: string | null;
  /** Body paragraphs (blank-line separated). */
  paragraphs: string[];
};

const COPY_DIR = path.join(process.cwd(), "content", "copy");
const cache = new Map<string, CopyBlock>();

export function loadCopy(name: string): CopyBlock {
  const cached = cache.get(name);
  if (cached) return cached;

  const filePath = path.join(COPY_DIR, `${name}.md`);
  let raw = "";
  try {
    raw = fs.readFileSync(filePath, "utf8");
  } catch {
    raw = `[Missing copy file: content/copy/${name}.md]`;
  }

  let title: string | null = null;
  let body = raw.trim();
  if (body.startsWith("# ")) {
    const newline = body.indexOf("\n");
    title = (newline === -1 ? body.slice(2) : body.slice(2, newline)).trim();
    body = newline === -1 ? "" : body.slice(newline + 1).trim();
  }
  const block: CopyBlock = {
    title,
    paragraphs: body
      .split(/\n\s*\n/)
      .map((p) => p.replace(/\s+/g, " ").trim())
      .filter(Boolean),
  };
  cache.set(name, block);
  return block;
}
