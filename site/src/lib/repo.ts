// Build-time access to repository files, so the site shows the real files instead of copies.
import { parse } from 'yaml';

import repoFiles from 'virtual:repo-files';

export const files: Record<string, string> = repoFiles;

export const repo = __REPO__;
export const repoUrl = `https://github.com/${repo}`;

export function readRepoFile(path: string): string {
	const clean = path.replace(/^\.?\//, '');
	const text = files[clean];
	if (text === undefined) {
		throw new Error(`RepoFile: ${clean} is not in the repo, or SOURCES in site/src/plugins/vite-repo-files.mjs doesn't include it.`);
	}
	return text;
}

export interface Check {
	id: string;
	lab: string;
	anchor: string;
	description: string;
	hint: string;
	required?: boolean;
	windows_only?: boolean;
}

export interface LabInfo {
	slug: string;
	title: string;
}

export interface Contract {
	site_url: string;
	labs: Record<string, LabInfo>;
	checks: Check[];
	shipped: Record<string, string[]>;
}

export const contract = parse(readRepoFile('lab/checks.yaml')) as Contract;

export interface CheckpointInfo {
	name: string;
	tag: string;
	aliases: string[];
	description: string;
}

export const checkpoints = (JSON.parse(readRepoFile('lab/checkpoints.json')) as { checkpoints: CheckpointInfo[] })
	.checkpoints;

export function labNumber(value: string | number): string {
	return String(value).padStart(2, '0');
}

export function checksFor(lab: string | number): Check[] {
	const key = labNumber(lab);
	return contract.checks.filter((c) => c.lab === key);
}

export const tracks = {
	full: {
		label: 'Full hands-on',
		labs: ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15'],
	},
	core: { label: 'Core', labs: ['01', '02', '04', '05', '06', '07', '10', '11', '12'] },
	customization: {
		label: 'Copilot customization only',
		labs: ['00', '01', '03', '06', '07', '11', '12', '13', '14', '15'],
	},
	presenter: { label: 'Presenter', labs: ['00', '01', '02'] },
} as const;
