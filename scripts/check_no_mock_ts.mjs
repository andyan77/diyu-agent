#!/usr/bin/env node
/**
 * Detect banned mock patterns in TypeScript/JavaScript source files.
 *
 * Banned patterns:
 *   - jest.mock(...) / jest.spyOn(...)
 *   - vi.mock(...) / vi.spyOn(...)
 *   - import ... from 'sinon'
 *   - td.replace(...) (testdouble)
 *
 * This is a text-based scanner (no AST) for speed and zero dependencies.
 *
 * Usage:
 *   node scripts/check_no_mock_ts.mjs .               # scan from cwd
 *   node scripts/check_no_mock_ts.mjs frontend/        # scan specific dir
 *   node scripts/check_no_mock_ts.mjs --json frontend/ # JSON output
 *
 * Exit codes:
 *   0 - No banned patterns
 *   1 - Banned patterns detected
 */

import { readFileSync, readdirSync, statSync } from "fs";
import { join, extname } from "path";

const BANNED_PATTERNS = [
  { regex: /\bjest\.mock\s*\(/, rule: "jest.mock" },
  { regex: /\bjest\.spyOn\s*\(/, rule: "jest.spyOn" },
  { regex: /\bvi\.mock\s*\(/, rule: "vi.mock" },
  { regex: /\bvi\.spyOn\s*\(/, rule: "vi.spyOn" },
  { regex: /from\s+['"]sinon['"]/, rule: "sinon-import" },
  { regex: /require\s*\(\s*['"]sinon['"]/, rule: "sinon-require" },
  { regex: /\btd\.replace\s*\(/, rule: "testdouble" },
];

const SCAN_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]);

const SKIP_DIRS = new Set([
  "node_modules",
  ".next",
  "dist",
  "build",
  ".turbo",
  "coverage",
]);

function walkDir(dir) {
  const results = [];
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return results;
  }

  for (const entry of entries) {
    if (SKIP_DIRS.has(entry) || entry.startsWith(".")) continue;

    const fullPath = join(dir, entry);
    let stat;
    try {
      stat = statSync(fullPath);
    } catch {
      continue;
    }

    if (stat.isDirectory()) {
      results.push(...walkDir(fullPath));
    } else if (stat.isFile() && SCAN_EXTENSIONS.has(extname(entry))) {
      results.push(fullPath);
    }
  }
  return results;
}

function scanFile(filepath) {
  const violations = [];
  let content;
  try {
    content = readFileSync(filepath, "utf-8");
  } catch {
    return violations;
  }

  const lines = content.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    for (const { regex, rule } of BANNED_PATTERNS) {
      if (regex.test(line)) {
        violations.push({
          file: filepath,
          line: i + 1,
          pattern: rule,
          content: line.trim().slice(0, 120),
        });
      }
    }
  }
  return violations;
}

function main() {
  const args = process.argv.slice(2);
  const jsonOutput = args.includes("--json");
  const dirs = args.filter((a) => !a.startsWith("--"));

  if (dirs.length === 0) {
    process.stderr.write(
      "Usage: check_no_mock_ts.mjs [--json] <dir1> [dir2] ...\n"
    );
    process.exit(2);
  }

  const allViolations = [];
  for (const dir of dirs) {
    const files = walkDir(dir);
    for (const f of files) {
      allViolations.push(...scanFile(f));
    }
  }

  if (jsonOutput) {
    const output = {
      tool: "check_no_mock_ts",
      directories: dirs,
      violations: allViolations,
      count: allViolations.length,
      status: allViolations.length > 0 ? "fail" : "pass",
    };
    process.stdout.write(JSON.stringify(output, null, 2) + "\n");
  } else {
    if (allViolations.length > 0) {
      process.stdout.write(
        `FAIL: ${allViolations.length} banned mock pattern(s) detected:\n\n`
      );
      for (const v of allViolations) {
        process.stdout.write(
          `  ${v.file}:${v.line} [${v.pattern}] ${v.content}\n`
        );
      }
      process.stdout.write(
        "\nAllowed alternative: use dependency injection or test adapters.\n"
      );
    } else {
      process.stdout.write(
        `PASS: No banned mock patterns in ${dirs.join(", ")}\n`
      );
    }
  }

  process.exit(allViolations.length > 0 ? 1 : 0);
}

main();
