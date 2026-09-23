// Checks the built site in dist/: every page loads scripts, styles, frames, and images only from
// this site, so the lab works offline and sends nothing to third parties. Exits 1 on any problem.
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { siteRoot, walk } from './lib.mjs';

const dist = path.join(siteRoot, 'dist');
const pages = walk(dist, (f) => f.endsWith('.html'));
if (pages.length === 0) {
	console.error('check-dist: no HTML in site/dist. Run npm run build first.');
	process.exit(1);
}

const offsite = /^(https?:)?\/\//i;
const patterns = [
	[/<script\b[^>]*\bsrc="([^"]+)"/gi, 'script'],
	[/<link\b[^>]*\brel="(?:stylesheet|preload|modulepreload)"[^>]*\bhref="([^"]+)"/gi, 'stylesheet or preload'],
	[/<iframe\b[^>]*\bsrc="([^"]+)"/gi, 'iframe'],
	[/<img\b[^>]*\bsrc="([^"]+)"/gi, 'image'],
	[/@import\s+(?:url\()?["']?([^"')\s]+)/gi, 'CSS import'],
];

const problems = [];
for (const full of pages) {
	const html = readFileSync(full, 'utf8');
	const file = path.relative(siteRoot, full).split(path.sep).join('/');
	for (const [re, kind] of patterns) {
		for (const m of html.matchAll(re)) if (offsite.test(m[1])) problems.push(`${file}: off-site ${kind} ${m[1]}`);
	}
	if (/STUB/.test(html.replace(/<script[\s\S]*?<\/script>/g, ''))) problems.push(`${file}: placeholder text STUB`);
}

if (problems.length) {
	console.error(`check-dist: ${problems.length} problem(s)\n`);
	for (const p of problems) console.error(`  ${p}`);
	process.exit(1);
}
console.log(`check-dist: ${pages.length} pages load nothing from other sites.`);
