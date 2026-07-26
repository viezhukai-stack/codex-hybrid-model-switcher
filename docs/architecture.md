# Architecture

The switcher separates three concerns:

- Codex Desktop keeps account login, plugins, MCP, and project history.
- The external switcher changes the active provider only when Codex is closed.
- The local bridge can forward cloud requests to an OpenAI-compatible provider
  using an API key environment variable.
- The local bridge also translates Codex Responses requests into llama.cpp Chat
  Completions requests for local models.

Hybrid 2.0 keeps Codex on one `custom` provider and places a hot router in front
of both destinations:

```text
Codex Desktop -> 127.0.0.1:19032/v1 -> cloud Responses provider
                                      -> 127.0.0.1:19030/v1 -> llama.cpp bridge
```

The router chooses the destination from each request's `model`, so different
Codex tasks can use different models concurrently. For cloud models that need
the non-streaming compatibility path, it converts the complete Responses JSON
back into SSE while preserving message, reasoning, function-call, usage, and
terminal-status objects. HTTP 429 retries are bounded and honor `Retry-After`.

Bridge-routed cloud requests flow through:

```text
Codex Desktop -> 127.0.0.1:19030/v1 -> bridge -> OpenAI-compatible provider
```

Local model requests flow through:

```text
Codex Desktop -> 127.0.0.1:19030/v1 -> bridge -> 127.0.0.1:19031/v1 -> llama.cpp
```

The bridge keeps image content blocks intact, strips known local-model channel
artifacts, and shuts the llama.cpp child process down after idle timeout.
