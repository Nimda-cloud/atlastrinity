
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import {
  StdioClientTransport,
  type StdioServerParameters,
} from '@modelcontextprotocol/sdk/client/stdio.js';
import { CompatibilityCallToolResultSchema } from '@modelcontextprotocol/sdk/types.js';
import type { CallToolResult, Tool } from '@modelcontextprotocol/sdk/types.js';
import process from 'node:process';

export interface MacOSToolsBridgeClientStatus {
  connected: boolean;
  bridgePid: number | null;
  lastError: string | null;
}

export interface MacOSToolsBridgeClientOptions {
  serverParams?: StdioServerParameters;
  connectTimeoutMs?: number;
  listToolsTimeoutMs?: number;
  callToolTimeoutMs?: number;
  onToolsListChanged?: () => void;
  onBridgeClosed?: () => void;
}

export class MacOSToolsBridgeClient {
  private readonly options: Required<
    Pick<
      MacOSToolsBridgeClientOptions,
      'connectTimeoutMs' | 'listToolsTimeoutMs' | 'callToolTimeoutMs'
    >
  > &
    Omit<
      MacOSToolsBridgeClientOptions,
      'connectTimeoutMs' | 'listToolsTimeoutMs' | 'callToolTimeoutMs'
    >;

  private transport: StdioClientTransport | null = null;
  private client: Client | null = null;
  private connectPromise: Promise<void> | null = null;
  private lastError: string | null = null;

  constructor(options: MacOSToolsBridgeClientOptions = {}) {
    this.options = {
      connectTimeoutMs: options.connectTimeoutMs ?? 15_000,
      listToolsTimeoutMs: options.listToolsTimeoutMs ?? 15_000,
      callToolTimeoutMs: options.callToolTimeoutMs ?? 60_000,
      ...options,
    };
  }

  getStatus(): MacOSToolsBridgeClientStatus {
    return {
      connected: this.client !== null,
      bridgePid: this.transport?.pid ?? null,
      lastError: this.lastError,
    };
  }

  async connectOnce(): Promise<void> {
    if (this.client) return;
    if (this.connectPromise) return this.connectPromise;

    this.connectPromise = (async (): Promise<void> => {
      try {
        const serverParams =
          this.options.serverParams ??
          ({
            command: process.env.MACOS_USE_BINARY_PATH || '../mcp-server-macos-use/.build/release/mcp-server-macos-use',
            args: [],
            stderr: 'pipe',
            env: process.env as Record<string, string>,
          } satisfies StdioServerParameters);

        const transport = new StdioClientTransport(serverParams);
        transport.onclose = (): void => {
          this.client = null;
          this.transport = null;
          this.connectPromise = null;
          this.options.onBridgeClosed?.();
        };

        const client = new Client(
          { name: 'xcodebuildmcp-macos-tools-bridge', version: '1.0.0' },
          {
            capabilities: {
                sampling: {},
            },
          },
        );

        await client.connect(transport, { timeout: this.options.connectTimeoutMs });

        this.transport = transport;
        this.client = client;
        this.lastError = null;
      } catch (error) {
        this.lastError = error instanceof Error ? error.message : String(error);
        await this.disconnect();
        throw error;
      } finally {
        this.connectPromise = null;
      }
    })();

    return this.connectPromise;
  }

  async disconnect(): Promise<void> {
    const client = this.client;
    const transport = this.transport;
    this.client = null;
    this.transport = null;
    this.connectPromise = null;

    try {
      await client?.close();
    } finally {
      try {
        await transport?.close?.();
      } catch {
        // ignore
      }
    }
  }

  async listTools(): Promise<Tool[]> {
    if (!this.client) {
      throw new Error('Bridge client is not connected');
    }
    const result = await this.client.listTools(undefined, {
      timeout: this.options.listToolsTimeoutMs,
    });
    return result.tools;
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<CallToolResult> {
    if (!this.client) {
      throw new Error('Bridge client is not connected');
    }
    const result: unknown = await this.client.request(
        { method: 'tools/call', params: { name, arguments: args } },
        CompatibilityCallToolResultSchema,
        {
          timeout: this.options.callToolTimeoutMs,
          // resetTimeoutOnProgress: true, // Not supported in this version of SDK?
        },
      );

    if (isCallToolResult(result)) {
      return result;
    }
    if (result && typeof result === 'object' && 'toolResult' in result) {
      const toolResult = (result as { toolResult: unknown }).toolResult;
      if (isCallToolResult(toolResult)) {
        return toolResult;
      }
    }

    // If this is a task result, we don't support it today.
    if (result && typeof result === 'object' && 'task' in result) {
      throw new Error(
        `Tool "${name}" returned a task result; task-based tools are not supported by the bridge proxy`,
      );
    }

    throw new Error(`Tool "${name}" returned an unexpected result shape`);
  }
}

function isCallToolResult(result: unknown): result is CallToolResult {
  if (!result || typeof result !== 'object') return false;
  const record = result as Record<string, unknown>;
  return Array.isArray(record.content);
}
