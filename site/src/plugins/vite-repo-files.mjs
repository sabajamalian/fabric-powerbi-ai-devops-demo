// Vite plugin that exposes selected repository files as `virtual:repo-files`, a map of
// repo-relative POSIX path to text. import.meta.glob skips dot folders such as .github, so the
// site reads the files with node:fs instead. Paths use node:path and work on Windows.
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import path from 'node:path';

const ID = 'virtual:repo-files';
const RESOLVED = '\0' + ID;

// [directory, recursive, allowed extensions or exact file names]
const SOURCES = [
	['.github', true, ['.md', '.yml', '.yaml', '.json', 'CODEOWNERS']],
	['.vscode', false, ['.json']],
	['config', false, ['.json']],
	['scripts', true, ['.ps1', '.sh', '.psd1']],
	['fabric', true, ['.tmdl', '.json', '.pbism', '.pbir', '.pbip', '.md', '.yaml', '.dax']],
	['evaluation', true, ['.yaml', '.json', '.md']],
	['lab', true, ['.yaml', '.json', '.md']],
	['rules', false, ['.yaml']],
	['data', false, ['README.md']],
	['data/schema', false, ['.json']],
	['tools/python/pharmacy_demo', true, ['.py']],
	['tools/python', false, ['pyproject.toml', 'requirements.txt', 'requirements-dev.txt']],
	['site', false, ['package.json', 'astro.config.mjs', '.nvmrc']],
	[
		'.',
		false,
		[
			'AGENTS.md',
			'README.md',
			'SECURITY.md',
			'CONTRIBUTING.md',
			'apm.yml',
			'apm.lock.yaml',
			'.gitattributes',
			'.gitignore',
			'.editorconfig',
			'PSScriptAnalyzerSettings.psd1',
		],
	],
];

const SKIP_DIRS = new Set(['node_modules', '.venv', '__pycache__', 'out', 'dist', '.pbi']);

function matches(name, allowed) {
	return allowed.some((a) => (a.startsWith('.') && !a.includes('.', 1) ? name.endsWith(a) : name === a));
}

function collect(repoRoot) {
	const out = {};
	for (const [dir, recursive, allowed] of SOURCES) {
		const start = path.join(repoRoot, dir);
		if (!existsSync(start)) continue;
		const stack = [start];
		while (stack.length) {
			const current = stack.pop();
			for (const name of readdirSync(current)) {
				const full = path.join(current, name);
				const stat = statSync(full);
				if (stat.isDirectory()) {
					if (recursive && !SKIP_DIRS.has(name)) stack.push(full);
				} else if (matches(name, allowed)) {
					const key = path.relative(repoRoot, full).split(path.sep).join('/');
					out[key] = readFileSync(full, 'utf8').replace(/\r\n/g, '\n');
				}
			}
		}
	}
	return out;
}

export default function repoFiles({ repoRoot }) {
	return {
		name: 'contoso-repo-files',
		resolveId(id) {
			return id === ID ? RESOLVED : undefined;
		},
		load(id) {
			if (id !== RESOLVED) return undefined;
			const files = collect(repoRoot);
			for (const key of Object.keys(files)) this.addWatchFile(path.join(repoRoot, key));
			return `export default ${JSON.stringify(files)};`;
		},
	};
}
