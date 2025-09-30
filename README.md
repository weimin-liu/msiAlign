[![DOI](https://zenodo.org/badge/764066001.svg)](https://doi.org/10.5281/zenodo.15039621)

# Installation

- The main branch always has the latest version. Download, install dependencies, and run `msiAlign/__main__.py`.
- install from pypi and run `msialign` in the terminal:
```bash
pip install msialign
msiAlign
```
- The latest executable is available [here](https://github.com/weimin-liu/msiAlign/releases/latest) (won't be regularly updated as it's hard to debug).
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
- **XRF Analysis**: Select `Calc > Prep XRF`. Pair teaching points and submit to calculate transformations. Specify XRF data path when asked to generate depth and mask data, which is saved in the same directory as the XRF data.
- Note the format of Teaching Points pairs: ![TP Pair Format](./imgs/Screenshot%202024-03-14%20at%2014.21.28.png)

### Depth Profile
- Go to `Calc > Downcore Profile` to generate depth profiles. Ensure MSI exports are named exactly after spectrum data (e.g., `xxxx.d` has `xxxx.d.txt`).
  - Spot method: three methods are available when averaging 2D data into 1D profiles.
    - all: all compounds listed in "Target cmpds" must be present in the spectrum, or the spectrum is ignored.
    - any: at least one compound listed in "Target cmpds" must be present in the spectrum, or the spectrum is ignored.
    - user input: based on the compound list (separated by ;) provided by the user, the spectrum is ignored if **any** of the listed compounds are not present.
  - Dynamic spot averaging: dynamically adjusting the spot size to ensure a minimum number of spectra are averaged instead of dropping them.
    - MSI res (um): the resolution of the MSI data in microns
    - Max extra rows: the maximum number of rows to add to the spot size to ensure the minimum number of spectra are averaged. If the number of spectra is still below the minimum after adding the maximum number of rows, all spectra within the horizon are ignored.

## Useful Functions
- **Save/Load Canvas**: Save workspace via `File > Save Workspace` (JSON file), reload with `File > Load Workspace`.
- **Teaching Point Coordinates**: Use `View > Update TP View`.
- **Developer Tools**: Access extra functions with `Ctrl + P`.

# TODO

- [ ] Implement a fallback prompt for unmatched names, asking for user input (`spec_id` or `spec_file_name`). 
