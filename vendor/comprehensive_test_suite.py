#!/usr/bin/env python3
"""
🧪 Comprehensive macOS MCP Server Test Suite
Tests all 50+ tools with deep validation, edge cases, and performance metrics
"""

import asyncio
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class ComprehensiveTester:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.test_data = {}
        
    async def run_test(self, tool_name, params, test_type="basic"):
        """Run a single test with comprehensive validation"""
        test_start = time.time()
        
        try:
            # Create test input
            input_data = {
                "jsonrpc": "2.0",
                "id": int(time.time()),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            # Execute test
            process = subprocess.Popen(
                ["./mcp-server-macos-use/.build/arm64-apple-macosx/release/mcp-server-macos-use"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd="."
            )
            
            stdout, stderr = process.communicate(
                input=json.dumps(input_data) + "\n",
                timeout=15
            )
            
            test_duration = time.time() - test_start
            
            # Parse response
            try:
                response = json.loads(stdout)
                is_success = process.returncode == 0 and not response.get("result", {}).get("isError", True)
                content = response.get("result", {}).get("content", [{}])[0].get("text", "")
                
                # Deep validation
                validation_result = self.validate_response(tool_name, content, test_type)
                
                result = {
                    "tool": tool_name,
                    "test_type": test_type,
                    "status": "success" if is_success else "error",
                    "duration": test_duration,
                    "content": content[:500],  # Truncate for readability
                    "validation": validation_result,
                    "response_time": test_duration,
                    "stderr": stderr[:200] if stderr else ""
                }
                
            except json.JSONDecodeError as e:
                result = {
                    "tool": tool_name,
                    "test_type": test_type,
                    "status": "error",
                    "duration": test_duration,
                    "content": f"JSON decode error: {e!s}",
                    "validation": {"valid": False, "issues": ["JSON parsing failed"]},
                    "response_time": test_duration,
                    "stderr": stderr[:200] if stderr else ""
                }
                
        except subprocess.TimeoutExpired:
            result = {
                "tool": tool_name,
                "test_type": test_type,
                "status": "timeout",
                "duration": 15.0,
                "content": "Test timed out after 15 seconds",
                "validation": {"valid": False, "issues": ["Timeout"]},
                "response_time": 15.0,
                "stderr": "Timeout error"
            }
            
        except Exception as e:
            result = {
                "tool": tool_name,
                "test_type": test_type,
                "status": "error",
                "duration": time.time() - test_start,
                "content": f"Exception: {e!s}",
                "validation": {"valid": False, "issues": [str(e)]},
                "response_time": time.time() - test_start,
                "stderr": str(e)
            }
        
        self.results.append(result)
        return result
    
    def validate_response(self, tool_name, content, test_type):
        """Deep validation of tool response"""
        issues = []
        
        # Basic validation
        if not content or content.strip() == "":
            issues.append("Empty or no content")
        
        # Tool-specific validation
        if "system_monitoring" in tool_name:
            try:
                data = json.loads(content)
                required_fields = ["metric", "duration", "current_usage"]
                for field in required_fields:
                    if field not in data:
                        issues.append(f"Missing required field: {field}")
            except:
                issues.append("Invalid JSON format")
        
        elif "process_management" in tool_name and test_type == "basic":
            try:
                data = json.loads(content)
                if not isinstance(data, list):
                    issues.append("Expected array of processes")
            except:
                issues.append("Invalid JSON format")
        
        elif "list_tools_dynamic" in tool_name:
            try:
                data = json.loads(content)
                if not isinstance(data, list):
                    issues.append("Expected array of tools")
                elif len(data) < 40:
                    issues.append(f"Expected 40+ tools, got {len(data)}")
            except:
                issues.append("Invalid JSON format")
        
        # Performance validation
        if any(keyword in content.lower() for keyword in ["error", "failed", "denied"]):
            issues.append("Contains error indicators")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    async def run_comprehensive_tests(self):
        """Run comprehensive test suite for all tools"""
        print("🧪 Starting Comprehensive macOS MCP Server Test Suite")
        print("=" * 70)
        
        # Define all test cases
        test_cases = [
            # Basic Automation Tests
            ("macos-use_open_application_and_traverse", {"identifier": "Finder"}, "basic"),
            ("macos-use_click_and_traverse", {"x": 100, "y": 100}, "basic"),
            ("macos-use_right_click_and_traverse", {"x": 100, "y": 100}, "basic"),
            ("macos-use_double_click_and_traverse", {"x": 100, "y": 100}, "basic"),
            ("macos-use_type_and_traverse", {"text": "Hello World"}, "basic"),
            ("macos-use_press_key_and_traverse", {"keyName": "return"}, "basic"),
            ("macos-use_scroll_and_traverse", {"direction": "down", "amount": 3}, "basic"),
            ("macos-use_refresh_traversal", {"pid": 0}, "basic"),
            ("macos-use_window_management", {"action": "list"}, "basic"),
            
            # System Control Tests
            ("macos-use_system_control", {"action": "get_info"}, "basic"),
            ("macos-use_system_control", {"action": "volume_up"}, "action"),
            ("macos-use_system_control", {"action": "brightness_down"}, "action"),
            ("macos-use_fetch_url", {"url": "https://www.apple.com"}, "basic"),
            ("macos-use_get_time", {"timezone": "UTC", "format": "readable"}, "basic"),
            ("macos-use_get_time", {"timezone": "Europe/Kyiv", "format": "iso"}, "timezone"),
            ("macos-use_countdown", {"seconds": 3, "message": "Test complete"}, "basic"),
            
            # AppleScript Tests
            ("macos-use_applescript", {"script": "tell application \"Finder\" to get name"}, "basic"),
            ("macos-use_applescript", {"script": "tell application \"System Events\" to get name"}, "system"),
            ("macos-use_applescript_templates", {"list": True}, "basic"),
            ("macos-use_applescript_templates", {"create": True, "name": "test", "script": "tell application \"Finder\" to beep"}, "create"),
            
            # Calendar Tests
            ("macos-use_calendar_events", {"start": "2026-02-10T00:00:00Z", "end": "2026-02-10T23:59:59Z"}, "basic"),
            ("macos-use_create_event", {"title": "Test Event", "date": "2026-02-10T15:00:00Z"}, "basic"),
            
            # Reminders Tests
            ("macos-use_reminders", {}, "basic"),
            ("macos-use_create_reminder", {"title": "Test Reminder"}, "basic"),
            
            # Notification Tests
            ("macos-use_notification", {"title": "Test", "body": "Testing notifications"}, "basic"),
            ("macos-use_notification_schedule", {"title": "Scheduled", "body": "In 5 seconds", "delay": 5}, "schedule"),
            
            # Notes Tests
            ("macos-use_notes_list_folders", {}, "basic"),
            ("macos-use_notes_create", {"folder": "Test", "title": "Test Note", "content": "Test content"}, "basic"),
            ("macos-use_notes_get", {"note": "Test Note"}, "basic"),
            
            # Mail Tests
            ("macos-use_mail_send", {"to": "test@example.com", "subject": "Test", "body": "Test"}, "basic"),
            ("macos-use_mail_read", {"limit": 5}, "basic"),
            
            # Finder Tests
            ("macos-use_finder_list_files", {"path": "/tmp", "limit": 10}, "basic"),
            ("macos-use_finder_get_selection", {}, "basic"),
            ("macos-use_finder_open_path", {"path": "/tmp"}, "basic"),
            ("macos-use_finder_move_to_trash", {"path": "/tmp/test_file.txt"}, "basic"),
            
            # System Info Tests
            ("macos-use_list_running_apps", {}, "basic"),
            ("macos-use_list_browser_tabs", {"browser": "Safari"}, "basic"),
            ("macos-use_list_all_windows", {}, "basic"),
            
            # Clipboard Tests
            ("macos-use_set_clipboard", {"text": "Test clipboard content", "addToHistory": True}, "basic"),
            ("macos-use_get_clipboard", {}, "basic"),
            ("macos-use_clipboard_history", {"action": "list", "limit": 5}, "basic"),
            ("macos-use_clipboard_history", {"action": "clear"}, "action"),
            
            # Screenshot & OCR Tests
            ("macos-use_take_screenshot", {"path": "/tmp/test_screenshot.png", "format": "png"}, "basic"),
            ("macos-use_take_screenshot", {"path": "/tmp/test_screenshot.jpg", "format": "jpg"}, "format"),
            ("macos-use_perform_ocr", {"imagePath": "/tmp/test_screenshot.png"}, "basic"),
            ("macos-use_analyze_ui", {"imagePath": "/tmp/test_screenshot.png"}, "basic"),
            
            # NEW: Advanced Tools
            ("macos-use_voice_control", {"command": "open safari", "language": "en-US", "confidence": 0.7}, "basic"),
            ("macos-use_voice_control", {"command": "take screenshot", "language": "en-US"}, "voice"),
            ("macos-use_process_management", {"action": "list"}, "basic"),
            ("macos-use_process_management", {"action": "monitor", "duration": 3}, "monitoring"),
            ("macos-use_process_management", {"action": "priority", "pid": 1, "priority": "high"}, "priority"),
            ("macos-use_file_encryption", {"action": "encrypt", "path": "/tmp/test.txt", "password": "test123", "algorithm": "AES256"}, "basic"),
            ("macos-use_file_encryption", {"action": "decrypt", "path": "/tmp/test.txt.encrypted", "password": "test123"}, "decrypt"),
            ("macos-use_system_monitoring", {"metric": "cpu", "duration": 5}, "basic"),
            ("macos-use_system_monitoring", {"metric": "memory", "duration": 5}, "memory"),
            ("macos-use_system_monitoring", {"metric": "all", "duration": 3}, "comprehensive"),
            ("macos-use_system_monitoring", {"metric": "cpu", "duration": 5, "alert": True, "threshold": 50.0}, "alert"),
            ("macos-use_list_tools_dynamic", {}, "basic"),
            ("macos-use_list_tools_dynamic", {"search": "screenshot"}, "search"),
            
            # Shell & Terminal Tests
            ("macos-use_execute_command", {"command": "echo 'Hello from shell'", "timeout": 5}, "basic"),
            ("macos-use_execute_command", {"command": "ls -la /tmp", "timeout": 5}, "listing"),
            ("macos-use_open_terminal", {"command": "echo 'Terminal test'", "execute": False}, "basic"),
            ("macos-use_open_terminal", {"command": "echo 'Auto execute'", "execute": True}, "execute"),
            
            # Spotlight Tests
            ("macos-use_spotlight_search", {"query": "test", "limit": 10}, "basic"),
            ("macos-use_spotlight_search", {"query": "*.png", "limit": 5}, "filetype"),
        ]
        
        print(f"📊 Running {len(test_cases)} comprehensive tests...")
        print()
        
        # Run all tests
        for i, (tool_name, params, test_type) in enumerate(test_cases, 1):
            print(f"🧪 Test {i:3d}/{len(test_cases)}: {tool_name} ({test_type})")
            print(f"   📋 Parameters: {params}")
            
            result = await self.run_test(tool_name, params, test_type)
            
            if result["status"] == "success":
                print(f"   ✅ Success ({result['duration']:.2f}s)")
                if result["validation"]["valid"]:
                    print("   🔍 Validation: ✅ Passed")
                else:
                    print(f"   🔍 Validation: ⚠️ {result['validation']['issues']}")
            else:
                print(f"   ❌ {result['status'].upper()} ({result['duration']:.2f}s)")
                if result["validation"]["issues"]:
                    print(f"   🔍 Issues: {result['validation']['issues']}")
            
            print()
            
            # Small delay between tests
            await asyncio.sleep(0.2)
        
        # Generate comprehensive report
        self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        success_count = sum(1 for r in self.results if r["status"] == "success")
        error_count = sum(1 for r in self.results if r["status"] == "error")
        timeout_count = sum(1 for r in self.results if r["status"] == "timeout")
        
        # Calculate statistics
        response_times = [r["response_time"] for r in self.results if r["response_time"] > 0]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        
        # Categorize results
        categories = {
            "automation": [],
            "system": [],
            "apple_script": [],
            "productivity": [],
            "security": [],
            "advanced": []
        }
        
        for result in self.results:
            tool_name = result["tool"]
            if any(keyword in tool_name for keyword in ["click", "type", "press", "scroll", "drag"]):
                categories["automation"].append(result)
            elif any(keyword in tool_name for keyword in ["system_control", "get_time", "countdown"]):
                categories["system"].append(result)
            elif "applescript" in tool_name:
                categories["apple_script"].append(result)
            elif any(keyword in tool_name for keyword in ["calendar", "reminders", "notes", "mail", "notification"]):
                categories["productivity"].append(result)
            elif any(keyword in tool_name for keyword in ["finder", "spotlight", "execute_command"]):
                categories["security"].append(result)
            else:
                categories["advanced"].append(result)
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": len(self.results),
                "successful": success_count,
                "errors": error_count,
                "timeouts": timeout_count,
                "success_rate": (success_count / len(self.results)) * 100,
                "total_duration": total_duration
            },
            "performance": {
                "average_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "min_response_time": min_response_time,
                "response_times": response_times
            },
            "categories": {},
            "detailed_results": self.results,
            "recommendations": self.generate_recommendations()
        }
        
        # Add category statistics
        for cat_name, cat_results in categories.items():
            cat_success = sum(1 for r in cat_results if r["status"] == "success")
            report["categories"][cat_name] = {
                "total": len(cat_results),
                "successful": cat_success,
                "success_rate": (cat_success / len(cat_results)) * 100 if cat_results else 0
            }
        
        # Save report
        with open('/tmp/comprehensive_test_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_summary(report)
    
    def print_summary(self, report):
        """Print comprehensive test summary"""
        print("=" * 70)
        print("🎉 COMPREHENSIVE TEST SUITE COMPLETE!")
        print("=" * 70)
        
        summary = report["summary"]
        perf = report["performance"]
        
        print("📊 SUMMARY:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   ✅ Successful: {summary['successful']}")
        print(f"   ❌ Errors: {summary['errors']}")
        print(f"   ⏱️ Timeouts: {summary['timeouts']}")
        print(f"   🎯 Success Rate: {summary['success_rate']:.1f}%")
        print(f"   ⏱️ Total Duration: {summary['total_duration']:.2f}s")
        print()
        
        print("⚡ PERFORMANCE:")
        print(f"   Avg Response Time: {perf['average_response_time']:.3f}s")
        print(f"   Max Response Time: {perf['max_response_time']:.3f}s")
        print(f"   Min Response Time: {perf['min_response_time']:.3f}s")
        print()
        
        print("📈 CATEGORIES:")
        for cat_name, cat_stats in report["categories"].items():
            print(f"   {cat_name.title()}: {cat_stats['successful']}/{cat_stats['total']} ({cat_stats['success_rate']:.1f}%)")
        print()
        
        print("🔧 RECOMMENDATIONS:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")
        print()
        
        print("📄 Detailed results saved to: /tmp/comprehensive_test_results.json")
        print("=" * 70)
    
    def generate_recommendations(self):
        """Generate improvement recommendations"""
        recommendations = []
        
        # Analyze common issues
        error_tools = [r["tool"] for r in self.results if r["status"] == "error"]
        timeout_tools = [r["tool"] for r in self.results if r["status"] == "timeout"]
        
        if timeout_tools:
            recommendations.append(f"Fix timeout issues for: {', '.join(timeout_tools[:3])}")
        
        if len(error_tools) > 5:
            recommendations.append(f"High error rate in: {', '.join(error_tools[:3])}")
        
        # Performance recommendations
        slow_tools = [r["tool"] for r in self.results if r["response_time"] > 5.0]
        if slow_tools:
            recommendations.append(f"Optimize slow tools: {', '.join(slow_tools[:3])}")
        
        # Validation recommendations
        validation_issues = sum(1 for r in self.results if not r["validation"]["valid"])
        if validation_issues > 0:
            recommendations.append(f"Fix {validation_issues} validation issues")
        
        if not recommendations:
            recommendations.append("All tools performing well!")
        
        return recommendations

async def main():
    """Main test runner"""
    tester = ComprehensiveTester()
    await tester.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())
