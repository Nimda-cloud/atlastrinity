
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { MacOSToolsBridgeClient } from './client.js';
import { ENHANCED_TOOLS } from './tools.js';
import { log } from '../../utils/logger.js';

let bridgeManager: MacOSToolsBridgeManager | null = null;

export class MacOSToolsBridgeManager {
  private client: MacOSToolsBridgeClient;

  constructor() {
    this.client = new MacOSToolsBridgeClient({
      onBridgeClosed: () => {
        log('warning', '[macos-tools-bridge] Bridge connection closed');
      },
    });
  }

  async connect(): Promise<void> {
    try {
      await this.client.connectOnce();
      const status = this.client.getStatus();
      log('info', `[macos-tools-bridge] Connected to bridge (PID: ${status.bridgePid})`);
    } catch (error) {
      log('error', `[macos-tools-bridge] Failed to connect: ${error instanceof Error ? error.message : String(error)}`);
      throw error;
    }
  }

  async callTool(name: string, args: any): Promise<any> {
    return await this.client.callTool(name, args);
  }

  async shutdown(): Promise<void> {
    await this.client.disconnect();
  }
}

export function getMacOSToolsBridgeManager(): MacOSToolsBridgeManager {
  if (!bridgeManager) {
    bridgeManager = new MacOSToolsBridgeManager();
  }
  return bridgeManager;
}

export async function registerMacOSTools(server: McpServer): Promise<void> {
  const manager = getMacOSToolsBridgeManager();

  try {
    await manager.connect();
  } catch (error) {
    log('error', `[macos-tools-bridge] Skipping registration due to connection failure: ${error}`);
    return;
  }

  for (const toolDef of ENHANCED_TOOLS) {
    server.tool(
      toolDef.name,
      toolDef.description,
      toolDef.schema.shape, // McpServer expects a raw object shape, not a Zod schema
      async (args: any) => {
        try {
          const result = await manager.callTool(toolDef.macosToolName, args);
          return {
            content: result.content,
            isError: result.isError
          };
        } catch (error) {
             return {
                content: [{
                    type: 'text' as const,
                    text: `Error calling tool ${toolDef.name}: ${error instanceof Error ? error.message : String(error)}`
                }],
                isError: true
            };
        }
      }
    );
    log('debug', `[macos-tools-bridge] Registered tool: ${toolDef.name}`);
  }

  log('info', `[macos-tools-bridge] Registered ${ENHANCED_TOOLS.length} enhanced tools`);
}

export async function shutdownMacOSToolsBridge(): Promise<void> {
    if (bridgeManager) {
        await bridgeManager.shutdown();
        bridgeManager = null;
    }
}
