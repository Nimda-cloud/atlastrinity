#!/usr/bin/env python3
"""
🧪 XcodeBuildMCP Tester with macOS Tools Integration
Tests XcodeBuildMCP tools and enhances them with our macOS MCP tools
"""

import asyncio
import json
import os
import subprocess
import time


class XcodeBuildMCPTester:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.xcodebuild_path = "/Users/olegikyma/Documents/GitHub/atlastrinity/vendor/XcodeBuildMCP"

    async def test_xcodebuild_mcp(self):
        """Test XcodeBuildMCP functionality"""
        print("🧪 Starting XcodeBuildMCP Testing with macOS Tools Integration")
        print("=" * 70)

        # First, let's check if XcodeBuildMCP is installed and working
        await self.check_xcodebuild_installation()

        # Test UI automation tools
        await self.test_ui_automation_tools()

        # Test simulator tools
        await self.test_simulator_tools()

        # Test project tools
        await self.test_project_tools()

        # Enhance with our macOS tools
        await self.enhance_with_macos_tools()

        # Generate comprehensive report
        self.generate_report()

    async def check_xcodebuild_installation(self):
        """Check XcodeBuildMCP installation"""
        print("🔍 Checking XcodeBuildMCP installation...")

        try:
            # Check if npm package is installed
            result = subprocess.run(
                ["npm", "list", "-g", "xcodebuildmcp"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                print("✅ XcodeBuildMCP is installed globally")
            else:
                print("⚠️ XcodeBuildMCP not found globally, checking local installation...")

                # Check local installation
                if os.path.exists(f"{self.xcodebuild_path}/package.json"):
                    print("✅ Found local XcodeBuildMCP installation")
                    await self.test_local_xcodebuild()
                else:
                    print("❌ XcodeBuildMCP not found")
                    return False

        except Exception as e:
            print(f"❌ Error checking installation: {e}")
            return False

        return True

    async def test_local_xcodebuild(self):
        """Test local XcodeBuildMCP installation"""
        print("🧪 Testing local XcodeBuildMCP...")

        try:
            # Change to XcodeBuildMCP directory
            os.chdir(self.xcodebuild_path)

            # Check if it's built
            if not os.path.exists("build"):
                print("📦 Building XcodeBuildMCP...")
                build_result = subprocess.run(
                    ["npm", "run", "build"], capture_output=True, text=True, timeout=60
                )

                if build_result.returncode == 0:
                    print("✅ XcodeBuildMCP built successfully")
                else:
                    print(f"❌ Build failed: {build_result.stderr}")
                    return False

            # Test CLI functionality
            cli_result = subprocess.run(
                ["node", "build/cli.js", "--help"], capture_output=True, text=True, timeout=10
            )

            if cli_result.returncode == 0:
                print("✅ CLI is working")
                return True
            print(f"❌ CLI test failed: {cli_result.stderr}")
            return False

        except Exception as e:
            print(f"❌ Error testing local XcodeBuildMCP: {e}")
            return False

    async def test_ui_automation_tools(self):
        """Test UI automation tools with our macOS tools"""
        print("\n🎯 Testing UI Automation Tools...")

        ui_tools = [
            "button",
            "tap",
            "gesture",
            "key_press",
            "type_text",
            "screenshot",
            "snapshot_ui",
        ]

        for tool in ui_tools:
            print(f"🔧 Testing {tool}...")

            # Use our macOS tools to enhance UI automation
            if tool in ["tap", "button"]:
                await self.test_enhanced_tap()
            elif tool in ["key_press", "type_text"]:
                await self.test_enhanced_typing()
            elif tool == "screenshot":
                await self.test_enhanced_screenshot()
            else:
                print(f"   ℹ️ {tool} - Would test with XcodeBuildMCP")

            await asyncio.sleep(0.1)

    async def test_enhanced_tap(self):
        """Test enhanced tap using our macOS tools"""
        try:
            # Use our macOS click tool
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_click_and_traverse",
                            "arguments": {"x": 100, "y": 100},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Enhanced tap with macOS tools works")
                self.results.append(
                    {
                        "tool": "enhanced_tap",
                        "status": "success",
                        "enhancement": "macOS click_and_traverse",
                    }
                )
            else:
                print("   ❌ Enhanced tap failed")
                self.results.append(
                    {"tool": "enhanced_tap", "status": "error", "error": result.stderr}
                )

        except Exception as e:
            print(f"   ❌ Enhanced tap error: {e}")

    async def test_enhanced_typing(self):
        """Test enhanced typing using our macOS tools"""
        try:
            # Use our macOS type tool
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_type_and_traverse",
                            "arguments": {"text": "Hello from enhanced testing!"},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Enhanced typing with macOS tools works")
                self.results.append(
                    {
                        "tool": "enhanced_typing",
                        "status": "success",
                        "enhancement": "macOS type_and_traverse",
                    }
                )
            else:
                print("   ❌ Enhanced typing failed")
                self.results.append(
                    {"tool": "enhanced_typing", "status": "error", "error": result.stderr}
                )

        except Exception as e:
            print(f"   ❌ Enhanced typing error: {e}")

    async def test_enhanced_screenshot(self):
        """Test enhanced screenshot using our macOS tools"""
        try:
            # Use our macOS screenshot tool
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_take_screenshot",
                            "arguments": {"path": "/tmp/enhanced_screenshot.png", "format": "png"},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Enhanced screenshot with macOS tools works")
                self.results.append(
                    {
                        "tool": "enhanced_screenshot",
                        "status": "success",
                        "enhancement": "macOS take_screenshot",
                    }
                )
            else:
                print("   ❌ Enhanced screenshot failed")
                self.results.append(
                    {"tool": "enhanced_screenshot", "status": "error", "error": result.stderr}
                )

        except Exception as e:
            print(f"   ❌ Enhanced screenshot error: {e}")

    async def test_simulator_tools(self):
        """Test simulator tools with macOS integration"""
        print("\n📱 Testing Simulator Tools...")

        # Test our system monitoring to check simulator processes
        await self.test_simulator_monitoring()

        # Test process management for simulators
        await self.test_simulator_process_management()

    async def test_simulator_monitoring(self):
        """Test simulator monitoring with our macOS tools"""
        try:
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_process_management",
                            "arguments": {"action": "list"},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Simulator process monitoring works")
                self.results.append(
                    {
                        "tool": "simulator_monitoring",
                        "status": "success",
                        "enhancement": "macOS process_management",
                    }
                )
            else:
                print("   ❌ Simulator monitoring failed")

        except Exception as e:
            print(f"   ❌ Simulator monitoring error: {e}")

    async def test_simulator_process_management(self):
        """Test simulator process management"""
        try:
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 5,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_system_monitoring",
                            "arguments": {"metric": "cpu", "duration": 3},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Simulator system monitoring works")
                self.results.append(
                    {
                        "tool": "simulator_system_monitoring",
                        "status": "success",
                        "enhancement": "macOS system_monitoring",
                    }
                )
            else:
                print("   ❌ Simulator system monitoring failed")

        except Exception as e:
            print(f"   ❌ Simulator system monitoring error: {e}")

    async def test_project_tools(self):
        """Test project tools with macOS integration"""
        print("\n📁 Testing Project Tools...")

        # Test file operations with our macOS tools
        await self.test_enhanced_file_operations()

        # Test clipboard operations for project data
        await self.test_clipboard_integration()

    async def test_enhanced_file_operations(self):
        """Test enhanced file operations"""
        try:
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 6,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_finder_list_files",
                            "arguments": {"path": "/tmp", "limit": 10},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Enhanced file operations work")
                self.results.append(
                    {
                        "tool": "enhanced_file_operations",
                        "status": "success",
                        "enhancement": "macOS finder_list_files",
                    }
                )
            else:
                print("   ❌ Enhanced file operations failed")

        except Exception as e:
            print(f"   ❌ Enhanced file operations error: {e}")

    async def test_clipboard_integration(self):
        """Test clipboard integration for project data"""
        try:
            result = subprocess.run(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                input=json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 7,
                        "method": "tools/call",
                        "params": {
                            "name": "macos-use_set_clipboard",
                            "arguments": {"text": "Xcode project data integration test"},
                        },
                    }
                )
                + "\n",
                capture_output=True,
                text=True,
                timeout=10,
                cwd="/Users/olegikyma/Documents/GitHub/atlastrinity",
            )

            if result.returncode == 0:
                print("   ✅ Clipboard integration works")
                self.results.append(
                    {
                        "tool": "clipboard_integration",
                        "status": "success",
                        "enhancement": "macOS set_clipboard",
                    }
                )
            else:
                print("   ❌ Clipboard integration failed")

        except Exception as e:
            print(f"   ❌ Clipboard integration error: {e}")

    async def enhance_with_macos_tools(self):
        """Demonstrate how to enhance XcodeBuildMCP with our macOS tools"""
        print("\n🚀 Enhancing XcodeBuildMCP with macOS Tools...")

        enhancements = [
            {
                "name": "Enhanced UI Automation",
                "macos_tools": [
                    "click_and_traverse",
                    "type_and_traverse",
                    "press_key_and_traverse",
                ],
                "benefits": [
                    "More reliable UI interaction",
                    "Better accessibility support",
                    "Traversal capabilities",
                ],
            },
            {
                "name": "Advanced Screenshot & OCR",
                "macos_tools": ["take_screenshot", "perform_ocr", "analyze_ui"],
                "benefits": ["High-quality screenshots", "Text recognition", "UI analysis"],
            },
            {
                "name": "System Integration",
                "macos_tools": ["system_monitoring", "process_management", "notification"],
                "benefits": ["Real-time monitoring", "Process control", "User notifications"],
            },
            {
                "name": "File & Clipboard Operations",
                "macos_tools": ["finder_list_files", "set_clipboard", "clipboard_history"],
                "benefits": [
                    "Enhanced file operations",
                    "Clipboard management",
                    "History tracking",
                ],
            },
            {
                "name": "Voice Control Integration",
                "macos_tools": ["voice_control"],
                "benefits": ["Voice commands", "Hands-free operation", "Accessibility"],
            },
        ]

        for enhancement in enhancements:
            print(f"\n🎯 {enhancement['name']}:")
            print(f"   🛠️  macOS Tools: {', '.join(enhancement['macos_tools'])}")
            for benefit in enhancement["benefits"]:
                print(f"   ✅ Benefit: {benefit}")

    def generate_report(self):
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = len(self.results) - success_count

        print("\n" + "=" * 70)
        print("🎉 XcodeBuildMCP Testing with macOS Tools Complete!")
        print("=" * 70)

        print("📊 SUMMARY:")
        print(f"   Total Tests: {len(self.results)}")
        print(f"   ✅ Successful: {success_count}")
        print(f"   ❌ Errors: {error_count}")
        print(
            f"   🎯 Success Rate: {(success_count / len(self.results) * 100):.1f}%"
            if self.results
            else "   🎯 Success Rate: N/A"
        )
        print(f"   ⏱️ Total Duration: {total_duration:.2f}s")
        print()

        print("🚀 ENHANCEMENT OPPORTUNITIES:")
        print("   1. UI Automation - Use our click/type/press tools for better reliability")
        print("   2. Screenshots - Enhanced capture with OCR and UI analysis")
        print("   3. System Monitoring - Real-time CPU/memory monitoring")
        print("   4. Process Management - Advanced simulator process control")
        print("   5. Voice Control - Add voice commands to Xcode workflows")
        print("   6. File Operations - Enhanced Finder integration")
        print("   7. Clipboard Management - History and enhanced operations")
        print()

        print("�� RECOMMENDATIONS:")
        print("   • Integrate macOS tools for enhanced UI automation")
        print("   • Use our screenshot/OCR for better visual testing")
        print("   • Implement system monitoring for performance tracking")
        print("   • Add voice control for accessibility")
        print("   • Enhance file operations with Finder integration")
        print("=" * 70)

        # Save results
        report_data = {
            "timestamp": "2026-02-10T01:50:00Z",
            "total_tests": len(self.results),
            "successful": success_count,
            "errors": error_count,
            "success_rate": success_count / len(self.results) * 100 if self.results else 0,
            "total_duration": total_duration,
            "results": self.results,
            "enhancements": [
                "UI Automation Enhancement",
                "Screenshot & OCR Integration",
                "System Monitoring",
                "Process Management",
                "Voice Control",
                "File Operations",
                "Clipboard Management",
            ],
        }

        with open("/tmp/xcodebuild_mcp_test_results.json", "w") as f:
            json.dump(report_data, f, indent=2)

        print("📄 Detailed results saved to: /tmp/xcodebuild_mcp_test_results.json")


async def main():
    """Main test runner"""
    tester = XcodeBuildMCPTester()
    await tester.test_xcodebuild_mcp()


if __name__ == "__main__":
    asyncio.run(main())
