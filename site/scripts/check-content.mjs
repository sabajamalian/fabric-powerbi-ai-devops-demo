// Checks the lab site's authored content before the build: lab page structure, the anchors that
// lab/checks.yaml links to, references to repo files, alt text, and prose style. Exits 1 on any
// problem. Run with: npm run check
import path from 'node:path';
import matter from 'gray-matter';
import { GENERATED, docsRoot, exists, json, read, rel, walk, yaml } from './lib.mjs';

const SECTIONS = [
	'At a glance',
	'Why this matters',
	'Concepts',
	'Before you begin',
	'Steps',
	'Verify your work',
	'Troubleshooting',
	'Knowledge check',
	'Recap and next',
	'Go further',
];

const problems = [];
const problem = (file, message) => problems.push(`${file}: ${message}`);

const contract = yaml('lab', 'checks.yaml');
const checkpointNames = new Set(['none', ...json('lab', 'checkpoints.json').checkpoints.map((c) => c.name)]);
const generated = new Set(GENERATED.map((g) => g.split('/').join(path.sep)));

const pages = walk(docsRoot, (f) => /\.mdx?$/.test(f));
const docRel = (full) => path.relative(docsRoot, full).split(path.sep).join('/');

// Parameter names declared in a script's top-level param(...) block, lowercased.
const paramCache = new Map();
function scriptParams(p) {
	if (paramCache.has(p)) return paramCache.get(p);
	const text = read(p).replace(/<#[\s\S]*?#>/g, '');
	const start = text.search(/^\s*param\s*\(/im);
	const names = new Set();
	if (start >= 0) {
		let i = text.indexOf('(', start);
		let depth = 0;
		let end = i;
		for (; end < text.length; end++) {
			if (text[end] === '(') depth++;
			else if (text[end] === ')' && --depth === 0) break;
		}
		for (const m of text.slice(i + 1, end).matchAll(/\$(\w+)\s*(?=[=,)\r\n]|$)/g)) names.add(m[1].toLowerCase());
	}
	paramCache.set(p, names);
	return names;
}

// Removes fenced code, inline code, and import lines, so prose checks don't trip on code.
function proseOf(body) {
	return body
		.replace(/^(\s*)(```|~~~)[\s\S]*?^\1\2\s*$/gm, '')
		.replace(/`[^`\n]*`/g, '')
		.replace(/^import .*$/gm, '');
}

// ---------- Every lab in the contract has a page ----------
for (const [num, info] of Object.entries(contract.labs)) {
	const slug = info.slug;
	if (!pages.some((p) => docRel(p).replace(/\.mdx?$/, '') === slug)) {
		problem(`lab/checks.yaml`, `lab ${num} slug ${slug} has no page under site/src/content/docs/`);
	}
}

for (const full of pages) {
	const file = rel(full);
	const isGenerated = generated.has(path.relative(docsRoot, full));
	const source = read(file);
	const { data, content } = matter(source);

	if (!data.title) problem(file, 'frontmatter has no title');
	if (!data.description || String(data.description).length < 20) {
		problem(file, 'frontmatter description is missing or shorter than 20 characters');
	}
	if (/^STUB\b|title: STUB/m.test(source)) problem(file, 'placeholder page (STUB) is still in place');

	const prose = proseOf(content);

	// Prose style: no em or en dashes, no emojis.
	if (!isGenerated) {
		content.split('\n').forEach((line, i) => {
			if (/[\u2013\u2014]/.test(line)) problem(`${file}:${i + 1}`, 'em or en dash; use a comma, colon, period, or "to"');
		});
		if (/\p{Extended_Pictographic}/u.test(prose)) problem(file, 'emoji in prose');
	}

	// Identifiers: GUIDs and email addresses never belong on the site.
	const guid = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i;
	const email = /\b[A-Za-z0-9._%+-]+@(?!users\.noreply\.github\.com)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/;
	content.split('\n').forEach((line, i) => {
		if (guid.test(line)) problem(`${file}:${i + 1}`, 'looks like a GUID; use a placeholder');
		if (email.test(line) && !/@(astrojs|github)\//.test(line)) problem(`${file}:${i + 1}`, 'looks like an email address');
	});

	// Images need alt text.
	for (const m of content.matchAll(/!\[([^\]]*)\]\(([^)]+)\)/g)) {
		if (!m[1].trim()) problem(file, `image ${m[2]} has no alt text`);
	}
	for (const m of content.matchAll(/<img\b[^>]*>/g)) {
		if (!/\balt=("[^"]+"|\{)/.test(m[0])) problem(file, `<img> without alt text: ${m[0].slice(0, 60)}`);
	}

	// Repo files named on the page exist.
	for (const m of content.matchAll(/<RepoFile\b[^>]*>/g)) {
		const p = /\bpath="([^"]+)"/.exec(m[0])?.[1];
		if (!p) continue;
		if (!exists(p)) {
			problem(file, `RepoFile path ${p} doesn't exist`);
			continue;
		}
		const range = /\blines="(\d+)-(\d+)"/.exec(m[0]);
		if (range) {
			const text = read(p);
			const total = text.split('\n').length - (text.endsWith('\n') ? 1 : 0);
			const [a, b] = [Number(range[1]), Number(range[2])];
			if (a > b || b > total) problem(file, `RepoFile ${p} lines ${a}-${b} is outside the file (${total} lines)`);
			else if (a === 1 && b === total) problem(file, `RepoFile ${p} lines 1-${b} is the whole file; drop the lines attribute`);
		}
	}
	for (const m of content.matchAll(/(?:\.\/)?scripts\/[\w./-]+\.ps1/g)) {
		const p = m[0].replace(/^\.\//, '');
		if (!exists(p)) problem(file, `script ${p} doesn't exist`);
	}
	// Parameters passed to repo scripts must exist in the script's param block.
	for (const m of content.matchAll(/(?:\.[\\/])?scripts[\\/]([\w.\\/-]+\.ps1)((?:[ \t]+[^\s`|;>]+)*)/g)) {
		const p = `scripts/${m[1].replace(/\\/g, '/')}`;
		if (!exists(p)) continue;
		const params = scriptParams(p);
		for (const arg of m[2].matchAll(/(?:^|\s)-([A-Za-z]\w*)/g)) {
			if (!params.has(arg[1].toLowerCase())) problem(file, `${p} has no parameter -${arg[1]}`);
		}
	}

	// ---------- Lab pages ----------
	if (!/^labs\/\d\d-/.test(docRel(full))) continue;
	const num = docRel(full).slice(5, 7);
	const lab = data.lab;
	if (!lab) {
		problem(file, 'lab page has no lab frontmatter');
		continue;
	}
	if (String(lab.number).padStart(2, '0') !== num) problem(file, `lab.number ${lab.number} doesn't match the file name`);
	if (!String(data.title).startsWith(`Lab ${num}: `)) problem(file, `title must start with "Lab ${num}: "`);
	for (const key of ['startCheckpoint', 'endCheckpoint']) {
		if (lab[key] && !checkpointNames.has(lab[key])) problem(file, `${key} ${lab[key]} isn't in lab/checkpoints.json`);
	}

	const h2 = [...content.matchAll(/^## (.+)$/gm)].map((m) => m[1].trim());
	if (JSON.stringify(h2) !== JSON.stringify(SECTIONS)) {
		problem(file, `sections must be exactly, in order: ${SECTIONS.join(' | ')}. Found: ${h2.join(' | ')}`);
	}

	const steps = [...content.matchAll(/^### Step (\d+)\. (.+)$/gm)].map((m) => Number(m[1]));
	if (steps.length === 0) problem(file, 'no "### Step N." headings');
	steps.forEach((n, i) => {
		if (n !== i + 1) problem(file, `step numbers must run 1, 2, 3 with no gaps; found ${steps.join(', ')}`);
	});
	const anchors = new Set(steps.map((n) => `step-${n}`));
	for (const check of contract.checks.filter((c) => c.lab === num)) {
		if (!anchors.has(check.anchor)) problem(file, `check ${check.id} links to #${check.anchor}, which isn't on the page`);
	}
	for (const m of content.matchAll(/<Checkpoint\b[^>]*\bstep="(\d+)"/g)) {
		if (!steps.includes(Number(m[1]))) problem(file, `<Checkpoint step="${m[1]}"> has no matching step heading`);
	}

	const required = [
		['<LabMeta', 'LabMeta in At a glance'],
		[`<VerifyStep lab="${num}"`, `<VerifyStep lab="${num}" />`],
		['<CatchUp', 'CatchUp in Before you begin'],
		[`<NextLab current="${num}"`, `<NextLab current="${num}" />`],
	];
	for (const [needle, what] of required) if (!content.includes(needle)) problem(file, `missing ${what}`);
	const quizzes = (content.match(/<KnowledgeCheck\b/g) || []).length;
	if (quizzes < 2 || quizzes > 3) problem(file, `needs two or three KnowledgeCheck blocks, found ${quizzes}`);
	if (!/<details>/.test(content)) problem(file, 'Troubleshooting needs at least one <details> block');
}

if (problems.length) {
	console.error(`check-content: ${problems.length} problem(s)\n`);
	for (const p of problems) console.error(`  ${p}`);
	process.exit(1);
}
console.log(`check-content: ${pages.length} pages OK.`);
