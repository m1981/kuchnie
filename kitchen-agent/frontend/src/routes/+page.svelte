<script lang="ts">
	import Markdown from '$lib/components/Markdown.svelte';

	type ToolLog = {
		name: string;
		args: Record<string, unknown>;
		result: {
			content?: string;
			[key: string]: unknown;
		};
	};

	type Message = {
		role: 'user' | 'assistant';
		content: string;
		tools?: ToolLog[];
	};

	type SessionSummary = {
		id: string;
		title: string;
		updated_at: string;
	};

	const templates = {
		'General Assistant':
			'You are a helpful assistant for a kitchen cabinet builder. Read files to answer questions, but NEVER edit or create files unless the user explicitly asks you to.',
		'Design Mode':
			'You are an expert kitchen designer. Focus on ergonomics, spacing, and aesthetics. Always check the repo map for design guidelines. NEVER edit files unless explicitly requested.',
		'Assembly Mode':
			"You are a master carpenter. Focus on structural integrity, hardware installation, and step-by-step assembly instructions. Answer the user's questions based on the files, but DO NOT modify the files yourself unless told to do so."
	};

	const modeMeta: Record<keyof typeof templates, { label: string; eyebrow: string }> = {
		'General Assistant': { label: 'General', eyebrow: 'Workspace help' },
		'Design Mode': { label: 'Design', eyebrow: 'Ergonomics and layout' },
		'Assembly Mode': { label: 'Assembly', eyebrow: 'Build and fitting' }
	};

	const starterPrompts = [
		'Review a kitchen layout for ergonomic risks and missing clearances.',
		'Explain which hinges and runners fit a tall kitchen cabinet.',
		'Create a step-by-step assembly checklist for base cabinets.',
		'Summarize material choices for durable kitchen cabinet fronts.'
	];

	let sessionId: string = $state(crypto.randomUUID());
	let currentMessage = $state('');
	let messages = $state<Message[]>([]);
	let isLoading = $state(false);
	let savedSessions = $state<SessionSummary[]>([]);
	let selectedTemplateName = $state<keyof typeof templates>('General Assistant');

	const activePrompt = $derived(templates[selectedTemplateName]);
	const activeMode = $derived(modeMeta[selectedTemplateName]);

	$effect(() => {
		fetchSessions();
	});

	async function fetchSessions() {
		try {
			const res = await fetch('http://127.0.0.1:8000/api/sessions');
			if (res.ok) savedSessions = await res.json();
		} catch (e) {
			console.error('Failed to fetch sessions', e);
		}
	}

	async function loadSession(id: string) {
		try {
			const res = await fetch(`http://127.0.0.1:8000/api/sessions/${id}`);
			if (res.ok) {
				const data = await res.json();
				sessionId = id;
				messages = data.ui_messages || [];
			}
		} catch (e) {
			console.error('Failed to load session', e);
		}
	}

	function startNewChat() {
		sessionId = crypto.randomUUID();
		messages = [];
		currentMessage = '';
	}

	function useStarterPrompt(prompt: string) {
		currentMessage = prompt;
	}

	function formatToolResult(tool: ToolLog) {
		return tool.result.content || JSON.stringify(tool.result, null, 2);
	}

	async function sendMessage() {
		if (!currentMessage.trim() || isLoading) return;

		const promptToSend = currentMessage.trim();
		messages.push({ role: 'user', content: promptToSend });
		currentMessage = '';
		isLoading = true;

		try {
			const response = await fetch('http://127.0.0.1:8000/api/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					session_id: sessionId,
					message: promptToSend,
					system_prompt: activePrompt
				})
			});

			if (!response.ok) {
				throw new Error(`API Error: ${response.status}`);
			}

			const data = await response.json();
			messages.push({ role: 'assistant', content: data.text, tools: data.tools_used });
			fetchSessions();
		} catch (error) {
			console.error('Fetch failed:', error);
			messages.push({ role: 'assistant', content: 'Error connecting to API.' });
		} finally {
			isLoading = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
</script>

<svelte:head>
	<title>Kitchen Agent</title>
</svelte:head>

<div class="flex h-screen overflow-hidden bg-surface text-ink">
	<aside
		class="hidden w-72 shrink-0 border-r border-line bg-panel/86 p-4 shadow-[1px_0_0_rgba(38,35,31,0.03)] lg:flex lg:flex-col"
	>
		<div class="mb-5">
			<p class="text-xs font-semibold tracking-[0.18em] text-muted uppercase">Kitchen Agent</p>
			<h1 class="mt-2 text-xl font-semibold text-ink">Project conversations</h1>
		</div>

		<button
			onclick={startNewChat}
			class="mb-5 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-line bg-ink px-3 text-sm font-semibold text-white shadow-sm transition hover:bg-ink-soft focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none"
		>
			<span aria-hidden="true">+</span>
			New chat
		</button>

		<div class="min-h-0 flex-1">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">History</h2>
				<span class="rounded-full bg-surface px-2 py-0.5 text-xs text-muted"
					>{savedSessions.length}</span
				>
			</div>

			<div class="space-y-1.5 overflow-y-auto pr-1">
				{#if savedSessions.length === 0}
					<p class="rounded-md border border-dashed border-line bg-surface p-3 text-sm text-muted">
						No saved conversations yet.
					</p>
				{/if}

				{#each savedSessions as session (session.id)}
					<button
						onclick={() => loadSession(session.id)}
						class="group w-full rounded-md px-3 py-2 text-left text-sm transition {sessionId ===
						session.id
							? 'bg-accent-soft text-ink shadow-[inset_3px_0_0_var(--color-accent)]'
							: 'text-muted hover:bg-surface hover:text-ink'}"
					>
						<span class="block truncate font-medium">{session.title}</span>
						<span class="mt-0.5 block truncate text-xs opacity-70"
							>{session.id.substring(0, 8)}</span
						>
					</button>
				{/each}
			</div>
		</div>
	</aside>

	<main class="flex min-w-0 flex-1 flex-col">
		<header class="border-b border-line bg-panel/92 px-4 py-3 backdrop-blur md:px-6">
			<div
				class="mx-auto flex max-w-5xl flex-col gap-3 md:flex-row md:items-center md:justify-between"
			>
				<div>
					<p class="text-xs font-semibold tracking-[0.16em] text-muted uppercase">
						Kitchen Cabinet Assistant
					</p>
					<div class="mt-1 flex flex-wrap items-center gap-2">
						<h2 class="text-xl font-semibold text-ink md:text-2xl">{activeMode.label} mode</h2>
						<span
							class="rounded-full border border-line bg-surface px-2.5 py-1 text-xs font-medium text-muted"
						>
							Session {sessionId.substring(0, 8)}
						</span>
					</div>
				</div>

				<div class="flex rounded-md border border-line bg-surface p-1">
					{#each Object.keys(templates) as templateName (templateName)}
						{@const typedName = templateName as keyof typeof templates}
						<button
							onclick={() => (selectedTemplateName = typedName)}
							class="rounded px-3 py-1.5 text-sm font-medium transition {selectedTemplateName ===
							typedName
								? 'bg-panel text-ink shadow-sm'
								: 'text-muted hover:text-ink'}"
						>
							{modeMeta[typedName].label}
						</button>
					{/each}
				</div>
			</div>
		</header>

		<section class="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6">
			<div class="mx-auto max-w-5xl space-y-5">
				<details class="group rounded-md border border-line bg-panel shadow-sm">
					<summary
						class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm"
					>
						<span>
							<span class="font-semibold text-ink">System prompt</span>
							<span class="ml-2 text-muted">{selectedTemplateName} · {activeMode.eyebrow}</span>
						</span>
						<span class="text-xs font-medium text-accent group-open:hidden">Expand</span>
						<span class="hidden text-xs font-medium text-accent group-open:inline">Collapse</span>
					</summary>
					<div class="border-t border-line bg-surface px-4 py-3">
						<p class="text-sm leading-6 whitespace-pre-wrap text-ink">{activePrompt}</p>
					</div>
				</details>

				{#if messages.length === 0}
					<div class="rounded-md border border-dashed border-line bg-panel p-5 shadow-sm">
						<p class="text-sm font-semibold text-ink">Start with a practical kitchen workflow</p>
						<div class="mt-4 grid gap-2 md:grid-cols-2">
							{#each starterPrompts as prompt (prompt)}
								<button
									onclick={() => useStarterPrompt(prompt)}
									class="rounded-md border border-line bg-surface px-3 py-3 text-left text-sm leading-5 text-ink transition hover:border-accent hover:bg-accent-soft focus:ring-2 focus:ring-accent focus:outline-none"
								>
									{prompt}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				<div class="space-y-5">
					{#each messages as msg, messageIndex (`${msg.role}-${messageIndex}`)}
						<article
							class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}"
							aria-label={msg.role === 'user' ? 'User message' : 'Assistant message'}
						>
							<div
								class={msg.role === 'user'
									? 'max-w-[min(760px,88%)] rounded-md bg-ink px-4 py-3 text-white shadow-sm'
									: 'w-full max-w-4xl rounded-md border border-line bg-panel p-4 shadow-sm'}
							>
								<div class="mb-2 flex items-center justify-between gap-3">
									<p
										class={msg.role === 'user'
											? 'text-xs font-semibold tracking-[0.14em] text-white/70 uppercase'
											: 'text-xs font-semibold tracking-[0.14em] text-muted uppercase'}
									>
										{msg.role === 'user' ? 'You' : 'Assistant'}
									</p>

									{#if msg.role === 'assistant' && msg.tools && msg.tools.length > 0}
										<span
											class="rounded-full border border-line bg-surface px-2 py-0.5 text-xs font-medium text-muted"
										>
											{msg.tools.length} tools
										</span>
									{/if}
								</div>

								<Markdown content={msg.content} variant={msg.role} />

								{#if msg.role === 'assistant' && msg.tools && msg.tools.length > 0}
									<div class="mt-4 space-y-2 border-t border-line pt-3">
										<p class="text-xs font-semibold tracking-[0.14em] text-muted uppercase">
											Tools used
										</p>

										{#each msg.tools as tool, toolIndex (`${tool.name}-${toolIndex}`)}
											<details class="group rounded-md border border-line bg-surface">
												<summary
													class="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-sm"
												>
													<span class="min-w-0">
														<span class="font-semibold text-ink">{tool.name}</span>
														<span class="ml-2 text-xs text-muted">Args and result</span>
													</span>
													<span class="text-xs font-medium text-accent group-open:hidden">View</span
													>
													<span class="hidden text-xs font-medium text-accent group-open:inline"
														>Hide</span
													>
												</summary>

												<div class="space-y-3 border-t border-line px-3 py-3">
													<div>
														<p class="mb-1 text-xs font-semibold text-muted uppercase">Args</p>
														<pre
															class="overflow-x-auto rounded bg-code px-3 py-2 text-xs leading-5 text-code-ink">{JSON.stringify(
																tool.args,
																null,
																2
															)}</pre>
													</div>
													<div>
														<p class="mb-1 text-xs font-semibold text-muted uppercase">Result</p>
														<pre
															class="max-h-72 overflow-auto rounded bg-code px-3 py-2 text-xs leading-5 text-code-ink">{formatToolResult(
																tool
															)}</pre>
													</div>
												</div>
											</details>
										{/each}
									</div>
								{/if}
							</div>
						</article>
					{/each}

					{#if isLoading}
						<article class="flex justify-start">
							<div class="w-full max-w-4xl rounded-md border border-line bg-panel p-4 shadow-sm">
								<p class="text-xs font-semibold tracking-[0.14em] text-muted uppercase">
									Assistant
								</p>
								<div class="mt-3 flex items-center gap-3 text-sm text-muted">
									<span class="h-2 w-2 animate-pulse rounded-full bg-accent"></span>
									Thinking, reading files, and preparing the answer...
								</div>
							</div>
						</article>
					{/if}
				</div>
			</div>
		</section>

		<footer class="border-t border-line bg-panel/95 px-4 py-4 backdrop-blur md:px-6">
			<div class="mx-auto max-w-5xl">
				<div class="mb-2 flex items-center justify-between gap-3">
					<p class="text-xs font-medium text-muted">
						Active mode:
						<span class="font-semibold text-ink">{selectedTemplateName}</span>
					</p>
					<button
						onclick={startNewChat}
						class="text-xs font-semibold text-muted transition hover:text-ink lg:hidden"
					>
						New chat
					</button>
				</div>

				<div class="flex items-end gap-2 rounded-md border border-line bg-surface p-2 shadow-sm">
					<label class="sr-only" for="message-input">Message</label>
					<textarea
						id="message-input"
						bind:value={currentMessage}
						onkeydown={handleKeydown}
						placeholder="Ask about layouts, materials, fittings, assembly, or kitchen documentation..."
						class="max-h-40 min-h-16 flex-1 resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink placeholder:text-muted focus:outline-none"
						rows="2"
					></textarea>

					<button
						onclick={sendMessage}
						disabled={isLoading || !currentMessage.trim()}
						class="h-10 rounded-md bg-accent px-4 text-sm font-semibold text-white transition hover:bg-accent-strong focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:outline-none disabled:cursor-not-allowed disabled:opacity-45"
					>
						Send
					</button>
				</div>
			</div>
		</footer>
	</main>
</div>
