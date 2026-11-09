# igaging-caliper

NVDA add-on that speaks the measurements of the **iGaging Bluetooth caliper**
(tested with the 100-700-B06).

The caliper connects to Windows as a Bluetooth keyboard: when you press DATA,
it types F24, a space and the measurement. This add-on catches those keys
everywhere (even in browse mode), so nothing is typed into the active window,
and NVDA speaks the measurement instead, for example "21.99 millimeters".

- Measurements can be saved to a text file and copied to the clipboard.
- NVDA announces when the caliper connects and disconnects.
- A command (no default gesture) reports the caliper battery level.
- Languages: English, French, German, Spanish.

Settings: NVDA menu, Preferences, Settings, "Caliper" category.
Full help: `piedCoulisse/doc/en/readme.html` (also in French, German, Spanish).

## Requirements

- NVDA 2023.1 or later (tested with NVDA 2026.3 on Windows 11).
- An iGaging Bluetooth caliper paired with Windows (it appears as
  "Bluetooth Keyboard").

## Building

```
python construire.py
```

Builds `igaging-caliper.nvda-addon` in the parent folder (translations are
compiled from the `.po` files on the way; no other tool needed).

## Authors and license

seb-naudet and Claude Code (Anthropic).
Contact: binaural.bourbonnais@gmail.com

Released under the GNU General Public License, version 2 (see `LICENSE`).
