# XcodeBuildMCP Integration

## Overview

XcodeBuildMCP is a Model Context Protocol server that provides comprehensive Xcode automation and iOS/macOS development capabilities for AtlasTrinity agents (Atlas, Tetyana, Grisha).

## Features

- **94+ Tools** across 14 specialized workflows
- **Build & Test Automation**: Build projects, run tests, generate coverage reports
- **Simulator Management**: List, boot, install apps, capture screenshots
- **Device Development**: Deploy to physical iOS devices
- **Log Analysis**: Parse and analyze Xcode build logs
- **Project Scaffolding**: Create new Xcode projects
- **Swift Package Manager**: Manage SPM dependencies
- **UI Automation**: Automate UI testing workflows

## Requirements

- **macOS**: 14.5 or later
- **Xcode**: 16.x or later (full installation, not just Command Line Tools)
- **Node.js**: 18.x or later
- **Git**: For cloning the repository

## Installation

XcodeBuildMCP is automatically installed during the setup process:

```bash
python3 scripts/setup_dev.py
```

The setup script will:
1. Check if full Xcode is installed
2. Clone XcodeBuildMCP from GitHub to `vendor/XcodeBuildMCP`
3. Install npm dependencies
4. Build the server (~30 seconds)

### Manual Installation

If you need to manually install or rebuild:

```bash
# Clone repository
git clone https://github.com/cameroncooke/XcodeBuildMCP.git vendor/XcodeBuildMCP

# Install dependencies
cd vendor/XcodeBuildMCP
npm install

# Build
npm run build
```

## Configuration

XcodeBuildMCP is configured in `~/.config/atlastrinity/mcp/config.json` (synced from `config/mcp_servers.json.template`):

```json
{
  "xcodebuild": {
    "command": "node",
    "args": [
      "${PROJECT_ROOT}/vendor/XcodeBuildMCP/.smithery/stdio/index.cjs"
    ],
    "connect_timeout": 120,
    "disabled": false,
    "tier": 2,
    "agents": ["atlas", "tetyana", "grisha"]
  }
}
```

## Available Workflows

1. **simulator** (19 tools): iOS Simulator development
2. **device** (14 tools): Physical device deployment
3. **debugging** (8 tools): Simulator debugging
4. **logging** (4 tools): Log capture & management
5. **macos** (11 tools): macOS app development
6. **project-discovery** (5 tools): Find and analyze projects
7. **project-scaffolding** (2 tools): Create new projects
8. **session-management** (3 tools): Session state management
9. **simulator-management** (8 tools): Simulator lifecycle
10. **swift-package** (6 tools): SPM operations
11. **ui-automation** (11 tools): UI testing automation
12. **utilities** (1 tool): Helper utilities
13. **workflow-discovery** (1 tool): Discover available workflows
14. **doctor** (1 tool): System health check

## Key Tools for Atlas Planning

Atlas benefits most from these tools for planning iOS/macOS development:

- `xcodebuild_build_project`: Build with custom schemes
- `xcodebuild_run_tests`: Execute unit/UI tests
- `xcodebuild_list_simulators`: List available simulators
- `xcodebuild_analyze_logs`: Diagnose build errors
- `xcodebuild_get_coverage`: Generate coverage reports

## Usage Examples

### Building a Project

```python
# Atlas can plan and execute iOS builds
await mcp_manager.call_tool("xcodebuild", "xcodebuild_build_project", {
    "project_path": "/path/to/MyApp.xcodeproj",
    "scheme": "MyApp",
    "configuration": "Debug",
    "destination": "platform=iOS Simulator,name=iPhone 15"
})
```

### Running Tests

```python
# Tetyana can run tests with granular control
await mcp_manager.call_tool("xcodebuild", "xcodebuild_run_tests", {
    "project_path": "/path/to/MyApp.xcodeproj",
    "scheme": "MyApp",
    "destination": "platform=iOS Simulator,name=iPhone 15",
    "only_testing": ["MyAppTests/LoginTests"]
})
```

### Managing Simulators

```python
# Grisha can manage simulator lifecycle
simulators = await mcp_manager.call_tool("xcodebuild", "xcodebuild_list_simulators", {
    "platform": "iOS",
    "available_only": True
})
```

## Troubleshooting

### "xcodebuild requires Xcode" Error

This means you have Command Line Tools but not full Xcode. Install Xcode from Mac App Store.

### Build Failures

Use `xcodebuild_analyze_logs` to parse error messages:

```python
analysis = await mcp_manager.call_tool("xcodebuild", "xcodebuild_analyze_logs", {
    "log_path": "/path/to/build.log",
    "error_only": True
})
```

### Simulator Not Booting

Check simulator status:

```python
await mcp_manager.call_tool("xcodebuild", "xcodebuild_boot_simulator", {
    "simulator_id": "SIMULATOR-UUID",
    "wait_for_boot": True
})
```

## Integration with Other MCP Servers

XcodeBuildMCP works seamlessly with:

- **macos-use**: For GUI automation and AppleScript
- **filesystem**: For reading/writing project files
- **vibe**: For AI-powered code generation and debugging
- **devtools**: For linting and code quality checks
- **github**: For repository operations

## Best Practices

1. **Use Atlas for Planning**: Let Atlas coordinate complex build/test workflows
2. **Parallel Testing**: Use `parallel: true` for faster test execution
3. **Coverage Reports**: Always generate coverage after tests
4. **Log Analysis**: Parse logs immediately after failed builds
5. **Simulator Cleanup**: Shutdown simulators when not in use

## Documentation Links

- **XcodeBuildMCP GitHub**: https://github.com/cameroncooke/XcodeBuildMCP
- **Official Docs**: https://www.xcodebuildmcp.com/
- **MCP Specification**: https://modelcontextprotocol.io/

## Version Information

- **XcodeBuildMCP**: v1.15.1+ (auto-updated from GitHub)
- **Integration Date**: 2026-01-28
- **Last Updated**: 2026-01-28
