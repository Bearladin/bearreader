import { readFile, readdir, stat } from 'node:fs/promises';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ts = require('typescript');

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const scanTargets = ['src', 'public', 'index.html', 'vite.config.ts'];
const codeExtensions = new Set(['.js', '.jsx', '.mjs', '.ts', '.tsx']);
const markupExtensions = new Set(['.html', '.htm', '.svg']);
const textExtensions = new Set([
  ...codeExtensions,
  ...markupExtensions,
  '.css',
  '.json',
  '.md',
  '.scss',
  '.txt',
]);

const oldBrandPatterns = [
  /\bLightnovel Crawler\b/g,
  /\bLight Novel Crawler\b/g,
  /\bLnCrawl\b/g,
  /\bLNCrawl\b/g,
];

const uiPropertyNames = new Set([
  'aria-label',
  'alt',
  'canceltext',
  'children',
  'content',
  'description',
  'emptytext',
  'label',
  'message',
  'oktext',
  'placeholder',
  'title',
]);

const technicalTokens = [
  'API',
  'application/epub+zip',
  'Argon2id',
  'ArrowLeft',
  'ArrowRight',
  'AZW3',
  'BTC',
  'CAPTCHA',
  'CLI',
  'DOCX',
  'DNS',
  'DMCA',
  'EPUB',
  'ETA',
  'Enter',
  'FB2',
  'GitHub',
  'GNU',
  'GPL',
  'GPL-v3',
  'GBK',
  'HTML',
  'HTTP',
  'HTTPS',
  'ID',
  'IP',
  'JSON',
  'Kindle',
  'MB',
  'LIT',
  'LRF',
  'MOBI',
  'MTL',
  'NumpadAdd',
  'NumpadSubtract',
  'PDB',
  'PDF',
  '.epub',
  'PWA',
  'OAuth',
  'Python',
  'QR',
  'RB',
  'RTF',
  'TCR',
  'TXT',
  'Tor',
  'URL',
  'U.S.C.',
  'VIP',
  'Web',
  'Windows',
  'UTF-8',
  'ZIP',
  'SVG',
  // 自托管界面字体（技术标识，非界面英文文案）
  'Cabinet Grotesk',
  'Switzer',
  'Geist Mono',
  'XiaoXiong Reader Kai',
  'XiaoXiong Reader Serif',
  'Roboto Slab',
  'Google Fonts',
  'favicon',
  'BearReader',
  'BearReader.exe',
  'backendtool.exe',
  'xbanxia',
  'display-mode: standalone',
  'YYYY/M/D HH:mm',
  'Edge-TTS',
  'Cloudflare',
  'Cookie',
  'iOS',
  'px',
  'ms',
  // 中文发行版内置书源域名（精确技术标识，非界面英文文案）
  'dushulai.com',
  'shuquta.com',
  'mayiwsk.com',
  'www.mayiwsk.com',
  'nieba.net',
];

const exactTechnicalPhrases = new Set([
  'BearReader',
  'BearReader.exe',
  'backendtool.exe',
  'Unknown',
  'Volume',
  '(display-mode: standalone)',
  'input, textarea, select, button, a[href], [role="button"], [contenteditable="true"]',
  ...technicalTokens.filter((token) => token !== 'Enter'),
  'Argon2id',
  'Bitcoin',
  'Ethereum',
  'Litecoin',
  'Solana',
  'Literata',
  'Merriweather',
  'Noto Serif',
  'Source Serif 4',
  'Crimson Text',
  'PT Serif',
  'IBM Plex Serif',
  'Taviraj',
  'Cormorant',
  'Playfair Display',
  'Arbutus Slab',
  'Roboto Slab',
]);

const nonUiTechnicalPhrases = new Set([
  ...exactTechnicalPhrases,
  'Enter',
  'Apple Color Emoji',
  'Arial',
  'Authorization',
  'Bearer',
  'BlinkMacSystemFont',
  'Helvetica Neue',
  'Microsoft YaHei',
  'Noto Color Emoji',
  'Noto Sans',
  'Noto Sans CJK SC',
  'PingFang SC',
  'Segoe UI',
  'Segoe UI Emoji',
  'Segoe UI Symbol',
]);

