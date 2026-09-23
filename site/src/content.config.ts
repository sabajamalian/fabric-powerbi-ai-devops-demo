import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

const checkpoint = z.enum([
	'none',
	'lab02-start',
	'lab05-complete',
	'lab06-complete',
	'lab07-complete',
	'lab08-complete',
	'lab09-complete',
]);

const lab = z
	.object({
		number: z.number().int().min(0).max(99),
		durationMinutes: z.number().int().positive(),
		level: z.enum(['intro', 'intermediate', 'advanced']),
		platforms: z.array(z.enum(['windows', 'macos', 'macos-file-mode'])).min(1),
		requiresDesktop: z.boolean(),
		surfaces: z.array(z.enum(['vscode', 'cli', 'cloud-agent', 'code-review', 'github', 'desktop'])).min(1),
		primitives: z.array(z.string()),
		startCheckpoint: checkpoint,
		endCheckpoint: checkpoint,
		// Set only after someone runs the lab end to end on Windows 11. Omit it until then.
		lastVerified: z.coerce.date().optional(),
	})
	.strict();

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		schema: docsSchema({
			extend: z.object({
				description: z.string().min(20),
				lab: lab.optional(),
			}),
		}),
	}),
};
