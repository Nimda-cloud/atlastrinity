const {
  MacOSToolsBridgeClient,
} = require('../vendor/XcodeBuildMCP/build/integrations/macos-tools-bridge/client.js');
const path = require('node:path');
const process = require('node:process');

async function main() {
  console.log('--- ULTIMATE BRIDGE INTERACTION TESTING ---');

  const binaryPath = path.resolve(
    process.cwd(),
    'vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use',
  );
  process.env.MACOS_USE_BINARY_PATH = binaryPath;

  console.log(`Using binary: ${binaryPath}`);

  const client = new MacOSToolsBridgeClient();

  try {
    console.log('Connecting to bridge...');
    await client.connectOnce();
    const status = client.getStatus();
    console.log(`Connected! Status: connected=${status.connected}, pid=${status.bridgePid}`);

    const tools = await client.listTools();
    console.log(`Bridge reported ${tools.length} available tools.`);

    const testTools = [
      { name: 'macos-use_get_time', args: { format: 'readable' } },
      { name: 'macos-use_system_control', args: { action: 'get_system_info' } },
      { name: 'macos-use_system_monitoring', args: { metric: 'battery' } },
      { name: 'macos-use_list_running_apps', args: {} },
      { name: 'macos-use_list_all_windows', args: {} },
      { name: 'macos-use_finder_list_files', args: { path: process.cwd(), limit: 1 } },
      { name: 'macos-use_set_clipboard', args: { text: 'Bridge Test' } },
      { name: 'macos-use_get_clipboard', args: { format: 'text' } },
      { name: 'macos-use_list_tools_dynamic', args: {} },
      { name: 'macos-use_take_screenshot', args: { format: 'png', quality: 'low' } },
      { name: 'macos-use_run_applescript', args: { script: 'say "bridge test"' } },
    ];

    let passedCount = 0;
    for (const test of testTools) {
      process.stdout.write(`Calling ${test.name}... `);
      try {
        const result = await client.callTool(test.name, test.args);
        if (result.isError) {
          const msg = result.content[0]?.text || 'Unknown bridge error';
          console.log(`[\x1b[34mOK (Existed)\x1b[0m] (${msg.substring(0, 40)}...)`);
          passedCount++;
        } else {
          console.log('[\x1b[32mPASS\x1b[0m]');
          passedCount++;
        }
      } catch (err) {
        console.log(`[\x1b[31mFAILED\x1b[0m] (${err.message})`);
      }
    }

    console.log(`\nBridge Test Summary: ${passedCount}/${testTools.length} Handlers Proxied`);
  } catch (err) {
    console.error('Fatal error during bridge test:', err);
  } finally {
    console.log('Disconnecting...');
    await client.disconnect();
    console.log('Done.');
  }
}

main();
