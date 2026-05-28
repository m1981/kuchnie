<script>
    // --- STATE ---
    let sessionId = "test-session-1";
    let currentMessage = "";
    let messages = [];
    let isLoading = false;

    // --- LOGIC ---
    async function sendMessage() {
        if (!currentMessage.trim()) return;

        // 1. Add user message to UI immediately
        messages = [...messages, { role: "user", content: currentMessage }];
        let promptToSend = currentMessage;
        currentMessage = ""; // Clear input
        isLoading = true;

        try {
            // 2. Call our FastAPI backend
            const response = await fetch("http://127.0.0.1:8000/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: sessionId,
                    message: promptToSend,
                    system_prompt: "You are a helpful assistant for a kitchen cabinet builder."
                })
            });

            if (!response.ok) throw new Error("API Error");

            const data = await response.json();

            // 3. Add assistant response to UI
            messages = [...messages, { 
                role: "assistant", 
                content: data.text, 
                tools: data.tools_used 
            }];
        } catch (error) {
            console.error(error);
            messages = [...messages, { role: "assistant", content: "❌ Error connecting to API." }];
        } finally {
            isLoading = false;
        }
    }

    // Handle Enter key
    function handleKeydown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    }
</script>

<!-- --- UI (HTML + TailwindCSS) --- -->
<main class="max-w-4xl mx-auto p-6 h-screen flex flex-col font-sans text-gray-800">
    
    <!-- Header -->
    <header class="mb-6 border-b pb-4">
        <h1 class="text-3xl font-bold">🪚 Kitchen Cabinet Assistant</h1>
        <p class="text-sm text-gray-500">Session: {sessionId}</p>
    </header>

    <!-- Chat Area -->
    <div class="flex-1 overflow-y-auto space-y-6 mb-6 pr-2">
        {#if messages.length === 0}
            <div class="text-center text-gray-400 mt-20">Ask a question to start...</div>
        {/if}

        {#each messages as msg}
            <div class="flex {msg.role === 'user' ? 'justify-end' : 'justify-start'}">
                <div class="max-w-[80%] rounded-lg p-4 {msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 border'}">
                    
                    <!-- Render Tool Logs (Expanders) -->
                    {#if msg.tools && msg.tools.length > 0}
                        <div class="mb-3 space-y-2">
                            {#each msg.tools as tool}
                                <details class="bg-white text-gray-800 text-xs rounded border p-2 cursor-pointer">
                                    <summary class="font-semibold">🛠️ Agent used tool: {tool.name}</summary>
                                    <div class="mt-2 p-2 bg-gray-50 rounded overflow-x-auto">
                                        <p><strong>Args:</strong> {JSON.stringify(tool.args)}</p>
                                        <p class="mt-1"><strong>Result:</strong></p>
                                        <pre class="whitespace-pre-wrap">{tool.result.content || JSON.stringify(tool.result)}</pre>
                                    </div>
                                </details>
                            {/each}
                        </div>
                    {/if}

                    <!-- Render Text -->
                    <div class="whitespace-pre-wrap">{msg.content}</div>
                </div>
            </div>
        {/each}

        {#if isLoading}
            <div class="flex justify-start">
                <div class="bg-gray-100 border rounded-lg p-4 text-gray-500 animate-pulse">
                    Thinking and reading files...
                </div>
            </div>
        {/if}
    </div>

    <!-- Input Area -->
    <div class="border-t pt-4">
        <div class="flex gap-2">
            <textarea 
                bind:value={currentMessage}
                on:keydown={handleKeydown}
                placeholder="Ask about your kitchen designs..." 
                class="flex-1 border rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows="2"
            ></textarea>
            <button 
                on:click={sendMessage}
                disabled={isLoading}
                class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
            >
                Send
            </button>
        </div>
    </div>
</main>