const rawEnumAndApiKeys = new Set([
  'accepted',
  'active',
  'admin',
  'all',
  'artifact',
  'artifact_batch',
  'asc',
  'basic',
  'canceled',
  'center',
  'chapter',
  'chapter_batch',
  'checked',
  'create',
  'cyan',
  'dark',
  'default',
  'desc',
  'description',
  'disabled',
  'domain',
  'email',
  'error',
  'failed',
  'feature',
  'full_novel',
  'full_novel_batch',
  'general',
  'green',
  'horizontal',
  'image',
  'image_batch',
  'is_public',
  'issue',
  'justify',
  'large',
  'left',
  'message',
  'my',
  'name',
  'notifications',
  'novel',
  'novel_batch',
  'pending',
  'premium',
  'processing',
  'public',
  'reader',
  'resolved',
  'right',
  'role',
  'running',
  'selection',
  'status',
  'success',
  'tier',
  'total_commits',
  'total_novels',
  'used',
  'user',
  'version',
  'vertical',
  'volume',
  'volume_batch',
  'undefined',
  'zh-CN',
]);

const rawDiagnosticLiterals = new Set([
  'HTTPError: 403 Client Error: Forbidden for url',
]);

const safeNonUiPatterns = [
  /^(?:https?:\/\/|mailto:|tel:)/i,
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  /^(?:@\/|\.{1,2}\/)/,
  /^\/\S*$/,
  /^\$\{API_BASE_URL\}\/(?:api|static)\//,
  /^[\w@.-]+(?:\/[\w@.-]+)+$/,
  /^[\w.-]+\.(?:css|html?|ico|js|json|mjs|png|scss|svg|ts|tsx|woff2)$/,
  /^[.?][\w?=&${}/.-]+$/,
  /^\*{1,2}\//,
  /^[#.][0-9a-f]{3,8}$/i,
  /^[a-z]+\/[a-z0-9.+-]+$/i,
  /^&[a-z]+;$/i,
  /^(?:noopener noreferrer|noreferrer noopener)$/,
  /^(?:calc|linear-gradient|rgba?)\(/,
  /(?:\b\d+(?:\.\d+)?px\b|\bsolid\b|\bease(?:-in-out)?\b|\bcubic-bezier\(|\btransparent\b)/,
  /,\s*(?:serif|sans-serif)(?:,|$)/i,
  /^(?:0|auto)(?:\s+(?:0|auto))*$/,
  /^(?:\d+(?:\.\d+)?(?:px|rem|em|%|s|ms)?)(?:\s+\d+(?:\.\d+)?(?:px|rem|em|%|s|ms)?)*$/i,
  /^(?:YYYY|MM|DD|HH|mm|ss)(?:[-/:.\s](?:YYYY|MM|DD|HH|mm|ss))*$/,
  /^\*+$/,
];

const compareCodePoints = (left, right) => {
  if (left === right) return 0;
  return left < right ? -1 : 1;
};

const normalize = (value) => value.replace(/\s+/g, ' ').trim();

const hasEnglish = (value) => /[A-Za-z]{2,}/.test(value);

function stripAllowedTechnicalTokens(value) {
  let remaining = value;
  for (const token of [...technicalTokens].sort(
    (left, right) => right.length - left.length || compareCodePoints(left, right)
  )) {
    remaining = remaining.replace(
      new RegExp(
        `\\b${token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`,
        'gi'
      ),
      ''
    );
  }
  return remaining;
}

function isAllowedUiText(value) {
  const normalized = normalize(value)
    .replace(/\$\{[^}]*\}/g, '')
    .replace(/&(?:[a-z]+|#\d+|#x[0-9a-f]+);/gi, '')
    .trim();
  if (!normalized || !hasEnglish(normalized)) {
    return true;
  }
  const unquoted = normalized.replace(/^[“”"'‘’]+|[“”"'‘’]+$/g, '');
  if (
    exactTechnicalPhrases.has(unquoted) ||
    /^BearReader( v\d+(\.\d+){0,2})?$/.test(unquoted) ||
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(unquoted) ||
    /^[a-z]+\/[a-z0-9.+-]+$/i.test(unquoted) ||
    /^\d+(?:\.\d+)?(?:px|rem|em|%|ms)$/i.test(unquoted)
  ) {
    return true;
  }
  if (!/[\u3400-\u9fff]/u.test(normalized)) {
    return false;
  }

  const remaining = stripAllowedTechnicalTokens(normalized);
  return !hasEnglish(remaining);
}

function isAllowedNonUiText(value) {
  const normalized = normalize(value);
  if (!normalized || !hasEnglish(normalized)) {
    return true;
  }
  if (
    rawEnumAndApiKeys.has(normalized.toLowerCase()) ||
    rawDiagnosticLiterals.has(normalized) ||
    nonUiTechnicalPhrases.has(normalized) ||
    safeNonUiPatterns.some((pattern) => pattern.test(normalized))
  ) {
    return true;
  }

  const words =
    normalized
      .replace(/\$\{[^}]*\}/g, '')
      .replace(/https?:\/\/\S+/gi, '')
      .replace(/\b\S+@\S+\b/g, '')
      .match(/[A-Za-z][A-Za-z0-9+]*/g) ?? [];
  return (
    words.length === 0 ||
    words.every(
      (word) =>
        nonUiTechnicalPhrases.has(word) ||
        rawEnumAndApiKeys.has(word.toLowerCase())
    )
  );
}

function looksLikeNonUiEnglish(value) {
  const normalized = normalize(value);
  return (
    !isAllowedNonUiText(normalized) &&
    hasEnglish(normalized) &&
    (/\s/.test(normalized) ||
      /[.!?]/.test(normalized) ||
      /^[A-Z][a-z]/.test(normalized))
  );
}

function lineNumberAt(content, index) {
  return content.slice(0, index).split('\n').length;
}

function addFinding(findings, seen, file, content, index, kind, value) {
  const normalized = normalize(value);
  const line = lineNumberAt(content, index);
  const key = `${file}:${line}:${kind}:${normalized}`;
  if (!normalized || seen.has(key)) {
    return;
  }
  seen.add(key);
  findings.push({ file, line, kind, value: normalized });
}

function propertyNameText(node) {
  if (!node) return undefined;
  if (ts.isIdentifier(node) || ts.isStringLiteralLike(node)) {
    return node.text.toLowerCase();
  }
  return undefined;
}

function expressionName(node) {
  if (ts.isIdentifier(node)) {
    return node.text;
  }
  if (ts.isPropertyAccessExpression(node)) {
    return `${expressionName(node.expression)}.${node.name.text}`;
  }
  return '';
}

function isImportOrModuleSpecifier(node) {
  const parent = node.parent;
  return (
    (ts.isImportDeclaration(parent) && parent.moduleSpecifier === node) ||
    (ts.isExportDeclaration(parent) && parent.moduleSpecifier === node) ||
    (ts.isExternalModuleReference(parent) && parent.expression === node)
  );
}

function isPropertyName(node) {
  const parent = node.parent;
  return (
    ((ts.isPropertyAssignment(parent) ||
      ts.isMethodDeclaration(parent) ||
      ts.isPropertyDeclaration(parent) ||
      ts.isPropertySignature(parent) ||
      ts.isMethodSignature(parent)) &&
      parent.name === node) ||
    (ts.isElementAccessExpression(parent) && parent.argumentExpression === node)
  );
}

function isStyleContext(node) {
  let current = node.parent;
  while (current) {
    if (
      ts.isJsxAttribute(current) &&
      current.name.getText().toLowerCase() === 'style'
    ) {
      return true;
    }
    if (
      ts.isPropertyAssignment(current) &&
      propertyNameText(current.name) === 'style'
    ) {
      return true;
    }
    if (
      ts.isJsxElement(current) ||
      ts.isJsxSelfClosingElement(current) ||
      ts.isCallExpression(current) ||
      ts.isVariableStatement(current)
    ) {
      return false;
    }
    current = current.parent;
  }
  return false;
}

function isConsoleArgument(node) {
  const parent = node.parent;
  return (
    ts.isCallExpression(parent) &&
    parent.arguments.includes(node) &&
    expressionName(parent.expression).startsWith('console.')
  );
}

function buildUiContextMap(sourceFile) {
  const declarations = new Map();
  const roots = [];
  const contexts = new WeakMap();

  const unwrapExpression = (node) => {
    let current = node;
    while (
      ts.isParenthesizedExpression(current) ||
      ts.isAsExpression(current) ||
      ts.isSatisfiesExpression(current) ||
      ts.isTypeAssertionExpression(current)
    ) {
      current = current.expression;
    }
    return current;
  };

  const resolveObjectLiteral = (node, visited = new Set()) => {
    const current = unwrapExpression(node);
    if (visited.has(current)) return undefined;
    visited.add(current);

    try {
      if (ts.isObjectLiteralExpression(current)) {
        return current;
      }
      if (ts.isIdentifier(current)) {
        const initializer = declarations.get(current.text);
        return initializer
          ? resolveObjectLiteral(initializer, visited)
          : undefined;
      }
      if (
        ts.isPropertyAccessExpression(current) ||
        ts.isElementAccessExpression(current)
      ) {
        const [initializer] = objectValuesForAccess(current, visited);
        return initializer
          ? resolveObjectLiteral(initializer, visited)
          : undefined;
      }
      return undefined;
    } finally {
      visited.delete(current);
    }
  };

  const staticAccessKey = (node) => {
    const current = unwrapExpression(node);
    if (ts.isStringLiteralLike(current) || ts.isNumericLiteral(current)) {
      return { kind: 'name', value: current.text };
    }
    if (ts.isPropertyAccessExpression(current)) {
      return { kind: 'expression', value: current.getText(sourceFile) };
    }
    return undefined;
  };

  const propertyKey = (name) => {
    if (
      ts.isIdentifier(name) ||
      ts.isStringLiteralLike(name) ||
      ts.isNumericLiteral(name)
    ) {
      return { kind: 'name', value: name.text };
    }
    if (ts.isComputedPropertyName(name)) {
      const staticKey = staticAccessKey(name.expression);
      return staticKey ?? {
        kind: 'expression',
        value: name.expression.getText(sourceFile),
      };
    }
    return undefined;
  };

  const encodedPropertyKey = (key) =>
    key ? `${key.kind}:${key.value}` : undefined;

  const flattenObjectLiteral = (object, visited = new Set()) => {
    if (visited.has(object)) return new Map();
    visited.add(object);
    const properties = new Map();

    try {
      for (const property of object.properties) {
        if (ts.isPropertyAssignment(property)) {
          const key = encodedPropertyKey(propertyKey(property.name));
          if (key) properties.set(key, property.initializer);
        } else if (ts.isShorthandPropertyAssignment(property)) {
          const initializer = declarations.get(property.name.text);
          if (initializer) {
            properties.set(`name:${property.name.text}`, initializer);
          }
        } else if (ts.isSpreadAssignment(property)) {
          const spreadObject = resolveObjectLiteral(
            property.expression,
            visited
          );
          if (!spreadObject) continue;
          for (const [key, initializer] of flattenObjectLiteral(
            spreadObject,
            visited
          )) {
            properties.set(key, initializer);
          }
        }
      }
      return properties;
    } finally {
      visited.delete(object);
    }
  };

  function objectValuesForAccess(node, visited = new Set()) {
    const object = resolveObjectLiteral(node.expression, visited);
    if (!object) return [];

    const accessKey = ts.isPropertyAccessExpression(node)
      ? { kind: 'name', value: node.name.text }
      : node.argumentExpression
        ? staticAccessKey(node.argumentExpression)
        : undefined;
    const properties = flattenObjectLiteral(object, visited);
    if (!accessKey) return [...properties.values()];

    const initializer = properties.get(encodedPropertyKey(accessKey));
    return initializer ? [initializer] : [];
  }

  const addRoot = (node, context) => {
    if (node) roots.push({ node, context });
  };

  const discover = (node) => {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer
    ) {
      declarations.set(node.name.text, node.initializer);
    }

    if (ts.isJsxExpression(node) && node.expression) {
      const container = node.parent;
      if (ts.isJsxElement(container) || ts.isJsxFragment(container)) {
        addRoot(node.expression, 'JSX 文本');
      } else if (ts.isJsxAttribute(container)) {
        const name = container.name.getText().toLowerCase();
        if (uiPropertyNames.has(name)) {
          addRoot(node.expression, `JSX 属性 ${name}`);
        }
      }
    } else if (
      ts.isJsxAttribute(node) &&
      node.initializer &&
      uiPropertyNames.has(node.name.getText().toLowerCase())
    ) {
      addRoot(
        node.initializer,
        `JSX 属性 ${node.name.getText().toLowerCase()}`
      );
    } else if (ts.isPropertyAssignment(node)) {
      const name = propertyNameText(node.name);
      if (
        name &&
        uiPropertyNames.has(name) &&
        isPotentialVisibleValue(node.initializer)
      ) {
        addRoot(node.initializer, `界面属性 ${name}`);
      }
    } else if (ts.isCallExpression(node)) {
      const name = expressionName(node.expression);
      if (
        /^(?:message|messageApi)\.(?:error|info|success|warning)$/.test(name) ||
        name === 'Promise.reject' ||
        name === 'stringifyError'
      ) {
        for (const argument of node.arguments) {
          addRoot(argument, `界面调用 ${name}`);
        }
      }
    }
    ts.forEachChild(node, discover);
  };
  discover(sourceFile);

  const processedRoots = new Set();
  for (let index = 0; index < roots.length; index += 1) {
    const { node: root, context } = roots[index];
    if (processedRoots.has(root)) continue;
    processedRoots.add(root);

    const mark = (node) => {
      if (!contexts.has(node)) {
        contexts.set(node, context);
      }

      if (ts.isIdentifier(node)) {
        const declaration = declarations.get(node.text);
        if (
          declaration &&
          isPotentialVisibleValue(declaration) &&
          !processedRoots.has(declaration)
        ) {
          roots.push({
            node: declaration,
            context: `界面变量 ${node.text}`,
          });
        }
        return;
      }
      if (
        ts.isAsExpression(node) ||
        ts.isSatisfiesExpression(node) ||
        ts.isTypeAssertionExpression(node)
      ) {
        mark(node.expression);
        return;
      }
      if (ts.isParenthesizedExpression(node)) {
        mark(node.expression);
        return;
      }
      if (ts.isConditionalExpression(node)) {
        mark(node.whenTrue);
        mark(node.whenFalse);
        return;
      }
      if (ts.isBinaryExpression(node)) {
        const operator = node.operatorToken.kind;
        if (operator === ts.SyntaxKind.AmpersandAmpersandToken) {
          mark(node.right);
        } else if (
          operator === ts.SyntaxKind.BarBarToken ||
          operator === ts.SyntaxKind.QuestionQuestionToken ||
          operator === ts.SyntaxKind.PlusToken
        ) {
          mark(node.left);
          mark(node.right);
        }
        return;
      }
      if (ts.isTemplateExpression(node)) {
        for (const span of node.templateSpans) {
          mark(span.expression);
        }
        return;
      }
      if (ts.isJsxElement(node) || ts.isJsxFragment(node)) {
        for (const child of node.children) {
          mark(child);
        }
        return;
      }
      if (ts.isJsxExpression(node)) {
        if (node.expression) mark(node.expression);
        return;
      }
      if (ts.isJsxSelfClosingElement(node)) {
        return;
      }
      if (
        ts.isPropertyAccessExpression(node) ||
        ts.isElementAccessExpression(node)
      ) {
        for (const initializer of objectValuesForAccess(node)) {
          mark(initializer);
        }
        return;
      }
      if (
        ts.isStringLiteralLike(node) ||
        ts.isCallExpression(node)
      ) {
        return;
      }
      ts.forEachChild(node, mark);
    };
    mark(root);
  }
  return contexts;
}

function isPotentialVisibleValue(node) {
  return (
    ts.isStringLiteralLike(node) ||
    ts.isTemplateExpression(node) ||
    ts.isIdentifier(node) ||
    ts.isPropertyAccessExpression(node) ||
    ts.isElementAccessExpression(node) ||
    ts.isParenthesizedExpression(node) ||
    ts.isAsExpression(node) ||
    ts.isSatisfiesExpression(node) ||
    ts.isTypeAssertionExpression(node) ||
    ts.isConditionalExpression(node) ||
    ts.isBinaryExpression(node) ||
    ts.isJsxElement(node) ||
    ts.isJsxSelfClosingElement(node) ||
    ts.isJsxFragment(node)
  );
}

function isInsideNonUiJsxAttribute(node) {
  let current = node.parent;
  while (current) {
    if (ts.isJsxAttribute(current)) {
      return !uiPropertyNames.has(current.name.getText().toLowerCase());
    }
    if (
      ts.isJsxElement(current) ||
      ts.isJsxSelfClosingElement(current) ||
      ts.isJsxFragment(current)
    ) {
      return false;
    }
    current = current.parent;
  }
  return false;
}

function staticParts(node) {
  if (ts.isStringLiteralLike(node)) {
    return [{ value: node.text, start: node.getStart() + 1 }];
  }
  if (ts.isTemplateExpression(node)) {
    const parts = [
      { value: node.head.text, start: node.head.getStart() + 1 },
    ];
    for (const span of node.templateSpans) {
      parts.push({
        value: span.literal.text,
        start: span.literal.getStart() + 1,
      });
    }
    return parts;
  }
  return [];
}

function auditCode(file, content) {
  const findings = [];
  const seen = new Set();
  const extension = path.extname(file);
  const scriptKind =
    extension === '.tsx'
      ? ts.ScriptKind.TSX
      : extension === '.jsx'
        ? ts.ScriptKind.JSX
        : extension === '.js' || extension === '.mjs'
          ? ts.ScriptKind.JS
          : ts.ScriptKind.TS;
  const sourceFile = ts.createSourceFile(
    file,
    content,
    ts.ScriptTarget.Latest,
    true,
    scriptKind
  );
  const uiContexts = buildUiContextMap(sourceFile);

  const visit = (node) => {
    if (ts.isJsxText(node)) {
      const value = normalize(node.getText(sourceFile));
      if (!isAllowedUiText(value)) {
        addFinding(
          findings,
          seen,
          file,
          content,
          node.getStart(sourceFile),
          'JSX 文本',
          value
        );
      }
    } else if (
      ts.isStringLiteralLike(node) ||
      ts.isTemplateExpression(node)
    ) {
      if (
        !isImportOrModuleSpecifier(node) &&
        !isPropertyName(node) &&
        !isStyleContext(node) &&
        !isConsoleArgument(node)
      ) {
        const mappedUiContext = uiContexts.get(node);
        const uiContext =
          isInsideNonUiJsxAttribute(node) &&
          (mappedUiContext === 'JSX 文本' ||
            mappedUiContext?.startsWith('界面变量 '))
            ? undefined
            : mappedUiContext;
        for (const part of staticParts(node)) {
          const shouldReport = uiContext
            ? !isAllowedUiText(part.value)
            : looksLikeNonUiEnglish(part.value);
          if (shouldReport) {
            addFinding(
              findings,
              seen,
              file,
              content,
              part.start,
              uiContext ?? '疑似英文字符串',
              part.value
            );
          }
        }
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sourceFile);
  return findings;
}

function stripMarkupNoise(content) {
  return content
    .replace(/<!--[\s\S]*?-->/g, (match) => ' '.repeat(match.length))
    .replace(/<(?:metadata|script|style)\b[\s\S]*?<\/(?:metadata|script|style)>/gi, (match) =>
      ' '.repeat(match.length)
    );
}

function auditMarkup(file, content) {
  const findings = [];
  const seen = new Set();
  const cleaned = stripMarkupNoise(content);
  const attributePattern =
    /\b(aria-label|alt|placeholder|title)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/gi;
  for (const match of cleaned.matchAll(attributePattern)) {
    const value = match[2] ?? match[3] ?? match[4] ?? '';
    if (!isAllowedUiText(value)) {
      addFinding(
        findings,
        seen,
        file,
        content,
        match.index + match[0].indexOf(value),
        `标记属性 ${match[1].toLowerCase()}`,
        value
      );
    }
  }

  const textPattern = />([^<]+)</g;
  for (const match of cleaned.matchAll(textPattern)) {
    const value = normalize(
      match[1]
        .replace(/&(?:[a-z]+|#\d+|#x[0-9a-f]+);/gi, ' ')
        .replace(/\{\{[\s\S]*?\}\}/g, ' ')
    );
    if (!isAllowedUiText(value)) {
      addFinding(
        findings,
        seen,
        file,
        content,
        match.index + 1,
        '标记可见文本',
        value
      );
    }
  }
  return findings;
}

function auditOldBrands(file, content) {
  const findings = [];
  const seen = new Set();
  for (const pattern of oldBrandPatterns) {
    pattern.lastIndex = 0;
    for (const match of content.matchAll(pattern)) {
      addFinding(
        findings,
        seen,
        file,
        content,
        match.index,
        '旧品牌',
        match[0]
      );
    }
  }
  return findings;
}

function auditContent(file, content) {
  const extension = path.extname(file);
  return [
    ...auditOldBrands(file, content),
    ...(codeExtensions.has(extension) ? auditCode(file, content) : []),
    ...(markupExtensions.has(extension) ? auditMarkup(file, content) : []),
  ];
}

function assertRegression(name, file, content, shouldFail) {
  const findings = auditContent(file, content);
  if (shouldFail && findings.length === 0) {
    throw new Error(`审计回归样例未能拦截：${name}`);
  }
  if (!shouldFail && findings.length > 0) {
    throw new Error(
      `审计回归样例误报：${name} -> ${findings
        .map((finding) => finding.value)
        .join(', ')}`
    );
  }
}

function runRegressionChecks() {
  const regressions = [
    {
      name: '动态 JSX 模板',
      file: 'probe.tsx',
      content: 'const view = <div>{`Welcome ${name}`}</div>;',
      shouldFail: true,
    },
    {
      name: '多行模板',
      file: 'probe.tsx',
      content: 'const view = <div>{`First line\nSecond line`}</div>;',
      shouldFail: true,
    },
    {
      name: '连字符 JSX',
      file: 'probe.tsx',
      content: 'const view = <div>sign-in</div>;',
      shouldFail: true,
    },
    {
      name: 'JSX raw key',
      file: 'probe.tsx',
      content: "const view = <Button>{'create'}</Button>;",
      shouldFail: true,
    },
    {
      name: '括号包装的 JSX raw key',
      file: 'probe.tsx',
      content: "const view = <Button>{('create')}</Button>;",
      shouldFail: true,
    },
    {
      name: '变量传入 JSX 的 raw key',
      file: 'probe.tsx',
      content: "const label = 'create'; const view = <Button>{label}</Button>;",
      shouldFail: true,
    },
    {
      name: '对象直接属性传入 JSX',
      file: 'probe.tsx',
      content:
        "const labels = { pending: 'pending' }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: true,
    },
    {
      name: '对象计算属性传入 JSX',
      file: 'probe.tsx',
      content:
        "const labels = { pending: 'pending', active: 'active' }; const view = <Tag>{labels[status]}</Tag>;",
      shouldFail: true,
    },
    {
      name: '对象别名传入 JSX',
      file: 'probe.tsx',
      content:
        "const labels = { pending: 'pending' }; const alias = labels; const view = <Tag>{alias.pending}</Tag>;",
      shouldFail: true,
    },
    {
      name: '中文对象映射传入 JSX',
      file: 'probe.tsx',
      content:
        "const labels = { pending: '待处理', active: '已启用' }; const view = <Tag>{labels[status]}</Tag>;",
      shouldFail: false,
    },
    {
      name: 'spread 后中文覆盖',
      file: 'probe.tsx',
      content:
        "const base = { pending: 'pending' }; const labels = { ...base, pending: '待处理' }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: false,
    },
    {
      name: 'spread 后英文覆盖',
      file: 'probe.tsx',
      content:
        "const base = { pending: '待处理' }; const labels = { ...base, pending: 'pending' }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: true,
    },
    {
      name: '嵌套 spread 英文最终值',
      file: 'probe.tsx',
      content:
        "const base = { pending: 'pending' }; const middle = { ...base }; const labels = { ...middle }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: true,
    },
    {
      name: 'spread shorthand 英文最终值',
      file: 'probe.tsx',
      content:
        "const pending = 'pending'; const base = { pending }; const labels = { ...base }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: true,
    },
    {
      name: '静态属性忽略无关 key',
      file: 'probe.tsx',
      content:
        "const labels = { pending: '待处理', failed: 'failed' }; const view = <Tag>{labels.pending}</Tag>;",
      shouldFail: false,
    },
    {
      name: '循环对象别名终止',
      file: 'probe.tsx',
      content:
        'const first = { ...second }; const second = { ...first }; const view = <Tag>{first.pending}</Tag>;',
      shouldFail: false,
    },
    {
      name: 'HTML placeholder',
      file: 'probe.html',
      content: '<input placeholder="Search novels">',
      shouldFail: true,
    },
    {
      name: '无引号 HTML placeholder',
      file: 'probe.html',
      content: '<input placeholder=Search>',
      shouldFail: true,
    },
    {
      name: 'message.error',
      file: 'probe.ts',
      content: "message.error('failed');",
      shouldFail: true,
    },
    {
      name: 'messageApi.error',
      file: 'probe.ts',
      content: "messageApi.error('failed');",
      shouldFail: true,
    },
    {
      name: 'UI mixed technical phrase',
      file: 'probe.tsx',
      content: '<input placeholder="Enter URL">',
      shouldFail: true,
    },
    {
      name: '普通英文键名不是技术词',
      file: 'probe.tsx',
      content: '<Button>Enter</Button>',
      shouldFail: true,
    },
    {
      name: 'non-UI raw API key',
      file: 'probe.ts',
      content: "const status = 'failed'; const endpoint = '/api/jobs';",
      shouldFail: false,
    },
    {
      name: 'exact technical UI text',
      file: 'probe.tsx',
      content: '<span>EPUB</span>',
      shouldFail: false,
    },
    {
      name: 'Chinese UI with technical token',
      file: 'probe.tsx',
      content: '<span>请输入 URL</span>',
      shouldFail: false,
    },
  ];

  for (const regression of regressions) {
    assertRegression(
      regression.name,
      regression.file,
      regression.content,
      regression.shouldFail
    );
  }
  return regressions.length;
}

async function collectFiles(target) {
  const absolute = path.join(repoRoot, target);
  const targetStat = await stat(absolute);
  if (targetStat.isFile()) {
    return textExtensions.has(path.extname(absolute)) ? [absolute] : [];
  }

  const entries = await readdir(absolute, { withFileTypes: true });
  const nested = await Promise.all(
    entries
      .sort((left, right) => compareCodePoints(left.name, right.name))
      .map((entry) => {
        const relative = path.join(target, entry.name);
        if (entry.isDirectory()) {
          return collectFiles(relative);
        }
        return textExtensions.has(path.extname(entry.name))
          ? [path.join(repoRoot, relative)]
          : [];
      })
  );
  return nested.flat();
}

const regressionCount = runRegressionChecks();

const files = (
  await Promise.all(scanTargets.map((target) => collectFiles(target)))
)
  .flat()
  .sort(compareCodePoints);

const findings = [];
for (const absoluteFile of files) {
  const relativeFile = path.relative(repoRoot, absoluteFile).replaceAll('\\', '/');
  const content = await readFile(absoluteFile, 'utf8');
  findings.push(...auditContent(relativeFile, content));
}

findings.sort((left, right) => {
  return (
    compareCodePoints(left.file, right.file) ||
    left.line - right.line ||
    compareCodePoints(left.kind, right.kind) ||
    compareCodePoints(left.value, right.value)
  );
});

if (findings.length > 0) {
  console.error('中文本地化审计失败：');
  for (const finding of findings) {
    console.error(
      `- ${finding.file}:${finding.line} [${finding.kind}] ${finding.value}`
    );
  }
  process.exitCode = 1;
} else {
  console.log(
    `中文本地化审计通过：已扫描 ${files.length} 个文件，${regressionCount} 个内存回归样例通过，未发现旧品牌或疑似英文界面文案。`
  );
}
