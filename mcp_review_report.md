# MCP Server Review

Generated at: "3030.020261916"

## ✅ macos-use (Tier 1)
- **Status**: OK
- **Tools**: 5

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| macos-use_open_application_and_traverse | Yes | Yes | Opens/activates an application and then traverses ... |
| macos-use_click_and_traverse | Yes | Yes | Simulates a click at the given coordinates within ... |
| macos-use_type_and_traverse | Yes | Yes | Simulates typing text into the app specified by PI... |
| macos-use_press_key_and_traverse | Yes | Yes | Simulates pressing a specific key (like Return, En... |
| macos-use_refresh_traversal | Yes | Yes | Traverses the accessibility tree of the applicatio... |

## ✅ filesystem (Tier 1)
- **Status**: OK
- **Tools**: 14

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| read_file | Yes | Yes | Read the complete contents of a file as text. DEPR... |
| read_text_file | Yes | Yes | Read the complete contents of a file from the file... |
| read_media_file | Yes | Yes | Read an image or audio file. Returns the base64 en... |
| read_multiple_files | Yes | Yes | Read the contents of multiple files simultaneously... |
| write_file | Yes | Yes | Create a new file or completely overwrite an exist... |
| edit_file | Yes | Yes | Make line-based edits to a text file. Each edit re... |
| create_directory | Yes | Yes | Create a new directory or ensure a directory exist... |
| list_directory | Yes | Yes | Get a detailed listing of all files and directorie... |
| list_directory_with_sizes | Yes | Yes | Get a detailed listing of all files and directorie... |
| directory_tree | Yes | Yes | Get a recursive tree view of files and directories... |
| move_file | Yes | Yes | Move or rename files and directories. Can move fil... |
| search_files | Yes | Yes | Recursively search for files and directories match... |
| get_file_info | Yes | Yes | Retrieve detailed metadata about a file or directo... |
| list_allowed_directories | Yes | Yes | Returns the list of directories that this server i... |

## ✅ fetch (Tier 2)
- **Status**: OK
- **Tools**: 0

## ✅ terminal (Tier 1)
- **Status**: OK
- **Tools**: 0

## ✅ sequential-thinking (Tier 1)
- **Status**: OK
- **Tools**: 1

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| sequentialthinking | Yes | Yes | A detailed tool for dynamic and reflective problem... |

## ✅ chrome-devtools (Tier 2)
- **Status**: OK
- **Tools**: 26

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| click | Yes | Yes | Clicks on the provided element... |
| close_page | Yes | Yes | Closes the page by its index. The last open page c... |
| drag | Yes | Yes | Drag an element onto another element... |
| emulate | Yes | Yes | Emulates various features on the selected page.... |
| evaluate_script | Yes | Yes | Evaluate a JavaScript function inside the currentl... |
| fill | Yes | Yes | Type text into a input, text area or select an opt... |
| fill_form | Yes | Yes | Fill out multiple form elements at once... |
| get_console_message | Yes | Yes | Gets a console message by its ID. You can get all ... |
| get_network_request | Yes | Yes | Gets a network request by an optional reqid, if om... |
| handle_dialog | Yes | Yes | If a browser dialog was opened, use this command t... |
| hover | Yes | Yes | Hover over the provided element... |
| list_console_messages | Yes | Yes | List all console messages for the currently select... |
| list_network_requests | Yes | Yes | List all requests for the currently selected page ... |
| list_pages | Yes | Yes | Get a list of pages open in the browser.... |
| navigate_page | Yes | Yes | Navigates the currently selected page to a URL.... |
| new_page | Yes | Yes | Creates a new page... |
| performance_analyze_insight | Yes | Yes | Provides more detailed information on a specific P... |
| performance_start_trace | Yes | Yes | Starts a performance trace recording on the select... |
| performance_stop_trace | Yes | Yes | Stops the active performance trace recording on th... |
| press_key | Yes | Yes | Press a key or key combination. Use this when othe... |
| resize_page | Yes | Yes | Resizes the selected page's window so that the pag... |
| select_page | Yes | Yes | Select a page as a context for future tool calls.... |
| take_screenshot | Yes | Yes | Take a screenshot of the page or element.... |
| take_snapshot | Yes | Yes | Take a text snapshot of the currently selected pag... |
| upload_file | Yes | Yes | Upload a file through a provided element.... |
| wait_for | Yes | Yes | Wait for the specified text to appear on the selec... |

## ✅ git (Tier 2)
- **Status**: OK
- **Tools**: 0

## ✅ vibe (Tier 2)
- **Status**: OK
- **Tools**: 0

## ✅ memory (Tier 2)
- **Status**: OK
- **Tools**: 0

## ✅ apple-mcp (Tier 3)
- **Status**: OK
- **Tools**: 7

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| contacts | Yes | Yes | Search and retrieve contacts from Apple Contacts a... |
| notes | Yes | Yes | Search, retrieve and create notes in Apple Notes a... |
| messages | Yes | Yes | Interact with Apple Messages app - send, read, sch... |
| mail | Yes | Yes | Interact with Apple Mail app - read unread emails,... |
| reminders | Yes | Yes | Search, create, and open reminders in Apple Remind... |
| calendar | Yes | Yes | Search, create, and open calendar events in Apple ... |
| maps | Yes | Yes | Search locations, manage guides, save favorites, a... |

## ✅ github (Tier 3)
- **Status**: OK
- **Tools**: 0

## ✅ duckduckgo-search (Tier 3)
- **Status**: OK
- **Tools**: 0

## ✅ context7 (Tier 4)
- **Status**: OK
- **Tools**: 2

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| resolve-library-id | Yes | Yes | Resolves a package/product name to a Context7-comp... |
| get-library-docs | Yes | Yes | Fetches up-to-date documentation for a library. Yo... |

## ✅ whisper-stt (Tier 4)
- **Status**: OK
- **Tools**: 0

## ✅ docker (Tier 4)
- **Status**: OK
- **Tools**: 0

## ✅ postgres (Tier 4)
- **Status**: OK
- **Tools**: 1

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| query | Yes | Yes | Run a read-only SQL query... |

## ✅ slack (Tier 4)
- **Status**: OK
- **Tools**: 8

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| slack_list_channels | Yes | Yes | List public or pre-defined channels in the workspa... |
| slack_post_message | Yes | Yes | Post a new message to a Slack channel... |
| slack_reply_to_thread | Yes | Yes | Reply to a specific message thread in Slack... |
| slack_add_reaction | Yes | Yes | Add a reaction emoji to a message... |
| slack_get_channel_history | Yes | Yes | Get recent messages from a channel... |
| slack_get_thread_replies | Yes | Yes | Get all replies in a message thread... |
| slack_get_users | Yes | Yes | Get a list of all users in the workspace with thei... |
| slack_get_user_profile | Yes | Yes | Get detailed profile information for a specific us... |

## ✅ graph (Tier 4)
- **Status**: OK
- **Tools**: 0

## ✅ time (Tier 4)
- **Status**: OK
- **Tools**: 6

| Tool | Desc? | Schema? | Preview |
|---|---|---|---|
| current_time | Yes | Yes | Get current time in UTC and specified timezone... |
| relative_time | Yes | Yes | Calculate relative time from now to a given time s... |
| days_in_month | Yes | Yes | Get the number of days in a month... |
| get_timestamp | Yes | Yes | Convert a date-time string to Unix timestamp in mi... |
| convert_time | Yes | Yes | Convert time between different IANA timezones... |
| get_week_year | Yes | Yes | Get week number and ISO week number for a date... |

## ✅ notes (Tier 2)
- **Status**: OK
- **Tools**: 0

