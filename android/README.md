# Nirikshak for Android

Tap **New package**, grant camera access, and show the front of the packet. Hold it in the guide until the app captures a photo. Follow its prompt to turn to the back. The third view is optional. The app sends the saved views, analyzes the printed declarations, and opens an inspection with the saved report. The flow needs no shutter tap, gallery upload, or package form.

Capture cues come from on-device checks for darkness, glare, framing, focus, motion, and resemblance to a panel already captured. Keep the packet centered against a plain background. The view labels follow the guided order. The camera estimates when a view is ready and relies on the operator to show the requested panel.

The app saves an unfinished scan on the phone. Use **Resume scan** after returning, or **Retry analysis** after a connection error. Successful submission deletes the phone's temporary photo copies. The backend still keeps the inspection and its evidence. If the server accepted a partial submission before you discarded a local scan, that inspection can appear in the web history.

## Run locally

1. Start the [FastAPI backend](../README.md#backend-setup) from this checkout. Install the backend's OCR dependencies and model for declaration extraction.
2. Install JDK 17 or 21, Android SDK Platform 36 and Android Build Tools 36.0.0. Set `ANDROID_HOME` or configure the SDK in Android Studio.
3. In this directory, run `./gradlew assembleDebug` or open it as a Gradle project in Android Studio. Use `gradlew.bat` on Windows.
4. Install `app/build/outputs/apk/debug/app-debug.apk`. The default debug API URL is `http://10.0.2.2:8000` for the standard Android emulator.

On a physical phone, build with `-PnirikshakApiBase=http://<computer-lan-ip>:8000`, start the development backend listening on the LAN, and connect both devices to the same network. Release builds require an HTTPS API URL supplied with the same Gradle property. The app builds as a separate client for the existing FastAPI server. Analysis can take several minutes on a CPU. This client sends `use_jev: false`.

## Verification

Run `./gradlew testDebugUnitTest lintDebug` for the capture gating tests and Android lint, and the normal backend test suite for inspection creation and export. The [Week 12 protocol](../docs/week-12.md#physical-capture-acceptance) covers the remaining phone and package acceptance checks.
