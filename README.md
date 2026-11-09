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

## Download and install

Download `igaging-caliper.nvda-addon` from the
[latest release](https://github.com/seb-naudet/igaging-caliper/releases/latest),
open it (press Enter on it in File Explorer), confirm, then restart NVDA.
Pair the caliper in Windows: Settings, Bluetooth & devices, Add device,
Bluetooth, choose "Bluetooth Keyboard".

## Going back to keyboard mode

Disable the add-on (NVDA menu, Tools, Add-on Store, Installed add-ons,
Disable, then restart NVDA): the caliper types the measurement into the
active field again. It types like an English (US) keyboard: with another
input language the measurement may come out wrong (with French AZERTY, the
digits become &, é, "…), so switch the input language to English
(Windows+Space on Windows), on the computer as on an iPhone.

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
