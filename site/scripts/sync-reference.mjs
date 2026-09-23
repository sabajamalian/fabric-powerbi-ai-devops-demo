// Writes the generated reference pages from the real repo files, so the site can't drift from
// the agents, skills, prompts, questions, sample runs, and scripts it describes.
import { mkdirSync, writeFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import matter from 'gray-matter';
import { GENERATED, docsRoot, json, read, rel, repoRoot, walk, yaml } from './lib.mjs';

const REPO = process.env.SITE_REPO || 'sabajamalian/fabric-powerbi-ai-devops-demo';
const blob = (p) => `https://github.com/${REPO}/blob/main/${p}`;
const notice = (sources) =>
	`:::note[Generated page]\nBuilt from ${sources} by \`site/scripts/sync-reference.mjs\`. Edit those files, not this page.\n:::\n`;
// Local URLs in help text become code, so the link validator doesn't treat them as site links.
const html = (s) =>
	String(s ?? '')
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/(?<!`)\bhttps?:\/\/(localhost|127\.0\.0\.1)[^\s`)]*/g, (m) => '`' + m.replace(/[.,]$/, '') + '`' + (/[.,]$/.test(m) ? m.slice(-1) : ''));
const esc = (s) => html(s).replace(/\|/g, '\\|').replace(/\n+/g, ' ').trim();
const code = (s) => `\`${String(s).replace(/`/g, "'")}\``;

function page(file, title, description, body) {
	const target = path.join(docsRoot, file);
	mkdirSync(path.dirname(target), { recursive: true });
	const front = `---\ntitle: ${JSON.stringify(title)}\ndescription: ${JSON.stringify(description)}\n---\n\n`;
	writeFileSync(target, front + body.trim() + '\n', 'utf8');
}

function fm(full) {
	return matter(read(rel(full)));
}

// ---------- Agents ----------
{
	const files = walk(path.join(repoRoot, '.github', 'agents'), (f) => f.endsWith('.agent.md'));
	let body = notice('`.github/agents/*.agent.md`');
	body += '\n| Agent | What it does | Tools |\n|---|---|---|\n';
	for (const f of files) {
		const { data } = fm(f);
		body += `| [${data.name}](#${data.name}) | ${esc(data.description)} | ${(data.tools ?? []).map(code).join(', ')} |\n`;
	}
	for (const f of files) {
		const { data } = fm(f);
		body += `\n## ${data.name}\n\n${esc(data.description)}\n\n`;
		body += `- **File:** [${rel(f)}](${blob(rel(f))})\n`;
		if (data['argument-hint']) body += `- **Argument hint:** ${esc(data['argument-hint'])}\n`;
		body += `- **Tools:** ${(data.tools ?? []).map(code).join(', ')}\n`;
		const hand = data.handoffs ?? [];
		if (hand.length) {
			body += '\n**Handoffs** (buttons that appear after the agent answers):\n\n| Button | Goes to | Sends the prompt automatically |\n|---|---|---|\n';
			for (const h of hand) body += `| ${esc(h.label)} | [${h.agent}](#${h.agent}) | ${h.send ? 'yes' : 'no, you review it first'} |\n`;
		}
	}
	page('reference/agents.md', 'Agents', 'Every custom agent in this repo, generated from the agent files.', body);
}

// ---------- Skills ----------
{
	const dirs = readdirSync(path.join(repoRoot, '.github', 'skills')).sort();
	let body = notice('`.github/skills/*/SKILL.md`');
	body += '\nCopilot reads each skill\'s `description` to decide when to load it, then reads the rest of `SKILL.md` and its `references/` only if it needs them.\n';
	body += '\n| Skill | Loads when |\n|---|---|\n';
	for (const d of dirs) {
		const { data } = matter(read('.github', 'skills', d, 'SKILL.md'));
		body += `| [${data.name}](#${data.name}) | ${esc(data.description)} |\n`;
	}
	for (const d of dirs) {
		const { data } = matter(read('.github', 'skills', d, 'SKILL.md'));
		const extra = walk(path.join(repoRoot, '.github', 'skills', d), (f) => !f.endsWith('SKILL.md')).map(rel);
		body += `\n## ${data.name}\n\n${esc(data.description)}\n\n- **File:** [.github/skills/${d}/SKILL.md](${blob(`.github/skills/${d}/SKILL.md`)})\n`;
		if (extra.length) body += `- **Supporting files:** ${extra.map((p) => `[${p.split('/').slice(3).join('/')}](${blob(p)})`).join(', ')}\n`;
	}
	body += '\n## Third-party skill: semantic-model-authoring\n\nInstalled from [microsoft/skills-for-fabric](https://github.com/microsoft/skills-for-fabric) by `apm install` into `.agents/skills/` and pinned in `apm.lock.yaml`. It isn\'t committed to this repo. See [APM and plugins](/reference/apm-and-plugins/).\n';
	page('reference/skills.md', 'Skills', 'Every skill in this repo, generated from the SKILL.md files.', body);
}

