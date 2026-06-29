# Architecture

The switcher separates three concerns:

- Codex Desktop keeps account login, plugins, MCP, and project history.
- The external switcher changes the active provider only when Codex is closed.
- The local bridge translates Codex Responses requests into llama.cpp Chat
  Completions requests.

Local model requests flow through:

```text
Codex Desktop -> 127.0.0.1:19030/v1 -> bridge -> 127.0.0.1:19031/v1 -> llama.cpp
```

The bridge keeps image content blocks intact, strips known local-model channel
artifacts, and shuts the llama.cpp child process down after idle timeout.

