export const IMPORTED_TTS_MAX_LENGTH = 1500;

export interface TtsSegment {
  text: string;
  element: HTMLElement;
}

interface BuildTtsSegmentsOptions {
  imported: boolean;
  chapterTitle: string;
}

const SPEECH_BLOCK_SELECTOR =
  'p, li, blockquote, h1, h2, h3, h4, h5, h6, pre';
const HEADING_TAGS = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6']);
const SENTENCE_END = /[。！？!?；;…]/;

function normalizedHeading(value: string): string {
  return value.normalize('NFC').replace(/\s+/g, '').trim();
}

function isRedundantImportedHeading(
  element: HTMLElement,
  text: string,
  chapterTitle: string
): boolean {
  if (!HEADING_TAGS.has(element.tagName)) return false;
  const normalized = normalizedHeading(text);
  return (
    /^#\d+$/.test(normalized) ||
    normalized === normalizedHeading(chapterTitle)
  );
}

function preferredCut(text: string, maxLength: number): number {
  const minimum = Math.floor(maxLength * 0.4);
  for (let index = maxLength - 1; index >= minimum; index -= 1) {
    if (SENTENCE_END.test(text[index])) {
      let cut = index + 1;
      while (cut < maxLength && /[”’」』》】)]/.test(text[cut])) {
        cut += 1;
      }
      return cut;
    }
  }
  for (let index = maxLength - 1; index >= minimum; index -= 1) {
    if (/\s/.test(text[index])) return index + 1;
  }
  return maxLength;
}

export function splitTtsText(
  value: string,
  maxLength = IMPORTED_TTS_MAX_LENGTH
): string[] {
  if (maxLength < 1) throw new Error('朗读分段长度必须大于 0');
  const chunks: string[] = [];
  let remaining = value.trim();
  while (remaining.length > maxLength) {
    const cut = preferredCut(remaining, maxLength);
    const chunk = remaining.slice(0, cut).trim();
    if (chunk) chunks.push(chunk);
    remaining = remaining.slice(cut).trimStart();
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

function topLevelSegments(contentEl: HTMLDivElement): TtsSegment[] {
  return Array.from(contentEl.children).map((element) => ({
    text: element.textContent?.trim() ?? '',
    element: element as HTMLElement,
  }));
}

function importedBlocks(contentEl: HTMLDivElement): TtsSegment[] {
  const blocks: TtsSegment[] = [];
  const visit = (element: HTMLElement) => {
    const hasNestedBlock = Boolean(element.querySelector(SPEECH_BLOCK_SELECTOR));
    if (
      element !== contentEl &&
      element.matches(SPEECH_BLOCK_SELECTOR) &&
      !hasNestedBlock
    ) {
      blocks.push({ text: element.textContent?.trim() ?? '', element });
      return;
    }

    let inlineText = '';
    const flushInlineText = () => {
      const text = inlineText.trim();
      if (text) blocks.push({ text, element });
      inlineText = '';
    };
    for (const node of element.childNodes) {
      if (node.nodeType === Node.TEXT_NODE) {
        inlineText += node.textContent ?? '';
        continue;
      }
      if (!(node instanceof HTMLElement)) continue;
      if (['IMG', 'SCRIPT', 'STYLE'].includes(node.tagName)) continue;
      if (
        node.matches(SPEECH_BLOCK_SELECTOR) ||
        node.querySelector(SPEECH_BLOCK_SELECTOR)
      ) {
        flushInlineText();
        visit(node);
      } else {
        inlineText += node.textContent ?? '';
      }
    }
    flushInlineText();
  };
  visit(contentEl);
  return blocks;
}

export function buildTtsSegments(
  contentEl: HTMLDivElement | null,
  options: BuildTtsSegmentsOptions
): TtsSegment[] {
  if (!contentEl) return [];
  if (!options.imported) return topLevelSegments(contentEl);

  const segments = importedBlocks(contentEl).flatMap(({ text, element }) => {
    if (
      !text ||
      isRedundantImportedHeading(element, text, options.chapterTitle)
    ) {
      return [];
    }
    return splitTtsText(text).map((chunk) => ({ text: chunk, element }));
  });

  if (segments.length > 0) return segments;
  return topLevelSegments(contentEl).flatMap((segment) =>
    splitTtsText(segment.text).map((text) => ({
      text,
      element: segment.element,
    }))
  );
}
