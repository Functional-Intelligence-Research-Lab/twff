# WeasyPrint Setup Guide

WeasyPrint requires native graphics libraries (Pango, Cairo, GObject) in addition to the Python package. These vary by platform. Glass Box uses WeasyPrint or ReportLab for PDF export, so you only need to set up one of them. This guide focuses on WeasyPrint, which provides better CSS support and would be the recommended option for most users.

> **Note:** If you prefer ReportLab, you can install it via `pip install reportlab` without additional native dependencies. However, WeasyPrint is the default and recommended PDF engine for Glass Box.
> This is espeacially important for windows as Weasyprint's installation on windows is more complex than ReportLab's, but it provides better PDF output quality and CSS support.

## Quick Check

Before installing, verify your current setup:

```bash
cd glassbox
python setup_weasyprint.py --check
```

If it shows ✓ for all components, you're ready to use PDF export.

---

## Platform-Specific Setup

### Windows (Recommended: MSYS2)

**Official WeasyPrint recommendation as of v63.0.**

#### Step 1: Install MSYS2

1. Download from: https://www.msys2.org/
2. Run the installer, choose `C:\msys64` as install location (default)
3. Launch **MSYS2 MinGW 64-bit terminal** (or x86 for 32-bit Python)

#### Step 2: Install Pango & Dependencies

In the MSYS2 terminal:

```bash
pacman -S mingw-w64-x86_64-pango
```

**For 32-bit Python:**
```bash
pacman -S mingw-w64-i686-pango
```

This automatically installs Cairo, GObject, and related libraries.

#### Step 3: Install WeasyPrint in Python

**Close MSYS2**, then in Windows `cmd.exe` or PowerShell:

```bash
cd \path\to\twff\glassbox
python -m pip install weasyprint

# Optional: Set environment variable (permanent setup)
set WEASYPRINT_DLL_DIRECTORIES=C:\msys64\mingw64\bin

# Or run the helper:
python setup_weasyprint.py --set-env
```

#### Step 4: Verify

```bash
python setup_weasyprint.py --check
```

Should show: ✓ WeasyPrint is fully functional!

---

### Linux

Native package managers have up-to-date Pango/Cairo packages.

#### Ubuntu / Debian

```bash
sudo apt-get update
sudo apt-get install libpango-1.0-0 libcairo2 libgobject-2.0-0 libfontconfig1
python -m pip install weasyprint
```

#### Fedora / RHEL / CentOS

```bash
sudo dnf install pango cairo gobject-introspection fontconfig
python -m pip install weasyprint
```

#### Arch Linux

```bash
sudo pacman -S pango cairo gobject-introspection
python -m pip install weasyprint
```

#### Verify

```bash
python setup_weasyprint.py --check
```

---

### macOS

#### Using Homebrew (Recommended)

```bash
brew install pango cairo libffi
python -m pip install weasyprint
```

#### Using conda

```bash
conda install -c conda-forge pango cairo
python -m pip install weasyprint
```

#### Verify

```bash
python setup_weasyprint.py --check
```

---

## Alternative: Docker

If you want to avoid installing system libraries, use Docker:

```bash
docker run --rm \
  -v $(pwd):/input \
  -v $(pwd)/output:/output \
  luca-vercelli/weasyprint \
  weasyprint /input/document.html /output/document.pdf
```

See: https://github.com/luca-vercelli/WeasyPrint-docker-images

---

## Alternative: WSL2 (Windows Subsystem for Linux)

Run Ubuntu (or another Linux) in WSL2:

1. Install WSL2: https://docs.microsoft.com/en-us/windows/wsl/install
2. In WSL2 terminal, follow **Linux** steps above
3. Access files via `/mnt/c/` (e.g., `/mnt/c/Users/...`)

---

## Troubleshooting

### Error: `OSError: cannot load library 'libgobject-2.0-0'`

**Cause:** Native libraries not found.

**Solution:**
- **Windows:** Ensure MSYS2 Pango is installed and `WEASYPRINT_DLL_DIRECTORIES` is set
- **Linux:** Run `sudo apt-get install libgobject-2.0-0` (or equivalent)
- **macOS:** Run `brew install pango`

### Error: `ImportError: No module named 'weasyprint'`

**Cause:** Python package not installed.

**Solution:**
```bash
python -m pip install weasyprint
```

### PDF Export Button is Grayed Out

The app detected that WeasyPrint is unavailable. See the console for details:

```bash
python setup_weasyprint.py --check
```

Then follow the steps for your platform above.

### WeasyPrint works in terminal but not in Glass Box app

**Possible cause:** Different Python interpreter or virtual environment.

**Solution:**
```bash
# Verify you're using the right Python
which python  # or 'where python' on Windows
python -m pip list | grep weasyprint

# Run Glass Box with the same Python
python glassbox/app.py
```

---

## Size & Performance

| Platform | Total Size | Setup Time | Notes |
|----------|-----------|-----------|-------|
| Windows (MSYS2) | ~2.9 GB | 10–15 min | Package-managed, official |
| Linux | ~100–500 MB | 2–5 min | Usually pre-installed |
| macOS | ~500 MB–1 GB | 5–10 min | Homebrew is fastest |
| Docker | ~500 MB–1 GB | 3 min | No system pollution |

---

## Reference

- **WeasyPrint Docs:** https://doc.courtbouillon.org/weasyprint/
- **TWFF Repository:** https://github.com/Functional-Intelligence-Research-Lab/twff
- **GitHub Issues:** https://github.com/Functional-Intelligence-Research-Lab/twff/issues

---

## Questions?

If you encounter issues beyond the troubleshooting section, open an issue on GitHub with:
- Your OS and Python version
- Output of `python setup_weasyprint.py --check`
- Full error message and traceback