// ---------- Prompts ----------
{
	const files = walk(path.join(repoRoot, '.github', 'prompts'), (f) => f.endsWith('.prompt.md'));
	let body = notice('`.github/prompts/*.prompt.md`');
	body += '\nType `/` followed by the prompt name in Copilot Chat to run one. Inputs in the table are asked for when you run the prompt, or you can pass them inline, for example `/answer-business-questions label=local-baseline`.\n';
	body += '\n| Prompt | Runs with agent | Inputs | What it does |\n|---|---|---|---|\n';
	for (const f of files) {
		const { data, content } = fm(f);
		const inputs = [...new Set([...content.matchAll(/\$\{input:([a-zA-Z0-9_-]+)/g)].map((m) => m[1]))];
		const agent = data.agent === 'agent' ? 'Agent (built in)' : `[${data.agent}](/reference/agents/#${data.agent})`;
		body += `| [/${data.name}](${blob(rel(f))}) | ${agent} | ${inputs.map(code).join(', ') || 'none'} | ${esc(data.description)} |\n`;
	}
	page('reference/prompts.md', 'Prompts', 'Every prompt file in this repo, generated from the prompt files.', body);
}

// ---------- Business questions ----------
{
	const q = yaml('evaluation', 'questions.yaml');
	let body = notice('`evaluation/questions.yaml` and `evaluation/expected/*.json`');
	body += `\nFive questions, graded 0 to 2 each, for a maximum of 10. The data covers ${q.data_window.start} to ${q.data_window.end}; the latest month is ${q.data_window.latest_month}.\n\n`;
	body += ':::caution[Spoilers for the question-tester]\nThis page shows the reference answers. That\'s fine for you to read. The `question-tester` agent is told not to read them, and a hook blocks it from opening `evaluation/expected/` in Copilot CLI and the cloud agent.\n:::\n';
	for (const item of q.questions) {
		const exp = json('evaluation', 'expected', `${item.id}.json`);
		body += `\n## ${item.id}: ${item.question}\n\n`;
		body += `**Paraphrases** (other ways a user might ask; try them in chat, the grader scores the main wording):\n\n${item.paraphrases.map((p) => `- ${p}`).join('\n')}\n\n`;
		body += `**Answer columns:** ${item.answer_columns.map(code).join(', ')}\n\n`;
		body += `**Grading:** ${esc(item.grading.type)}${item.grading.partial ? `, partial credit by ${esc(item.grading.partial.type)}` : ''}.\n\n`;
		body += `<details>\n<summary>How the reference answer is defined</summary>\n\n${esc(item.default_interpretation)}\n\n</details>\n\n`;
		const rows = exp.rows.slice(0, 12);
		body += `<details>\n<summary>Expected answer (${exp.rows.length} rows${exp.rows.length > 12 ? ', first 12 shown' : ''})</summary>\n\n`;
		body += `| ${exp.columns.join(' | ')} |\n|${exp.columns.map(() => '---').join('|')}|\n`;
		for (const r of rows) body += `| ${exp.columns.map((c) => esc(r[c])).join(' | ')} |\n`;
		body += '\n</details>\n';
	}
	page('reference/business-questions.md', 'Business questions', 'The five business questions, their paraphrases, and the reference answers.', body);
}

// ---------- Scripts ----------
function help(text) {
	const block = /<#([\s\S]*?)#>/.exec(text)?.[1] ?? '';
	const out = { synopsis: '', description: '', params: [], examples: [] };
	const parts = block.split(/^\s*\.(SYNOPSIS|DESCRIPTION|PARAMETER|EXAMPLE|NOTES)\b ?(.*)$/m);
	for (let i = 1; i < parts.length; i += 3) {
		const [kind, arg, value] = [parts[i], parts[i + 1].trim(), parts[i + 2].replace(/^\n/, '').replace(/\s+$/, '')];
		const dedent = value.split('\n').map((l) => l.replace(/^ {4}/, '')).join('\n');
		if (kind === 'SYNOPSIS') out.synopsis = dedent.trim();
		else if (kind === 'DESCRIPTION') out.description = dedent.trim();
		else if (kind === 'PARAMETER') out.params.push({ name: arg, text: dedent.trim() });
		else if (kind === 'EXAMPLE') out.examples.push(dedent.trim());
	}
	return out;
}
{
	const files = walk(path.join(repoRoot, 'scripts'), (f) => f.endsWith('.ps1'))
		.map(rel)
		.filter((p) => !p.includes('/tests/') && !path.basename(p).startsWith('_'));
	let body = notice('the comment-based help in `scripts/**/*.ps1`');
	body += '\nEvery script runs in PowerShell 7 (`pwsh`) on Windows 11, and most also run on macOS. None installs system software. Get the same help in a terminal with `Get-Help ./scripts/<name>.ps1 -Detailed`.\n';
	const groups = { 'scripts/lab/': 'Lab scripts', 'scripts/hooks/': 'Hook scripts', 'scripts/maintainer/': 'Maintainer scripts', 'scripts/': 'Everyday scripts' };
	for (const [prefix, label] of Object.entries(groups)) {
		const inGroup = files.filter((p) => p.startsWith(prefix) && (prefix !== 'scripts/' || p.split('/').length === 2));
		if (!inGroup.length) continue;
		body += `\n## ${label}\n`;
		for (const p of inGroup) {
			const h = help(read(p));
			body += `\n### ${path.basename(p)}\n\n${esc(h.synopsis)}\n\n- **File:** [${p}](${blob(p)})\n`;
			if (h.description) body += `\n<details>\n<summary>Details</summary>\n\n${html(h.description)}\n\n</details>\n`;
			if (h.params.length) {
				body += '\n| Parameter | Meaning |\n|---|---|\n';
				for (const prm of h.params) body += `| ${code('-' + prm.name)} | ${esc(prm.text)} |\n`;
			}
			if (h.examples.length) body += `\n\`\`\`powershell\n${h.examples.join('\n')}\n\`\`\`\n`;
		}
	}
	page('reference/scripts.md', 'Scripts', 'Every PowerShell script in the repo, generated from its comment-based help.', body);
}

// ---------- Expected results ----------
{
	const q = yaml('evaluation', 'questions.yaml');
	const before = json('evaluation', 'runs', 'sample-baseline.json');
	const after = json('evaluation', 'runs', 'sample-ai-ready.json');
	let body = notice('`evaluation/runs/sample-baseline.json` and `evaluation/runs/sample-ai-ready.json`');
	body += '\nThese are the committed sample runs, graded by `pharmacy_demo`. Your own runs in Labs 05 and 10 will differ in wording and sometimes by a point per question. What should hold: the AI-ready model scores clearly higher, and Q02, Q04, and Q05 improve the most.\n';
	body += `\n## Scores\n\n| Question | Before (baseline) | After (AI-ready) |\n|---|---|---|\n`;
	for (const item of q.questions) {
		const b = before.grade.by_question[item.id];
		const a = after.grade.by_question[item.id];
		body += `| ${item.id}: ${esc(item.question)} | ${b.score} (${esc(b.reason)}) | ${a.score} (${esc(a.reason)}) |\n`;
	}
	body += `| **Total** | **${before.grade.total} of ${before.grade.max}** | **${after.grade.total} of ${after.grade.max}** |\n`;
	for (const [label, run] of [['Baseline run notes', before], ['AI-ready run notes', after]]) {
		body += `\n## ${label}\n\n${esc(run.notes ?? '')}\n\n| Question | Assumptions the agent recorded |\n|---|---|\n`;
		for (const ans of run.answers) body += `| ${ans.question_id} | ${esc((ans.assumptions ?? []).join('; ')) || 'none'} |\n`;
	}
	body += '\n## Normal variance\n\n- Scores can move by one point on Q02 to Q05 between two runs on the same model, because the agent may pick a different reading of "latest month" or "unusually high" when the model doesn\'t define them.\n- On the AI-ready model the definitions are in the AI instructions and measures, so runs agree more often.\n- The deterministic check is `Invoke-DaxQuestionTests.ps1` in Lab 08. It runs the reference DAX against Desktop and doesn\'t vary.\n';
	page('present/expected-results.md', 'Expected results', 'Before and after scores from the committed sample runs, with notes on normal variance.', body);
}

console.log(`sync-reference: wrote ${GENERATED.length} generated pages.`);
