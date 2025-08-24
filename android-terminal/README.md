Canvas Terminal Android

A native Android terminal app using Kotlin + Jetpack Compose + jackpal/androidterm PTY, styled with Material 3.

Prerequisites
- Android Studio Koala (or Flamingo+)
- JDK 17

Build & Run
1) Open the `android-terminal/` folder in Android Studio
2) Let Gradle sync; ensure JitPack is available
3) Run the app on a device/emulator (minSdk 26)

Notes
- Uses `ShellTermSession` from Android-Terminal-Emulator; default shell: `/system/bin/sh` or `$SHELL`.
- UI uses Material 3 dark scheme; easy to customize.
- Next: tabs/splits, settings, permissions for storage, keyboard IME tweaks.
