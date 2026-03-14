// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
	outDir: '../docs',
	integrations: [
		starlight({
			title: 'Paperwise Docs',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/zellux/paperwise' }],
			sidebar: [
				{
					label: 'Start Here',
					items: [
						{ label: 'Getting Started', slug: 'getting-started' },
						{ label: 'Model Config', slug: 'model-config' },
						{ label: 'Support', slug: 'support' },
					],
				},
				{
					label: 'Reference',
					items: [
						{ label: 'Local Development', slug: 'reference/local-development' },
						{ label: 'Repository Layout', slug: 'reference/repository-layout' },
					],
				},
			],
		}),
	],
});
