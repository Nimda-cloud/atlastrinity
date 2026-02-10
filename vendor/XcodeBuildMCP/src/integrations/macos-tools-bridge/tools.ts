
import { z } from 'zod';

export interface EnhancedToolDefinition {
  name: string;
  description: string;
  macosToolName: string;
  schema: z.ZodObject<any>;
}

export const ENHANCED_TOOLS: EnhancedToolDefinition[] = [
  // UI Automation
  {
    name: 'enhanced_tap',
    description: 'Tap with accessibility traversal for reliable UI interaction',
    macosToolName: 'macos-use_click_and_traverse',
    schema: z.object({
      x: z.number().describe('The x-coordinate of the click'),
      y: z.number().describe('The y-coordinate of the click'),
      pid: z.number().optional().describe('Optional process ID to target'),
    }),
  },
  {
    name: 'enhanced_type_text',
    description: 'Type text with real-time feedback and validation',
    macosToolName: 'macos-use_type_and_traverse',
    schema: z.object({
      text: z.string().describe('The text to type'),
      pid: z.number().optional().describe('Optional process ID to target'),
    }),
  },
  {
    name: 'enhanced_key_press',
    description: 'Press keys with modifier support and traversal integration',
    macosToolName: 'macos-use_press_key_and_traverse',
    schema: z.object({
      keyName: z.string().describe('The name of the key to press (e.g., "return", "tab", "c")'),
      pid: z.number().optional().describe('Optional process ID to target'),
    }),
  },
  
  // Visual Testing / Screenshots
  {
    name: 'enhanced_screenshot',
    description: 'Take high-quality screenshots with region selection, compression, and OCR support',
    macosToolName: 'macos-use_take_screenshot',
    schema: z.object({
      path: z.string().optional().describe('Absolute path to save the screenshot'),
      region: z.object({
        x: z.number(),
        y: z.number(),
        width: z.number(),
        height: z.number(),
      }).optional().describe('Optional region to capture'),
      monitor: z.number().optional().describe('Optional monitor index (0 for main)'),
      quality: z.enum(['low', 'medium', 'high', 'lossless']).optional().describe('Compression quality'),
      format: z.enum(['png', 'jpg', 'webp']).optional().describe('Image format (default: png)'),
      ocr: z.boolean().optional().describe('Run OCR on screenshot and return text'),
    }),
  },
  {
    name: 'ocr_analysis',
    description: 'Perform OCR (text recognition) on the screen or a specific region',
    macosToolName: 'macos-use_analyze_screen',
    schema: z.object({
      region: z.object({
        x: z.number(),
        y: z.number(),
        width: z.number(),
        height: z.number(),
      }).optional().describe('Optional region to analyze'),
      language: z.enum(['en', 'uk', 'ru', 'auto']).optional().describe('Language hint (default: auto)'),
      confidence: z.boolean().optional().describe('Include confidence scores (default: false)'),
      format: z.enum(['json', 'text', 'both']).optional().describe('Output format (default: both)'),
    }),
  },
  {
    name: 'ui_analysis',
    description: 'Analyze UI elements on the screen or a specific region',
    macosToolName: 'macos-use_analyze_screen',
    schema: z.object({
      region: z.object({
        x: z.number(),
        y: z.number(),
        width: z.number(),
        height: z.number(),
      }).optional().describe('Optional region to analyze'),
      format: z.enum(['json', 'text', 'both']).optional().describe('Output format (default: both)'),
    }),
  },

  // System Monitoring
  {
    name: 'system_monitor',
    description: 'Monitor system resources (CPU, Memory, Disk, Network)',
    macosToolName: 'macos-use_system_monitoring',
    schema: z.object({
      metric: z.enum(['cpu', 'memory', 'disk', 'network', 'all']).describe('Metric to monitor'),
      duration: z.number().optional().describe('Duration in seconds to monitor'),
    }),
  },
  
  // Process Management
  {
      name: 'process_manager',
      description: 'List and manage running processes',
      macosToolName: 'macos-use_process_management',
      schema: z.object({
          action: z.enum(['list', 'monitor']).describe('Action to perform'),
          duration: z.number().optional().describe('Duration for monitoring in seconds')
      })
  },

  // File Operations
  {
    name: 'enhanced_list_files',
    description: 'List files using Finder with enhanced filtering',
    macosToolName: 'macos-use_finder_list_files',
    schema: z.object({
      path: z.string().describe('Directory path to list'),
      limit: z.number().optional().describe('Maximum number of items to return'),
    }),
  },
  {
      name: 'enhanced_open_path',
      description: 'Open a file or directory using Finder',
      macosToolName: 'macos-use_finder_open_path',
      schema: z.object({
          path: z.string().describe('Path to open')
      })
  },

  // Clipboard
  {
    name: 'enhanced_clipboard',
    description: 'Get or set clipboard content with history and rich text support',
    macosToolName: 'macos-use_set_clipboard',
    schema: z.object({
      text: z.string().describe('Text to copy to clipboard'),
      html: z.string().optional().describe('Optional HTML content'),
      image: z.string().optional().describe('Optional base64 image data'),
      addToHistory: z.boolean().optional().describe('Whether to add to history (default: true)'),
      showAnimation: z.boolean().optional().describe('Show visual feedback (default: true)'),
    }),
  },
  
  // Voice Control
  {
      name: 'voice_control',
      description: 'Execute voice commands for hands-free development',
      macosToolName: 'macos-use_voice_control',
      schema: z.object({
          command: z.string().describe('Voice command to execute'),
          language: z.string().optional().describe('Language code (default: en-US)')
      })
  },

  // Discovery
  {
      name: 'list_macos_tools',
      description: 'List all available macOS tools dynamically',
      macosToolName: 'macos-use_list_tools_dynamic',
      schema: z.object({})
  }
];
