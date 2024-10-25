# Installation

- The main branch always has the latest version. Download, install `requirements.txt`, and run `msiAlign.py`.
- The latest binary is available [here](https://github.com/weimin-liu/msiAlign/releases/latest).  
  **Note**: You may get a trojan warning due to a PyInstaller issue (see discussions 
  [here](https://stackoverflow.com/questions/43777106/program-made-with-pyinstaller-now-seen-as-a-trojan-horse-by-avg), 
  [here](https://stackoverflow.com/questions/64788656/exe-file-made-with-pyinstaller-being-reported-as-a-virus-threat-by-windows-defen), 
  and [here](https://github.com/pyinstaller/pyinstaller/issues/5854)).  
  It's a **false positive**; allow it to run in your antivirus settings.

# Known Bugs

- [ ] Binary post-25.10.2024 is incompatible with previous workspace versions. For older compatibility, use this binary version [here](https://github.com/weimin-liu/msiAlign/releases/tag/v1.0.2).
- [x] Fixed: Vertical lines may not delete properly.
- [x] Fixed: Teaching points don’t update when images move.
- [x] Fixed: Duplicate images re-added without warning.

# Usage Guide

## Quick Start

- **Metadata Database (for MSI only)**: Go to `File > Crawl Metadata` and select your directory.
- **Add Images**: Use `File > Add Images`, selecting whether it’s a reference image (for cm/pixel alignment).
- **Organize Images**: Drag images and resize. Use `Ctrl+Click` to add alignment lines.
- **Calculate cm/pixel**: Place vertical lines on ruler marks, right-click, set as "scale lines," and select `Calc > cm/Px`.
- **Sediment Start**: Right-click a vertical line and select "Sediment Start."
- **Teaching Points**: Add teaching points by `Shift+Click`. The distance from sediment start will auto-calculate.

### Preparing for Analysis
- **MSI Analysis**: Select `Calc > Prep MSI`, attach the metadata, and pair teaching points manually or automatically. Submit to calculate transformations.
- **XRF Analysis**: Similar steps as MSI. Specify XRF data path, and the program generates depth and mask data saved as a CSV.

### Depth Profile
- Go to `Calc > Downcore Profile` to generate depth profiles. Ensure MSI exports are named exactly after spectrum data (e.g., `xxxx.d` has `xxxx.d.txt`).

## Useful Functions
- **Save/Load Canvas**: Save workspace via `File > Save Workspace` (JSON file), reload with `File > Load Workspace`.
- **Teaching Point Coordinates**: Use `View > Update TP View`.
- **Developer Tools**: Access extra functions with `Ctrl + P`.

# TODO

- [ ] Implement a fallback prompt for unmatched names, asking for user input (`spec_id` or `spec_file_name`). 