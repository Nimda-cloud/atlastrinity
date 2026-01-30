#!/usr/bin/env node
/**
 * Config Template Sync Script
 * 
 * Syncs configuration templates to active config locations.
 * Usage: npm run config:sync
 * 
 * This script copies template files from config/ to ~/.config/atlastrinity/
 * preserving user modifications while updating structure.
 */

import fs from 'fs';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PROJECT_ROOT = path.resolve(__dirname, '..');
const CONFIG_ROOT = path.join(os.homedir(), '.config', 'atlastrinity');
const MCP_DIR = path.join(CONFIG_ROOT, 'mcp');

// Configuration mappings: template -> destination
const CONFIG_MAPPINGS = [
  {
    template: path.join(PROJECT_ROOT, 'config', 'config.yaml.template'),
    destination: path.join(CONFIG_ROOT, 'config.yaml'),
    description: 'Main system configuration',
  },
  {
    template: path.join(PROJECT_ROOT, 'config', 'behavior_config.yaml.template'),
    destination: path.join(CONFIG_ROOT, 'behavior_config.yaml'),
    description: 'Behavior engine configuration',
  },
  {
    template: path.join(PROJECT_ROOT, 'config', 'vibe_config.toml.template'),
    destination: path.join(CONFIG_ROOT, 'vibe_config.toml'),
    description: 'Vibe CLI configuration',
  },
  {
    template: path.join(PROJECT_ROOT, 'config', 'monitoring_config.yaml.template'),
    destination: path.join(CONFIG_ROOT, 'monitoring_config.yaml'),
    description: 'Monitoring and observability configuration',
  },
  {
    template: path.join(PROJECT_ROOT, 'config', 'mcp_servers.json.template'),
    destination: path.join(MCP_DIR, 'mcp_servers.json'),
    description: 'MCP servers configuration',
  },
];

function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
    console.log(`✓ Created directory: ${dirPath}`);
  }
}

function backupConfig(filePath) {
  if (fs.existsSync(filePath)) {
    const backupPath = `${filePath}.backup.${Date.now()}`;
    fs.copyFileSync(filePath, backupPath);
    console.log(`  → Backup created: ${path.basename(backupPath)}`);
    return backupPath;
  }
  return null;
}

function syncConfig(mapping, options = {}) {
  const { template, destination, description } = mapping;
  const { force = false, backup = true } = options;

  console.log(`\n📝 ${description}`);
  console.log(`   Template: ${path.relative(PROJECT_ROOT, template)}`);
  console.log(`   Destination: ${path.relative(os.homedir(), destination)}`);

  // Check if template exists
  if (!fs.existsSync(template)) {
    console.log(`   ⚠️  Template not found, skipping`);
    return false;
  }

  // Ensure destination directory exists
  ensureDirectoryExists(path.dirname(destination));

  // Backup existing config if requested
  if (backup && fs.existsSync(destination)) {
    backupConfig(destination);
  }

  // Copy template to destination
  try {
    if (force || !fs.existsSync(destination)) {
      fs.copyFileSync(template, destination);
      console.log(`   ✓ Synced successfully`);
      return true;
    } else {
      console.log(`   → File exists, use --force to overwrite`);
      return false;
    }
  } catch (error) {
    console.error(`   ✗ Error syncing: ${error.message}`);
    return false;
  }
}

function main() {
  const args = process.argv.slice(2);
  const force = args.includes('--force');
  const noBackup = args.includes('--no-backup');

  console.log('═══════════════════════════════════════════════════════');
  console.log('  AtlasTrinity Config Template Sync');
  console.log('═══════════════════════════════════════════════════════');
  console.log(`Config Root: ${CONFIG_ROOT}`);
  console.log(`Force Mode: ${force ? 'YES' : 'NO'}`);
  console.log(`Backup: ${noBackup ? 'NO' : 'YES'}`);

  let syncedCount = 0;
  let skippedCount = 0;

  for (const mapping of CONFIG_MAPPINGS) {
    const synced = syncConfig(mapping, { force, backup: !noBackup });
    if (synced) {
      syncedCount++;
    } else {
      skippedCount++;
    }
  }

  console.log('\n═══════════════════════════════════════════════════════');
  console.log(`✓ Synced: ${syncedCount} files`);
  console.log(`→ Skipped: ${skippedCount} files`);
  console.log('═══════════════════════════════════════════════════════');

  if (skippedCount > 0 && !force) {
    console.log('\nℹ️  Use --force to overwrite existing configs');
    console.log('   Example: npm run config:sync -- --force');
  }

  console.log('\n✓ Config sync complete!');
  console.log('  Run your application to apply changes.\n');
}

// Run the script
main();
