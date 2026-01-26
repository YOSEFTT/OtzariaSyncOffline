## GitHub Workflows Rules
When reviewing files in `.github/workflows/`:
1. Ensure every job has a `timeout-minutes` set to prevent hanging builds.
2. Verify that we are pinning actions to specific SHAs (e.g., `uses: actions/checkout@a123...`) instead of tags like `@v3` for security.
3. Check for overly permissive permissions in the `permissions:` block.

# Python & PyQt Project Style Guide

## 1. Cross-Platform Compatibility (Windows, Linux, macOS/Apple Silicon)
*   **Paths:** Never use hardcoded path separators (`\` or `/`). Always use `pathlib.Path` or `os.path.join`.
    *   *Bad:* `open("data\\config.json")`
    *   *Good:* `open(Path("data") / "config.json")`
*   **Encoding:** Always specify `encoding='utf-8'` when opening files. Windows defaults to `cp1252` which will crash the app with Hebrew characters.
*   **Line Endings:** Be aware of CRLF (Windows) vs LF (Linux/Mac) when parsing synced files. Use universal newlines mode (default in Python) but verify when processing raw bytes.
*   **Apple Silicon:** Avoid libraries that rely on x86-only binary wheels if possible. When using `ctypes` or loading DLLs/dylibs, dynamically check the OS and architecture.

## 2. PyQt & GUI Best Practices
*   **Threading:** NEVER run network requests (GitHub Sync) or heavy file operations on the main thread.
    *   Use `QThread`, `QRunnable` with `QThreadPool`, or `asyncio` integrated with Qt loop.
    *   The UI must remain responsive (no freezing).
*   **Signals & Slots:** Use strict type hints for custom signals. Avoid connecting signals to lambdas with complex logic; define a separate method instead.
*   **Assets & Fonts:**
    *   Load fonts and icons using relative paths or the Qt Resource System (`.qrc`).
    *   Ensure fonts are bundled correctly so they work on systems where the font isn't installed globally.
*   **High DPI:** Ensure layouts use layouts (`QVBoxLayout`, `QGridLayout`) and not fixed pixel positioning, to support high-resolution screens (Retina/4K).

## 3. GitHub Sync & Networking
*   **Timeouts:** All network requests (GitHub API, downloading files) must have a defined `timeout`. Never hang indefinitely.
*   **Error Handling:** Wrap sync operations in `try/except` blocks.
    *   Handle `ConnectionError` and `Timeout` specifically.
    *   Show user-friendly messages in the GUI (e.g., via `QMessageBox` or a status bar) when sync fails, do not just print to console.
*   **Rate Limiting:** If iterating over many files from GitHub, ensure we handle API rate limits or use a delay between requests if necessary.

## 4. Code Quality & Formatting
*   **Type Hinting:** Use Python type hints (`def func(a: int) -> str:`) everywhere.
*   **Docstrings:** Document complex sync logic and custom widgets.
*   **Constants:** Do not hardcode GitHub URLs or API tokens. Use environment variables or a configuration file/class.

## 5. GitHub Workflows (CI/CD)
*   **Matrix Strategy:** When editing workflows, ensure tests run on `ubuntu-latest`, `windows-latest`, and `macos-latest`.
*   **Action Pinning:** Pin actions to specific commits or versions for security.

## 6. Packaging & PyInstaller Compatibility
*   **Resource Paths:**
    *   NEVER access asset files (fonts, images, icons, config templates) using direct relative paths like `open("assets/font.ttf")`.
    *   ALWAYS use a helper function to resolve paths that detects if the app is running in "frozen" mode (PyInstaller).
    *   *Requirement:* Code must check `getattr(sys, 'frozen', False)` and use `sys._MEIPASS` when applicable.
*   **Console Output:**
    *   Avoid using `print()` for error reporting. In the packaged windowed GUI (noconsole mode), standard output is lost.
    *   Use the Python `logging` module (writing to a file) or display critical errors to the user via `QMessageBox`.
*   **Dynamic Imports:**
    *   Avoid complex dynamic imports (`__import__` or `importlib`) unless necessary, as PyInstaller's static analysis might miss them, causing `ModuleNotFoundError` in the built executable.