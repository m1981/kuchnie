/**
 * lib/types/states.ts
 * ====================
 * Generic typed state machines for async operations.
 *
 * Eliminates the "boolean soup" anti-pattern where separate `isLoading`,
 * `error`, `data` flags can co-exist in impossible combinations (e.g.
 * loading=true AND error set simultaneously).
 */

/**
 * AsyncState — general-purpose async state machine.
 *
 * Usage:
 *   let state = $state<AsyncState<string[]>>({ status: 'idle' });
 *   state = { status: 'loading' };
 *   state = { status: 'success', data: ['a', 'b'] };
 *   state = { status: 'error', message: 'Network error' };
 *
 *   // Exhaustive switch — TypeScript will complain if you miss a branch.
 *   switch (state.status) {
 *     case 'idle':    return 'Nothing yet';
 *     case 'loading': return 'Thinking…';
 *     case 'success': return state.data.join(', ');
 *     case 'error':   return `Error: ${state.message}`;
 *   }
 */
export type AsyncState<T> =
	| { status: 'idle' }
	| { status: 'loading' }
	| { status: 'error'; message: string }
	| { status: 'success'; data: T };

/**
 * RemoteData — async state machine for fetch operations.
 *
 * Same shape as AsyncState but uses `error` instead of `message`
 * for consistency with fetch error patterns in stores.
 *
 * Usage:
 *   let fetchState = $state<RemoteData<Folder[]>>({ status: 'idle' });
 *   fetchState = { status: 'loading' };
 *   fetchState = { status: 'success', data: folders };
 *   fetchState = { status: 'error', error: 'Network error' };
 */
export type RemoteData<T> =
	| { status: 'idle' }
	| { status: 'loading' }
	| { status: 'error'; error: string }
	| { status: 'success'; data: T };
