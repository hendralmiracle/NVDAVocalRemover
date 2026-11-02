# NVDAVocalRemover

AI-powered Vocal & Stem Separation Add-on for the NVDA Screen Reader on Windows.
Powered by state-of-the-art BS-Roformer and Mel-Band Roformer models via MVSEP cloud GPU backend.

## Features
- **100% Accessible UI:** Fully keyboard and screen reader accessible (NVDA).
- **Global Shortcut:**  to open the separation dialog.
- **5 Separation Categories & SOTA AI Models:**
  1. **Music and vocals:**
     - Mel-Roformer deux (becruily)
     - BS-Roformer HyperACE (unwa)
  2. **Keep backing vocals (Karaoke):**
     - BS-RoFormer Kar (anvuew)
     - BS-RoFormer Kar (frazer & becruily)
     - Mel-RoFormer Kar by becruily
  3. **Extract backing vocals:**
     - Mel-RoFormer Lead/Back (isolates Lead Vocals, Backing Vocals, and Instrumental)
  4. **Bass:**
     - BS-RoFormer (extracts Bass and Instrumental)
  5. **Drums:**
     - Mel-RoFormer (extracts Drums and Instrumental)
- **Output Formats:** WAV (Lossless 16-bit uncompressed) or MP3 (320 kbps).
- **Clean Stem Filenames:** Cleanly formatted  without random timestamps.
- **Bilingual Interface:** Real-time toggle between **Bahasa Indonesia** and **English**.
- **Auto-Queueing & Beep Monitor:** Displays queue status (e.g. ) with non-intrusive periodic audio beeps.
- **In-App Update Checker:** Check for updates directly from the dialog.

## Requirements
- NVDA 2021.1 or later on Windows.
- Free MVSEP API Token (obtainable from https://mvsep.com/user-api).

## Installation
Download the latest  from the [Releases](https://github.com/hendralmiracle/NVDAVocalRemover/releases) page and open it to install into NVDA.
