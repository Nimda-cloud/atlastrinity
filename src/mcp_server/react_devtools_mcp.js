#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

/**
 * React DevTools MCP Server
 * Provides tools to inspect React component tree and state via Chrome DevTools Protocol.
 *
 * Note: This server acts as a bridge. It expects another MCP server (chrome-devtools-mcp)
 * to be running, or it can be used to generate scripts to be executed via evaluate_script.
 *
 * BETTER APPROACH: This server provides specialized scripts that "understand" React Fiber
 * to be executed in the browser context.
 */

const server = new Server(
  {
    name: 'react-devtools-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

const REACT_QUERY_SCRIPTS = {
  get_tree: `
    (function() {
      const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
      if (!hook) return { error: "React DevTools Global Hook not found. Is DevTools established?" };
      
      const renderers = Array.from(hook.renderers.values());
      if (renderers.length === 0) return { error: "No React renderers found." };

      function simplifyNode(node) {
        if (!node) return null;
        return {
          name: node.elementType?.displayName || node.elementType?.name || node.type?.displayName || node.type?.name || "Anonymous",
          type: typeof node.type === 'string' ? node.type : 'component',
          props: node.memoizedProps ? Object.keys(node.memoizedProps).filter(k => k !== 'children') : [],
          children: node.child ? [simplifyNode(node.child)] : [] // Simplified recursive walk
        };
      }

      // This is a VERY simplified walk. Реалізація повного дерева Fiber потребує більше коду.
      return { success: true, message: "React detected. Use specialized queries for deeper inspection." };
    })()
  `,

  detect_react: `
    (function() {
      return !!(window.__REACT_DEVTOOLS_GLOBAL_HOOK__ && window.__REACT_DEVTOOLS_GLOBAL_HOOK__.renderers.size > 0);
    })()
  `,
};

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'react_get_introspection_script',
        description:
          'Returns a JavaScript snippet to be executed in the browser (via evaluate_script) to inspect React internals.',
        inputSchema: {
          type: 'object',
          properties: {
            queryType: {
              type: 'string',
              enum: ['detect', 'basic_info', 'component_tree'],
              description: 'The type of introspection to perform.',
            },
          },
          required: ['queryType'],
        },
      },
    ],
  };
});

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'react_get_introspection_script') {
    let script = '';
    switch (args.queryType) {
      case 'detect':
        script = REACT_QUERY_SCRIPTS.detect_react;
        break;
      case 'basic_info':
        script = REACT_QUERY_SCRIPTS.get_tree;
        break;
      default:
        script = "return 'Not implemented yet';";
    }

    return {
      content: [
        {
          type: 'text',
          text: script,
        },
      ],
    };
  }

  throw new Error(`Tool not found: ${name}`);
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('React DevTools MCP server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
