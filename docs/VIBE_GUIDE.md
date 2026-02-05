# VIBE Integration Guide (Version 2.0.2)

This document provides a detailed overview of the architecture and integration of Vibe 2.0.2 within the Atlas Trinity project.

---

## 1. Role of `vibe_server.py` as an MCP Server

The `vibe_server.py` file serves as the core MCP (Multi-Component Protocol) server for the Vibe system. It is responsible for wrapping the Mistral Vibe CLI into an MCP-compliant programmatic mode. Key features include:

- **Configuration Support**: Handles providers, models, agents, and tool permissions.
- **Tool Integration**: Implements 17 MCP tools covering all Vibe capabilities.
- **Streaming Output**: Provides real-time notifications and streaming responses.
- **Error Handling**: Ensures proper resource cleanup and robust error management.
- **Session Management**: Supports session persistence and resumption.
- **Dynamic Switching**: Allows runtime switching of models and providers.

The server initializes using the `FastMCP` framework and dynamically loads configurations from `vibe_config.toml`. It also manages concurrency through a global lock to prevent rate-limit collisions.

---

## 2. Three-Tier Fallback Mechanism

The Vibe system employs a robust three-tier fallback mechanism to ensure uninterrupted service. The tiers are prioritized as follows:

1. **Copilot**: The primary provider for handling requests. It integrates directly with GitHub Copilot APIs.
2. **Mistral**: Acts as the secondary fallback, leveraging the Mistral AI platform for processing requests.
3. **OpenRouter**: Serves as the final fallback, ensuring redundancy and reliability.

The fallback mechanism is dynamically configured in the `fallback_chain` parameter within the Vibe configuration. When a rate limit or error occurs with the current provider, the system automatically switches to the next available provider in the chain.

---

## 3. Usage of `copilot_proxy.py` for Local GPT-4o Requests

The `copilot_proxy.py` script acts as a local proxy server to facilitate requests to the GPT-4o model. Key functionalities include:

- **Request Handling**: Supports both GET and POST requests, mimicking OpenAI-style APIs.
- **Model Listing**: Provides a standard endpoint (`/v1/models`) to list available models.
- **Request Forwarding**: Forwards requests to GitHub Copilot APIs with appropriate headers and authentication.
- **Error Management**: Handles upstream timeouts and errors gracefully, returning appropriate HTTP status codes.

The proxy listens on `127.0.0.1:8085` by default and ensures compatibility with tools expecting OpenAI-style endpoints.

---

## 4. Configuration via `vibe_config.toml`

The `vibe_config.toml` file is the central configuration file for the Vibe system. It defines:

- **Providers**: API keys, endpoints, and proxy settings for each provider.
- **Models**: Temperature, pricing, and aliases for available models.
- **MCP Servers**: Transport protocols, URLs, and startup parameters.
- **Tools**: Enabled and disabled tools, along with permissions.

> **Note**: The `vibe_config.toml.template` file was not found in the repository. Ensure that the configuration file is correctly placed and synced to the appropriate directories.

---

## Conclusion

This guide outlines the architecture and integration of Vibe 2.0.2 within the Atlas Trinity project. For further details, refer to the source code and configuration files.