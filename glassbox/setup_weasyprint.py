"""
setup_weasyprint.py — WeasyPrint Dependency Checker

Checks if WeasyPrint and its native library dependencies are available.
Provides platform-specific installation guidance.

Usage:
    python setup_weasyprint.py --check        # Check current status
    python setup_weasyprint.py --setup        # Attempt automatic setup (if supported)
"""
import os
import platform
import subprocess
import sys


class WeasyPrintChecker:
    """Dependency checker for WeasyPrint on various platforms."""

    def __init__(self):
        self.system = platform.system()  # 'Windows', 'Linux', 'Darwin'
        self.python_exe = sys.executable

    def check_weasyprint(self) -> dict:
        """
        Comprehensive check of WeasyPrint and its dependencies.

        Returns:
            {
                'available': bool,
                'weasyprint_version': str or None,
                'native_libs': {'lib_name': bool, ...},
                'missing_libs': [str, ...],
                'platform': str,
                'repair_url': str,
            }
        """
        result = {
            'available': False,
            'weasyprint_version': None,
            'native_libs': {},
            'missing_libs': [],
            'platform': self.system,
            'repair_url': 'https://github.com/Functional-Intelligence-Research-Lab/twff/blob/main/WEASYPRINT_SETUP.md',
        }

        # Step 1: Check native library availability first (before importing weasyprint)
        if self.system == 'Windows':
            result['native_libs'] = self._check_windows_libs()
        elif self.system == 'Linux':
            result['native_libs'] = self._check_linux_libs()
        elif self.system == 'Darwin':
            result['native_libs'] = self._check_macos_libs()

        # Identify missing libs
        result['missing_libs'] = [lib for lib, available in result['native_libs'].items() if not available]

        # Step 2: Check if weasyprint module imports (only if native libs OK)
        if not result['missing_libs']:
            try:
                import weasyprint
                result['weasyprint_version'] = weasyprint.__version__
            except ImportError as e:
                result['missing_libs'].append(f"weasyprint module: {e}")
            except Exception as e:
                result['missing_libs'].append(f"weasyprint import error: {e}")
        else:
            result['missing_libs'].insert(0, "weasyprint (cannot import - missing native libraries)")

        # Overall availability
        result['available'] = len(result['missing_libs']) == 0

        return result

    def _check_windows_libs(self) -> dict:
        """Check for Windows native libraries via ctypes.util.find_library()."""
        import ctypes.util
        libs_to_check = [
            'gobject-2.0-0',      # GObject
            'glib-2.0-0',         # GLib
            'pango-1.0-0',        # Pango
            'cairo-2',            # Cairo
            'fontconfig',         # Fontconfig
        ]
        result = {}
        for lib in libs_to_check:
            found = ctypes.util.find_library(lib) is not None
            result[lib] = found
        return result

    def _check_linux_libs(self) -> dict:
        """Check for Linux native libraries."""
        import ctypes.util
        libs_to_check = ['gobject-2.0', 'pango-1.0', 'cairo']
        result = {}
        for lib in libs_to_check:
            found = ctypes.util.find_library(lib) is not None
            result[lib] = found
        return result

    def _check_macos_libs(self) -> dict:
        """Check for macOS native libraries via Homebrew or system."""
        import ctypes.util
        libs_to_check = ['gobject-2.0', 'pango-1.0', 'cairo']
        result = {}
        for lib in libs_to_check:
            found = ctypes.util.find_library(lib) is not None
            result[lib] = found
        return result

    def report(self, check_result: dict) -> str:
        """Format a human-readable report of the check."""
        lines = []
        lines.append("=" * 60)
        lines.append("WeasyPrint Dependency Check")
        lines.append("=" * 60)
        lines.append(f"Platform: {check_result['platform']}")
        lines.append(f"Python: {sys.version}")

        if check_result['weasyprint_version']:
            lines.append(f"WeasyPrint: ✓ v{check_result['weasyprint_version']}")
        else:
            lines.append("WeasyPrint: ✗ NOT INSTALLED")

        if check_result['native_libs']:
            lines.append("\nNative Libraries:")
            for lib, available in check_result['native_libs'].items():
                status = "✓" if available else "✗"
                lines.append(f"  {status} {lib}")

        if check_result['available']:
            lines.append("\n✓ WeasyPrint is fully functional!")
        else:
            lines.append("\n✗ WeasyPrint is NOT fully functional.")
            if check_result['missing_libs']:
                lines.append("\nMissing components:")
                for lib in check_result['missing_libs']:
                    lines.append(f"  • {lib}")

        lines.append(f"\nSetup guide: {check_result['repair_url']}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_platform_instructions(self) -> str:
        """Return platform-specific installation instructions."""
        instructions = {
            'Windows': """
WINDOWS SETUP (Recommended: MSYS2)
==================================
1. Download MSYS2 from https://www.msys2.org/
2. Run the installer and follow the prompts
3. Open MSYS2 terminal and run:
   pacman -S mingw-w64-x86_64-pango

4. Close MSYS2, then in Windows cmd/PowerShell:
   set WEASYPRINT_DLL_DIRECTORIES=C:\\msys64\\mingw64\\bin
   python -m pip install weasyprint

5. Verify:
   python setup_weasyprint.py --check

Alternative (Docker):
   docker pull luca-vercelli/weasyprint
   See full guide for details.
""",
            'Linux': """
LINUX SETUP
===========
Most distributions have Pango/Cairo in standard repos.

Ubuntu/Debian:
   sudo apt-get install libpango-1.0-0 libcairo2 libgobject-2.0-0
   python -m pip install weasyprint

Fedora/RHEL:
   sudo dnf install pango cairo gobject-introspection
   python -m pip install weasyprint

Verify:
   python setup_weasyprint.py --check
""",
            'Darwin': """
MACOS SETUP
===========
Using Homebrew (recommended):
   brew install pango cairo
   python -m pip install weasyprint

Or using conda:
   conda install -c conda-forge pango cairo

Verify:
   python setup_weasyprint.py --check
""",
        }
        return instructions.get(self.system, "Platform not recognized. See WEASYPRINT_SETUP.md")

    @staticmethod
    def set_environment_windows():
        """Set WEASYPRINT_DLL_DIRECTORIES for Windows MSYS2 setup."""
        msys2_path = r"C:\msys64\mingw64\bin"
        if os.path.exists(msys2_path):
            os.environ['WEASYPRINT_DLL_DIRECTORIES'] = msys2_path
            return True
        return False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WeasyPrint Dependency Checker")
    parser.add_argument(
        '--check', action='store_true',
        help="Check WeasyPrint dependency status"
    )
    parser.add_argument(
        '--setup', action='store_true',
        help="Show setup instructions for your platform"
    )
    parser.add_argument(
        '--set-env', action='store_true',
        help="(Windows only) Set WEASYPRINT_DLL_DIRECTORIES environment variable"
    )

    args = parser.parse_args()

    checker = WeasyPrintChecker()

    if args.set_env:
        if checker.system == 'Windows':
            if checker.set_environment_windows():
                print("✓ WEASYPRINT_DLL_DIRECTORIES set for MSYS2")
            else:
                print("✗ MSYS2 not found at C:\\msys64\\mingw64\\bin")
        else:
            print("--set-env only applies to Windows")
        return

    if args.check:
        result = checker.check_weasyprint()
        print(checker.report(result))
        sys.exit(0 if result['available'] else 1)

    if args.setup:
        print(checker.get_platform_instructions())
        return

    # Default: run check
    result = checker.check_weasyprint()
    print(checker.report(result))
    sys.exit(0 if result['available'] else 1)


if __name__ == '__main__':
    main()
