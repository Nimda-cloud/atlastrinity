const { spawn } = require('node:child_process');
const _path = require('node:path');

// Path to the recompiled binary
const SERVER_PATH =
  '/Users/olegkizyma/Documents/GitHub/atlastrinity/vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use';

const client = spawn(SERVER_PATH, [], {
  stdio: ['pipe', 'pipe', 'inherit'],
});

let id = 0;
const pendingRequests = new Map();
const BASE64_REGEX = /^[A-Za-z0-9+/=]+$/;

client.stdout.on('data', (data) => {
  const lines = data
    .toString()
    .split('\n')
    .filter((line) => line.trim());
  for (const line of lines) {
    try {
      const response = JSON.parse(line);
      // Determine if it's a response to a request
      if (response.id !== undefined && pendingRequests.has(response.id)) {
        const { resolve, reject } = pendingRequests.get(response.id);
        pendingRequests.delete(response.id);
        if (response.error) {
          reject(response.error);
        } else {
          resolve(response.result);
        }
      }
    } catch {
      // Ignore parse errors for partial lines
    }
  }
});

function sendRequest(method, params) {
  return new Promise((resolve, reject) => {
    const request = {
      jsonrpc: '2.0',
      id: id++,
      method,
      params,
    };
    pendingRequests.set(request.id, { resolve, reject });
    client.stdin.write(`${JSON.stringify(request)}\n`);
  });
}

function sendNotification(method, params) {
  const notification = {
    jsonrpc: '2.0',
    method,
    params,
  };
  client.stdin.write(`${JSON.stringify(notification)}\n`);
}

async function runTests() {
  try {
    console.log('--- Initializing ---');
    const initRes = await sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'verifier', version: '1.0' },
    });
    console.log('Initialize Response:', JSON.stringify(initRes));

    sendNotification('notifications/initialized', {});
    console.log('Initialized.');

    // Test 1: Finder List Files (New Implementation)
    console.log('\n--- Test 1: Finder List Files ---');
    try {
      const finderRes = await sendRequest('tools/call', {
        name: 'macos-use_finder_list_files',
        arguments: { path: '/', limit: 3 },
      });
      console.log('Finder Result:', `${JSON.stringify(finderRes, null, 2).slice(0, 200)}...`);
    } catch (e) {
      console.error('Finder Error:', e);
    }

    // Test 2: System Control (New Actions)
    console.log('\n--- Test 2: System Control Actions ---');
    try {
      const mediaRes = await sendRequest('tools/call', {
        name: 'macos-use_system_control',
        arguments: { action: 'get_system_info' },
      });
      console.log('System Info Result:', JSON.stringify(mediaRes, null, 2));
    } catch (e) {
      console.error('System Control Error:', e);
    }

    // Test 3: Screenshot (Base64 Check)
    console.log('\n--- Test 3: Screenshot ---');
    try {
      const shotRes = await sendRequest('tools/call', {
        name: 'macos-use_take_screenshot',
        arguments: { quality: 'low' }, // Use low quality for speed
      });
      const content = shotRes.content[0].text;
      console.log('Screenshot Result Length:', content.length);
      console.log('Starts with:', content.slice(0, 50));
      console.log('Ends with:', content.slice(-50));
      // Check for valid Base64 characters only (simple regex)
      if (BASE64_REGEX.test(content)) {
        console.log('Status: Valid Base64');
      } else {
        console.log('Status: INVALID Base64 (contains non-b64 chars)');
      }
    } catch (e) {
      console.error('Screenshot Error:', e);
    }

    // Test 4: Notes (Corrected Syntax)
    console.log('\n--- Test 4: Notes List Folders ---');
    try {
      const notesRes = await sendRequest('tools/call', {
        name: 'macos-use_notes_list_folders',
        arguments: {},
      });
      console.log('Notes Result:', JSON.stringify(notesRes, null, 2));
    } catch (e) {
      console.error('Notes Error:', e);
    }

    // Test 5: Native System Info
    console.log('\n--- Test 5: Native System Info ---');
    try {
      console.log('Calling get_system_info...');
      const sysInfoRes = await sendRequest('tools/call', {
        name: 'macos-use_system_control',
        arguments: { action: 'get_system_info' },
      });
      console.log('System Info Result:', JSON.stringify(sysInfoRes, null, 2));
    } catch (e) {
      console.error('System Info Error:', e);
    }

    try {
      console.log('Calling get_storage...');
      const storageRes = await sendRequest('tools/call', {
        name: 'macos-use_system_control',
        arguments: { action: 'get_storage' },
      });
      console.log('Storage Info Result:', JSON.stringify(storageRes, null, 2));
    } catch (e) {
      console.error('Storage Info Error:', e);
    }

    // Test 6: Calendar Events (Native)
    console.log('\n--- Test 6: Calendar Events (Native) ---');
    try {
      const now = new Date();
      const future = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000); // +7 days
      console.log(`Searching events from ${now.toISOString()} to ${future.toISOString()}...`);
      const eventsRes = await sendRequest('tools/call', {
        name: 'macos-use_calendar_events',
        arguments: {
          start: now.toISOString(),
          end: future.toISOString(),
        },
      });
      console.log('Calendar Events Result:', JSON.stringify(eventsRes, null, 2));
    } catch (e) {
      console.error('Calendar Events Error:', e);
    }

    // Test 7: Reminders (Native)
    console.log('\n--- Test 7: Reminders (Native) ---');
    try {
      console.log('Fetching reminders...');
      const remindersRes = await sendRequest('tools/call', {
        name: 'macos-use_reminders',
        arguments: {},
      });
      console.log('Reminders Result:', JSON.stringify(remindersRes, null, 2));
    } catch (e) {
      console.error('Reminders Error:', e);
    }
  } catch (err) {
    console.error('Test Suite Failed:', err);
  } finally {
    client.kill();
  }
}

runTests();
