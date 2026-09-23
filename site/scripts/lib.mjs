// Shared helpers for the site build scripts. Paths are resolved with node:path, so they work on
// Windows and macOS alike.
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYaml } from 'yaml';

export const siteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const repoRoot = path.resolve(siteRoot, '..');
export const docsRoot = path.join(siteRoot, 'src', 'content', 'docs');

export const read = (...parts) => readFileSync(path.join(repoRoot, ...parts), 'utf8').replace(/\r\n/g, '\n');
export const exists = (...parts) => existsSync(path.join(repoRoot, ...parts));
export const yaml = (...parts) => parseYaml(read(...parts));
export const json = (...parts) => JSON.parse(read(...parts));

export function walk(dir, filter = () => true) {
	if (!existsSync(dir)) return [];
	const out = [];
	for (const name of readdirSync(dir)) {
		const full = path.join(dir, name);
		if (statSync(full).isDirectory()) out.push(...walk(full, filter));
		else if (filter(full)) out.push(full);
	}
	return out.sort();
}

export const rel = (full) => path.relative(repoRoot, full).split(path.sep).join('/');

// Generated pages. They are gitignored and rebuilt before every check, dev, and build.
export const GENERATED = [
	'reference/agents.md',
	'reference/skills.md',
	'reference/prompts.md',
	'reference/business-questions.md',
	'reference/scripts.md',
	'present/expected-results.md',
];
