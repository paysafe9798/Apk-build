# Prime Shani — Sensitivity Generator

Android app that auto-reads your device's real specs (RAM, screen
resolution/DPI, refresh rate, battery, chipset hints) and generates
tuned in-game sensitivity values, fully on-device — no manual input
required.

This is a rebuild of the original sensitivity-generation logic as a
native Android app: the same calculation engine (device scoring →
in-process micro-benchmark → tiered sensitivity curve) now runs
inside the app via [Chaquopy](https://chaquo.com/chaquopy/) instead
of as a desktop Python script.

## How the build works

- `app/src/main/assets/engine.py` — the calculation engine (device
  scoring, benchmark, sensitivity generation, formatting).
- `app/src/main/java/.../DeviceCollector.java` — uses Android's own
  APIs (`Build`, `ActivityManager`, `WindowManager`, `BatteryManager`)
  to automatically read the real device's specs. No root, no shell
  commands, no manual entry.
- `app/src/main/java/.../MainActivity.java` — wires the UI button to
  the engine and displays the formatted result.
- Chaquopy packages a real Python 3 interpreter inside the APK so
  `engine.py` runs unchanged on-device.

## Building the APK via GitHub Actions

1. Push this repository to GitHub (or fork it).
2. Go to the **Actions** tab → select **Build Prime Shani APK** →
   **Run workflow** (or just push to `main`, it triggers automatically).
3. Once the run finishes, open the run → download the
   **prime-shani-apk** artifact. Inside is `app-debug.apk`.
4. Transfer the APK to your Android device and install it (you'll
   need to allow "install from unknown sources" since it isn't signed
   with a Play Store key).

## Building locally instead

```bash
./gradlew assembleDebug
```

The output APK will be at:
`app/build/outputs/apk/debug/app-debug.apk`

## Notes

- Minimum Android version: 7.0 (API 24).
- The in-app micro-benchmark runs briefly (under ~2 seconds) each
  time you tap **Regenerate**, exactly mirroring the original
  CPU/RAM/GFX-ratio scoring approach, just scaled down so the UI
  doesn't lag.
- Chipset tier lookup (`d8f.json`) is bundled as an asset and used to
  cross-check the benchmark-derived tier against known chipset names.
