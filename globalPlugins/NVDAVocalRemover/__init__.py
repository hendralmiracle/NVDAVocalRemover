# NVDAVocalRemover - Global Plugin
# Shortcut: NVDA+Shift+X
# Engine: MVSEP Cloud API + High-accuracy BS-Roformer / Mel-Roformer Models

import os
import sys
import threading
import json
import urllib.request
import urllib.parse
import urllib.error
import mimetypes
import uuid
import winsound
import time
import webbrowser
import tempfile
import re
import wx

import globalPluginHandler
import ui
import api
import gui
from scriptHandler import script
import addonHandler

addonHandler.initTranslation()

CURRENT_VERSION = "1.4.0"
GITHUB_REPO = "hendralmiracle/NVDAVocalRemover"

CONFIG_DIR = os.path.join(os.environ.get('APPDATA', ''), 'NVDAVocalRemover')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
DEFAULT_OUT_DIR = os.path.join(os.path.expanduser("~"), "Music", "VocalRemover")

# Categories & Models (Comprehensive X-Minus Pro Vocal Remover set)
CATEGORIES = [
    "1: Music and vocals",
    "2: Keep backing vocals",
    "3: Extract backing vocals",
    "4: Bass",
    "5: Drums",
    "6: Guitar",
    "7: Saxophone",
    "8: Splitter (Multi-stem)",
    "9: De-echo / De-reverb",
    "10: De-crowd",
    "11: Restoration (Denoise & Enhance)",
    "12: Other (Male / Female Vocals)"
]

MODELS_PER_CAT = {
    "1: Music and vocals": [
        "Mel-Roformer deux (becruily)",
        "BS-Roformer HyperACE (unwa)",
        "MDX23C",
        "BS PolarFormer"
    ],
    "2: Keep backing vocals": [
        "BS-RoFormer Kar (anvuew)",
        "BS-RoFormer Kar (frazer & becruily)",
        "Mel-RoFormer Kar by becruily"
    ],
    "3: Extract backing vocals": [
        "Mel-RoFormer Lead/Back",
        "Phantom Center (BS-RoFormer)"
    ],
    "4: Bass": [
        "BS-RoFormer"
    ],
    "5: Drums": [
        "Mel-RoFormer"
    ],
    "6: Guitar": [
        "BS Roformer SW",
        "Mel-RoFormer (2024.06)",
        "Ensemble (BS + Mel Roformer)",
        "BS-Roformer (viperx)",
        "Mel-RoFormer (Acoustic) β",
        "Electric Guitar (Mel-Roformer)",
        "Lead & Rhythm Guitar (Two-stage)",
        "Pedal Steel Guitar"
    ],
    "7: Saxophone": [
        "BS-RoFormer",
        "MelBand Roformer"
    ],
    "8: Splitter (Multi-stem)": [
        "Demucs4 HT (4 stems)",
        "BS-Roformer SW (6 stems)",
        "DrumSep (6 stems)"
    ],
    "9: De-echo / De-reverb": [
        "DeReverb stereo (BS-Roformer)",
        "DeReverb room (BS-Roformer)",
        "Reverb removal (Mel-Roformer)"
    ],
    "10: De-crowd": [
        "BS-Roformer",
        "Mel-Roformer"
    ],
    "11: Restoration (Denoise & Enhance)": [
        "DeNoise (aufr33 & gabox)",
        "Apollo Audio Enhancer",
        "AudioSR (Super Resolution)"
    ],
    "12: Other (Male / Female Vocals)": [
        "Mel-RoFormer (2025.01) (Beta Version)",
        "Mel-RoFormer (2025.01) (Acapella only) (Beta Version)",
        "SCNet XL (Beta Version)",
        "BS-RoFormer by aufr33 (Beta Version)",
        "BS-RoFormer by Sucial (Beta Version)"
    ]
}

# Mapping to MVSEP API parameters: (sep_type, add_opt1, add_opt2)
MVSEP_CONFIG = {
    # 1: Music and vocals
    ("1: Music and vocals", "Mel-Roformer deux (becruily)"): (48, 11, 2),        # MelBand Roformer ID 48, opt 11 = becruily deux
    ("1: Music and vocals", "BS-Roformer HyperACE (unwa)"): (40, 142, 2),        # BS Roformer ID 40, opt 142 = HyperACE v2 instrum
    ("1: Music and vocals", "MDX23C"): (25, None, None),
    ("1: Music and vocals", "BS PolarFormer"): (123, None, None),

    # 2: Keep backing vocals
    ("2: Keep backing vocals", "BS-RoFormer Kar (anvuew)"): (49, 7, 0),             # MVSep Karaoke ID 49, opt 7 = BS Roformer anvuew
    ("2: Keep backing vocals", "BS-RoFormer Kar (frazer & becruily)"): (49, 5, 0),  # MVSep Karaoke ID 49, opt 5 = BS Roformer frazer & becruily
    ("2: Keep backing vocals", "Mel-RoFormer Kar by becruily"): (49, 1, 0),          # MVSep Karaoke ID 49, opt 1 = MelBand becruily

    # 3: Extract backing vocals
    ("3: Extract backing vocals", "Mel-RoFormer Lead/Back"): (49, 0, 1),               # MVSep Karaoke ID 49, opt 0 = Mel-Roformer, opt 2 = 1 (Extract vocals first)
    ("3: Extract backing vocals", "Phantom Center (BS-RoFormer)"): (55, 1, None),      # MVSep Phantom Centre ID 55, opt 1 = BS-Roformer by gilliaan

    # 4: Bass
    ("4: Bass", "BS-RoFormer"): (41, 0, 0),                          # MVSep Bass ID 41, opt 0 = BS Roformer, opt 2 = 0

    # 5: Drums
    ("5: Drums", "Mel-RoFormer"): (44, 1, 0),                         # MVSep Drums ID 44, opt 1 = MelBand Roformer, opt 2 = 0

    # 6: Guitar
    ("6: Guitar", "BS Roformer SW"): (31, 7, None),
    ("6: Guitar", "Mel-RoFormer (2024.06)"): (31, 3, None),
    ("6: Guitar", "Ensemble (BS + Mel Roformer)"): (31, 6, None),
    ("6: Guitar", "BS-Roformer (viperx)"): (31, 5, None),
    ("6: Guitar", "Mel-RoFormer (Acoustic) β"): (66, None, 0),
    ("6: Guitar", "Electric Guitar (Mel-Roformer)"): (81, None, 0),
    ("6: Guitar", "Lead & Rhythm Guitar (Two-stage)"): (101, 0, None),
    ("6: Guitar", "Pedal Steel Guitar"): (124, None, None),
    ("6: Guitar", "Mel-RoFormer"): (31, 3, None),
    ("6: Guitar", "BS-Roformer"): (31, 7, None),
    ("6: Guitar", "BS Roformer SW (SDR: 9.05)"): (31, 7, None),

    # 7: Saxophone
    ("7: Saxophone", "BS-RoFormer"): (61, 3, None),                   # MVSep Saxophone ID 61, opt 1 = 3 (BS Roformer)
    ("7: Saxophone", "MelBand Roformer"): (61, 1, None),              # MVSep Saxophone ID 61, opt 1 = 1 (MelBand Roformer)

    # 8: Splitter (Multi-stem)
    ("8: Splitter (Multi-stem)", "Demucs4 HT (4 stems)"): (20, 0, None),   # Demucs4 HT ID 20, opt 1 = 0 (htdemucs_ft)
    ("8: Splitter (Multi-stem)", "BS-Roformer SW (6 stems)"): (63, None, None), # BS Roformer SW ID 63 (6 stems)
    ("8: Splitter (Multi-stem)", "DrumSep (6 stems)"): (37, 7, 0),         # DrumSep ID 37, opt 1 = 7 (MelBand Roformer 6 stems)

    # 9: De-echo / De-reverb
    ("9: De-echo / De-reverb", "DeReverb stereo (BS-Roformer)"): (22, 7, 1), # Reverb Removal ID 22, opt 1 = 7, opt 2 = 1
    ("9: De-echo / De-reverb", "DeReverb room (BS-Roformer)"): (22, 6, 1),   # Reverb Removal ID 22, opt 1 = 6, opt 2 = 1
    ("9: De-echo / De-reverb", "Reverb removal (Mel-Roformer)"): (22, 5, 1), # Reverb Removal ID 22, opt 1 = 5, opt 2 = 1

    # 10: De-crowd
    ("10: De-crowd", "BS-Roformer"): (34, 2, None),                   # Crowd removal ID 34, opt 1 = 2 (BS Roformer)
    ("10: De-crowd", "Mel-Roformer"): (34, 0, None),                  # Crowd removal ID 34, opt 1 = 0 (Mel Roformer)

    # 11: Restoration (Denoise & Enhance)
    ("11: Restoration (Denoise & Enhance)", "DeNoise (aufr33 & gabox)"): (47, 0, None), # DeNoise ID 47, opt 1 = 0
    ("11: Restoration (Denoise & Enhance)", "Apollo Audio Enhancer"): (51, 3, 0),        # Apollo ID 51, opt 1 = 3, opt 2 = 0
    ("11: Restoration (Denoise & Enhance)", "AudioSR (Super Resolution)"): (59, 0, None),# AudioSR ID 59, opt 1 = 0

    # 12: Other (Male / Female Vocals)
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Beta Version)"): (57, 2, 1), # MVSep ID 57, opt 1 = 2 (MelRoformer 2025.01), opt 2 = 1 (Extract vocals first with BS Roformer)
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Acapella only) (Beta Version)"): (57, 2, 0), # MVSep ID 57, opt 1 = 2, opt 2 = 0 (Direct from mixture)
    ("12: Other (Male / Female Vocals)", "SCNet XL (Beta Version)"): (57, 1, 1), # MVSep ID 57, opt 1 = 1 (SCNet XL), opt 2 = 1
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by aufr33 (Beta Version)"): (57, 3, 1), # MVSep ID 57, opt 1 = 3 (BSRoformer by aufr33), opt 2 = 1
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by Sucial (Beta Version)"): (57, 0, 1), # MVSep ID 57, opt 1 = 0 (BSRoformer by Sucial), opt 2 = 1

    # Fallbacks for legacy/alternative names
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01)"): (57, 2, 1),
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Acapella only)"): (57, 2, 0),
    ("12: Other (Male / Female Vocals)", "SCNet XL"): (57, 1, 1),
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by aufr33"): (57, 3, 1),
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by Sucial"): (57, 0, 1),
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (SDR: 13.03)"): (57, 2, 1),
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Acapella / Vocal only)"): (57, 2, 0),
    ("12: Other (Male / Female Vocals)", "SCNet XL (SDR: 11.83)"): (57, 1, 1),
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by aufr33 (SDR: 8.18)"): (57, 3, 1),
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by Sucial (SDR: 6.52)"): (57, 0, 1),
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (Male / Female)"): (57, 2, 1),
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (Vocal only)"): (57, 2, 0),

    # Fallbacks for string-only lookup
    "Mel-Roformer deux (becruily)": (48, 11, 2),
    "BS-Roformer HyperACE (unwa)": (40, 142, 2),
    "BS-RoFormer Kar (anvuew)": (49, 7, 0),
    "BS-RoFormer Kar (frazer & becruily)": (49, 5, 0),
    "Mel-RoFormer Kar by becruily": (49, 1, 0),
    "Mel-RoFormer Lead/Back": (49, 0, 1),
    "BS-RoFormer": (41, 0, 0),
    "Mel-RoFormer (Acoustic) β": (66, None, 0)
}


# Descriptions for all AI models (X-Minus Pro style, Bilingual: id / en)
MODEL_DESCRIPTIONS = {
    # 1: Music and vocals
    ("1: Music and vocals", "Mel-Roformer deux (becruily)"): {
        "en": "The best model for isolating both vocals and music",
        "id": "Model terbaik untuk memisahkan vokal dan musik"
    },
    ("1: Music and vocals", "BS-Roformer HyperACE (unwa)"): {
        "en": "Less muddy",
        "id": "Lebih jernih dan minim keruh (Less muddy)"
    },
    ("1: Music and vocals", "MDX23C"): {
        "en": "Fast and balanced separation",
        "id": "Pemisahan cepat dan seimbang"
    },
    ("1: Music and vocals", "BS PolarFormer"): {
        "en": "New architecture for long audio",
        "id": "Arsitektur baru untuk audio panjang"
    },

    # 2: Keep backing vocals
    ("2: Keep backing vocals", "BS-RoFormer Kar (anvuew)"): {
        "en": "Preserves backing vocals cleanly",
        "id": "Mempertahankan vokal latar dengan bersih"
    },
    ("2: Keep backing vocals", "BS-RoFormer Kar (frazer & becruily)"): {
        "en": "Professional karaoke separation",
        "id": "Pemisahan vokal karaoke profesional"
    },
    ("2: Keep backing vocals", "Mel-RoFormer Kar by becruily"): {
        "en": "Warm harmony and backing vocals",
        "id": "Menjaga harmoni dan vokal latar"
    },

    # 3: Extract backing vocals
    ("3: Extract backing vocals", "Mel-RoFormer Lead/Back"): {
        "en": "Extracts lead, backing vocals and music",
        "id": "Memisahkan vokal utama, vokal latar, dan musik"
    },
    ("3: Extract backing vocals", "Phantom Center (BS-RoFormer)"): {
        "en": "Center channel & wide stereo sides",
        "id": "Pemisahan vokal tengah dan stereo samping"
    },

    # 4: Bass
    ("4: Bass", "BS-RoFormer"): {
        "en": "Dedicated bass isolation",
        "id": "Isolasi nada bass instrumen"
    },

    # 5: Drums
    ("5: Drums", "Mel-RoFormer"): {
        "en": "Full drum kit and percussion isolation",
        "id": "Isolasi seluruh perangkat drum dan perkusi"
    },

    # 6: Guitar
    ("6: Guitar", "BS Roformer SW"): {
        "en": "Highest quality guitar separation",
        "id": "Kualitas separasi gitar terbaik"
    },
    ("6: Guitar", "BS Roformer SW (SDR: 9.05)"): {
        "en": "Highest quality guitar separation",
        "id": "Kualitas separasi gitar terbaik"
    },
    ("6: Guitar", "Mel-RoFormer (2024.06)"): {
        "en": "Acoustic and electric guitar model",
        "id": "Model gitar akustik dan elektrik"
    },
    ("6: Guitar", "Ensemble (BS + Mel Roformer)"): {
        "en": "Balanced ensemble for all genres",
        "id": "Kombinasi seimbang untuk semua genre"
    },
    ("6: Guitar", "BS-Roformer (viperx)"): {
        "en": "Guitar isolation (viperx edition)",
        "id": "Isolasi gitar (edisi viperx)"
    },
    ("6: Guitar", "Mel-RoFormer (Acoustic) β"): {
        "en": "Acoustic guitar from mixture",
        "id": "Gitar akustik langsung dari musik"
    },
    ("6: Guitar", "Electric Guitar (Mel-Roformer)"): {
        "en": "Electric guitar isolation",
        "id": "Isolasi gitar elektrik"
    },
    ("6: Guitar", "Lead & Rhythm Guitar (Two-stage)"): {
        "en": "Splits lead and rhythm guitars",
        "id": "Memecah lead dan rhythm gitar"
    },
    ("6: Guitar", "Pedal Steel Guitar"): {
        "en": "Pedal steel and slide guitar",
        "id": "Isolasi pedal steel dan slide gitar"
    },

    # 7: Saxophone
    ("7: Saxophone", "BS-RoFormer"): {
        "en": "High accuracy saxophone isolation",
        "id": "Isolasi saksofon akurasi tinggi"
    },
    ("7: Saxophone", "MelBand Roformer"): {
        "en": "Alternative saxophone model",
        "id": "Model saksofon alternatif"
    },

    # 8: Splitter (Multi-stem)
    ("8: Splitter (Multi-stem)", "Demucs4 HT (4 stems)"): {
        "en": "4 stems: vocals, drums, bass, other",
        "id": "4 trek: vokal, drum, bass, lainnya"
    },
    ("8: Splitter (Multi-stem)", "BS-Roformer SW (6 stems)"): {
        "en": "6 stems: vocals, bass, drums, guitar, piano, other",
        "id": "6 trek: vokal, bass, drum, gitar, piano, lainnya"
    },
    ("8: Splitter (Multi-stem)", "DrumSep (6 stems)"): {
        "en": "6 drum parts: kick, snare, cymbals, toms, hh, crash",
        "id": "6 bagian drum: kick, snare, cymbal, tom, hihat, crash"
    },

    # 9: De-echo / De-reverb
    ("9: De-echo / De-reverb", "DeReverb stereo (BS-Roformer)"): {
        "en": "Removes stereo reverb and echo",
        "id": "Menghilangkan reverb dan gema stereo"
    },
    ("9: De-echo / De-reverb", "DeReverb room (BS-Roformer)"): {
        "en": "Removes room reflections (dry vocal)",
        "id": "Menghilangkan pantulan ruangan (dry vocal)"
    },
    ("9: De-echo / De-reverb", "Reverb removal (Mel-Roformer)"): {
        "en": "Smooth vocal dereverberation",
        "id": "Pembersih reverb vokal halus"
    },

    # 10: De-crowd
    ("10: De-crowd", "BS-Roformer"): {
        "en": "Removes audience and crowd noise",
        "id": "Menghilangkan suara penonton dan kerumunan"
    },
    ("10: De-crowd", "Mel-Roformer"): {
        "en": "Alternative live crowd removal",
        "id": "Pembersih suara penonton live alternatif"
    },

    # 11: Restoration (Denoise & Enhance)
    ("11: Restoration (Denoise & Enhance)", "DeNoise (aufr33 & gabox)"): {
        "en": "Cleans tape hiss and background noise",
        "id": "Membersihkan desis kaset dan derau latar"
    },
    ("11: Restoration (Denoise & Enhance)", "Apollo Audio Enhancer"): {
        "en": "Enhances low bitrate and MP3 audio",
        "id": "Penjernih frekuensi MP3 dan bitrate rendah"
    },
    ("11: Restoration (Denoise & Enhance)", "AudioSR (Super Resolution)"): {
        "en": "Upscales audio to high resolution (48 kHz)",
        "id": "Meningkatkan resolusi audio ke 48 kHz"
    },

    # 12: Other (Male / Female Vocals)
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Beta Version)"): {
        "en": "The best model for separating male and female voices (Beta)",
        "id": "Model terbaik pemisah vokal pria dan wanita (Beta)"
    },
    ("12: Other (Male / Female Vocals)", "Mel-RoFormer (2025.01) (Acapella only) (Beta Version)"): {
        "en": "Direct separation for tracks that contain only voices (Beta)",
        "id": "Pemisahan langsung untuk trek yang hanya berisi vokal (tanpa musik) (Beta)"
    },
    ("12: Other (Male / Female Vocals)", "SCNet XL (Beta Version)"): {
        "en": "SCNet XL model for male and female separation (Beta)",
        "id": "Model SCNet XL untuk pemisahan vokal pria dan wanita (Beta)"
    },
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by aufr33 (Beta Version)"): {
        "en": "BS-Roformer model by aufr33 (Beta)",
        "id": "Model BS-Roformer racikan aufr33 (Beta)"
    },
    ("12: Other (Male / Female Vocals)", "BS-RoFormer by Sucial (Beta Version)"): {
        "en": "BS-Roformer model by Sucial (Beta)",
        "id": "Model BS-Roformer racikan Sucial (Beta)"
    }
}

# Formats: 0 = MP3 (320kbps), 1 = WAV (16-bit uncompressed)
FORMATS = [
    "WAV (Lossless)",
    "MP3 (320 kbps)"
]
FORMAT_MAP = {
    "WAV (Lossless)": "1",
    "MP3 (320 kbps)": "0"
}

LANGUAGES = ["Bahasa Indonesia", "English"]
LANG_MAP = {"Bahasa Indonesia": "id", "English": "en"}
REV_LANG_MAP = {"id": "Bahasa Indonesia", "en": "English"}

TEXTS = {
    "id": {
        "dialog_title": "NVDA Vocal Remover (BS-Roformer / Mel-Roformer)",
        "browse": "&Browse (Pilih Lagu)...",
        "cat_label": "&Kategori Pemisahan:",
        "model_label": "&Pilihan Model AI:",
        "token_label": "MVSEP &API Token:",
        "get_token": "&Dapatkan API Key...",
        "clear_queue": "&Bersihkan Antrean",
        "format_label": "&Format Output Hasil:",
        "lang_label": "&Bahasa / Language:",
        "output_label": "&Folder Penyimpanan Hasil:",
        "browse_out": "Pilih &Folder...",
        "check_update": "&Cek Pembaruan...",
        "start_btn": "&Pisahkan Vokal (Mulai)",
        "cancel_btn": "&Batal",
        "select_file_dlg": "Pilih File Audio (MP3, WAV, FLAC, M4A, OGG)",
        "select_folder_dlg": "Pilih Folder Hasil",
        "err_no_file": "Error: File audio belum dipilih. Silakan tekan tombol Browse.",
        "err_empty_file": "Error: File audio kosong (0 bytes) atau rusak.",
        "err_no_token": "Perhatian: Masukkan API Token MVSEP gratis Anda agar pemrosesan model SOTA berjalan.",
        "uploading": "Mengunggah {filename} menggunakan model {model_name} (Format: {out_format}). Mohon tunggu...",
        "upload_done": "Audio berhasil diunggah. Menunggu respons antrean server...",
        "turn_arrived": "Giliran tiba! Lagu Anda berhasil masuk ke antrean server.",
        "waiting_turn": "Menunggu giliran otomatis...",
        "server_processing": "AI sedang memproses pemisahan audio di GPU...",
        "stage_merging": "Tahap {status}: menyatukan hasil audio...",
        "sep_failed": "Pemisahan gagal: {reason}",
        "sep_done": "Pemisahan selesai! Memulai proses unduhan hasil...",
        "timeout": "Waktu pemrosesan melebihi batas atau server tidak merespons.",
        "downloading_stem": "Mengunduh stem {idx} dari {total}: {stem}...",
        "all_saved": "Berhasil! Semua stem tersimpan di folder: {out_dir}",
        "checking_queue": "Memeriksa dan membersihkan antrean di server...",
        "queue_cleared": "Berhasil membatalkan {count} file dari antrean server.",
        "queue_empty": "Antrean server sudah kosong dan bersih.",
        "checking_update": "Memeriksa pembaruan...",
        "update_available": "Versi baru {version} tersedia!\n\nCatatan rilis:\n{body}\n\nApakah Anda ingin mengunduh dan memperbarui sekarang?",
        "update_title": "Pembaruan Add-on Tersedia",
        "update_latest": "NVDAVocalRemover sudah menggunakan versi terbaru (v{version}).",
        "update_downloading": "Sedang mengunduh pembaruan versi {version}...",
        "update_err": "Gagal memeriksa pembaruan: {error}",
        "update_no_repo": "Belum ada rilis pembaruan baru.",
        "open_token_page": "Membuka halaman API Token MVSEP di browser...",
        "file_selected": "Dipilih: {filename}"
    },
    "en": {
        "dialog_title": "NVDA Vocal Remover (BS-Roformer / Mel-Roformer)",
        "browse": "&Browse...",
        "cat_label": "&Separation Category:",
        "model_label": "&AI Model Selection:",
        "token_label": "MVSEP &API Token:",
        "get_token": "&Get API Key...",
        "clear_queue": "&Clear Queue",
        "format_label": "&Output Format:",
        "lang_label": "&Bahasa / Language:",
        "output_label": "&Output Folder:",
        "browse_out": "Select &Folder...",
        "check_update": "&Check for Updates...",
        "start_btn": "&Separate Vocals (Start)",
        "cancel_btn": "&Cancel",
        "select_file_dlg": "Select Audio File (MP3, WAV, FLAC, M4A, OGG)",
        "select_folder_dlg": "Select Output Folder",
        "err_no_file": "Error: No audio file selected. Please use the Browse button.",
        "err_empty_file": "Error: Audio file is empty (0 bytes) or corrupted.",
        "err_no_token": "Warning: Please enter your free MVSEP API Token to process SOTA models.",
        "uploading": "Uploading {filename} using model {model_name} (Format: {out_format}). Please wait...",
        "upload_done": "Audio uploaded successfully. Awaiting server queue response...",
        "turn_arrived": "Your turn has arrived! Your audio has entered the server queue.",
        "waiting_turn": "Waiting for turn automatically...",
        "server_processing": "AI is processing audio separation on GPU...",
        "stage_merging": "Stage {status}: merging audio stems...",
        "sep_failed": "Separation failed: {reason}",
        "sep_done": "Separation complete! Starting stem downloads...",
        "timeout": "Processing timed out or server did not respond.",
        "downloading_stem": "Downloading stem {idx} of {total}: {stem}...",
        "all_saved": "Success! All stems saved in folder: {out_dir}",
        "checking_queue": "Checking and clearing queue on server...",
        "queue_cleared": "Successfully cancelled {count} file(s) from server queue.",
        "queue_empty": "Server queue is already empty.",
        "checking_update": "Checking for updates...",
        "update_available": "A new version {version} is available!\n\nRelease notes:\n{body}\n\nWould you like to download and install it now?",
        "update_title": "Add-on Update Available",
        "update_latest": "NVDAVocalRemover is up to date (v{version}).",
        "update_downloading": "Downloading update version {version}...",
        "update_err": "Failed to check for updates: {error}",
        "update_no_repo": "No new releases found.",
        "open_token_page": "Opening MVSEP API Token page in browser...",
        "file_selected": "Selected: {filename}"
    }
}

def load_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "api_token": "",
        "category": "1: Music and vocals",
        "model": "Mel-Roformer deux (becruily)",
        "format": "WAV (Lossless)",
        "language": "id",
        "output_dir": DEFAULT_OUT_DIR
    }

def save_config(cfg):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)

def encode_multipart(fields, files):
    boundary = uuid.uuid4().hex
    crlf = b"\r\n"
    lines = []
    for (k, v) in fields.items():
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{k}"'.encode())
        lines.append(b"")
        lines.append(str(v).encode('utf-8'))
    for (k, filepath) in files.items():
        filename = os.path.basename(filepath).replace('"', '_')
        mime = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
        lines.append(f"--{boundary}".encode())
        lines.append(f'Content-Disposition: form-data; name="{k}"; filename="{filename}"'.encode('utf-8'))
        lines.append(f'Content-Type: {mime}'.encode())
        lines.append(b"")
        with open(filepath, 'rb') as f:
            lines.append(f.read())
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    body = crlf.join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return content_type, body

def clean_filename_part(text):
    text = str(text or "")
    text = text.replace("Piano: ", "Piano - ").replace("Strings: ", "Strings - ")
    text = text.replace(": ", " ").replace(":", " ")
    text = text.replace("/", "-").replace("\\", "-")
    for ch in '*?"<>|':
        text = text.replace(ch, "")
    text = re.sub(r'\s+', ' ', text)
    return text.strip(" .")

def get_clean_stem_name(stem_type, category, model_name=""):
    s = str(stem_type or "").lower().strip()
    cat = category.lower()
    m = model_name.lower()

    # Restoration / Noise / Reverb / Crowd
    if "noreverb" in s or "no-reverb" in s:
        return "De-reverbed (Dry)"
    elif "reverb" in s and "no" not in s:
        return "Reverb only"
    elif "crowd" in s:
        return "Crowd Noise"
    elif "dry" in s or "restored" in s or "clean" in s:
        return "Restored"
    elif "noise" in s:
        return "Noise removed"

    # Phantom center
    elif "center" in s:
        return "Center (Phantom)"
    elif "wide" in s or "sides" in s:
        return "Sides (Stereo)"

    # Drum components (DrumSep)
    elif "kick" in s:
        return "Kick"
    elif "snare" in s:
        return "Snare"
    elif "cymbal" in s:
        return "Cymbals"
    elif "tom" in s:
        return "Toms"
    elif "hi-hat" in s or "hh" in s:
        return "Hi-Hat"
    elif "ride" in s:
        return "Ride"
    elif "crash" in s:
        return "Crash"

    # Instruments & Guitar variants
    elif "acoustic" in s and "guitar" in s:
        return "Acoustic Guitar"
    elif "electric" in s and "guitar" in s:
        return "Electric Guitar"
    elif "pedal" in s or "steel" in s:
        return "Pedal Steel Guitar"
    elif "lead" in s and "guitar" in s:
        return "Lead Guitar"
    elif "rhythm" in s and "guitar" in s:
        return "Rhythm Guitar"
    elif "all" in s and "guitar" in s:
        return "All Guitar"
    elif "no" in s and "guitar" in s:
        return "Instrumental (no Guitar)"
    elif "guitar" in s:
        return "Guitar"
    elif "piano" in s:
        return "Piano"
    elif "string" in s:
        return "Strings"
    elif "sax" in s:
        return "Saxophone"
    elif "bass" in s:
        return "Bass"
    elif "drum" in s:
        return "Drums"

    # Vocals & Backing vocals & Male / Female
    elif "female" in s:
        return "Female Vocals"
    elif "male" in s:
        return "Male Vocals"
    elif "back" in s and ("instrum" in s or "music" in s or "+" in s or "track" in s):
        return "Backing Track with BV"
    elif "lead" in s:
        return "Lead Vocals"
    elif "back" in s:
        return "Backing Vocals"
    elif "only" in s and "instrum" in s:
        return "Instrumental only"
    elif "vocal" in s:
        return "Vocals"

    # Other / Inverted stems based on category
    elif "other" in s or "instrum" in s or "music" in s:
        if "keep backing" in cat:
            return "Backing Track with BV"
        elif "extract backing" in cat:
            return "Instrumental only"
        elif "bass" in cat:
            return "Instrumental (no Bass)"
        elif "drum" in cat:
            return "Instrumental (no Drums)"
        elif "guitar" in cat:
            return "Instrumental (no Guitar)"
        elif "sax" in cat:
            return "Instrumental (no Saxophone)"
        elif "de-crowd" in cat:
            return "Clean (no Crowd)"
        elif "other" in cat:
            if "male" in cat or "female" in cat:
                return "Instrumental"
            elif "piano" in m:
                return "Instrumental (no Piano)"
            elif "string" in m:
                return "Instrumental (no Strings)"
        elif "piano" in cat or "string" in cat:
            if "piano" in m:
                return "Instrumental (no Piano)"
            elif "string" in m:
                return "Instrumental (no Strings)"
        return "Instrumental"

    return stem_type if stem_type else "Audio"

def cancel_active_queue(api_token):
    if not api_token:
        return 0
    user_url = f"https://mvsep.com/api/app/user?api_token={api_token}"
    req = urllib.request.Request(user_url, headers={"User-Agent": "Mozilla/5.0"})
    cancelled = 0
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            queue = data.get("data", {}).get("current_queue", [])
            for h in queue:
                post_data = urllib.parse.urlencode({"api_token": api_token, "hash": h}).encode()
                req_cancel = urllib.request.Request("https://mvsep.com/api/separation/cancel", data=post_data, headers={"User-Agent": "Mozilla/5.0"}, method="POST")
                try:
                    with urllib.request.urlopen(req_cancel, timeout=15) as c_resp:
                        cancelled += 1
                except Exception:
                    pass
    except Exception:
        pass
    return cancelled

def check_for_updates(current_version, lang="id"):
    txt = TEXTS.get(lang, TEXTS["id"])
    ui.message(txt["checking_update"])
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            rel = json.loads(resp.read().decode('utf-8'))

        tag = rel.get("tag_name", "").lstrip("v").strip()
        body = rel.get("body", "").strip() or "Pembaruan performa dan perbaikan bug."
        
        def parse_v(v_str):
            nums = [int(x) for x in re.findall(r'\d+', str(v_str))]
            return nums or [0]

        if parse_v(tag) > parse_v(current_version):
            addon_url = None
            for asset in rel.get("assets", []):
                if asset.get("name", "").endswith(".nvda-addon"):
                    addon_url = asset.get("browser_download_url")
                    break
            if not addon_url:
                addon_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{tag}/NVDAVocalRemover.nvda-addon"

            def prompt_and_install():
                msg = txt["update_available"].format(version=tag, body=body)
                title = txt["update_title"]
                dlg = wx.MessageDialog(gui.mainFrame, msg, title, wx.YES_NO | wx.ICON_QUESTION)
                if dlg.ShowModal() == wx.ID_YES:
                    ui.message(txt["update_downloading"].format(version=tag))
                    temp_dir = tempfile.gettempdir()
                    target_file = os.path.join(temp_dir, f"NVDAVocalRemover_{tag}.nvda-addon")
                    urllib.request.urlretrieve(addon_url, target_file)
                    os.startfile(target_file)
                dlg.Destroy()
            wx.CallAfter(prompt_and_install)
        else:
            ui.message(txt["update_latest"].format(version=current_version))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            ui.message(txt["update_no_repo"])
        else:
            ui.message(txt["update_err"].format(error=f"HTTP {e.code}"))
    except Exception as e:
        ui.message(txt["update_err"].format(error=str(e)))


class VocalRemoverDialog(wx.Dialog):
    def __init__(self, parent):
        self.config = load_config()
        self.lang = self.config.get("language", "id")
        if self.lang not in TEXTS:
            self.lang = "id"
        txt = TEXTS[self.lang]

        super(VocalRemoverDialog, self).__init__(parent, title=txt["dialog_title"])
        self.selected_file = ""

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        # 1. Language choice (At the very beginning of the tab order)
        self.lbl_lang = wx.StaticText(self, label=txt["lang_label"])
        mainSizer.Add(self.lbl_lang, 0, wx.ALL, 8)
        self.langCombo = wx.ComboBox(self, choices=LANGUAGES, style=wx.CB_READONLY)
        cur_lang_str = REV_LANG_MAP.get(self.lang, LANGUAGES[0])
        self.langCombo.SetSelection(LANGUAGES.index(cur_lang_str))
        self.langCombo.Bind(wx.EVT_COMBOBOX, self.onLanguageChange)
        mainSizer.Add(self.langCombo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 2. File selection (Browse button only, edit box removed)
        self.browseBtn = wx.Button(self, label=txt["browse"])
        self.browseBtn.Bind(wx.EVT_BUTTON, self.onBrowse)
        mainSizer.Add(self.browseBtn, 0, wx.EXPAND | wx.ALL, 8)

        # 3. Category choice
        self.lbl_cat = wx.StaticText(self, label=txt["cat_label"])
        self.catCombo = wx.ComboBox(self, choices=CATEGORIES, style=wx.CB_READONLY)
        cur_cat = self.config.get("category", CATEGORIES[0])
        if cur_cat not in CATEGORIES:
            cur_cat = CATEGORIES[0]
        self.catCombo.SetSelection(CATEGORIES.index(cur_cat))
        self.catCombo.Bind(wx.EVT_COMBOBOX, self.onCategoryChange)
        mainSizer.Add(self.lbl_cat, 0, wx.ALL, 8)
        mainSizer.Add(self.catCombo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 4. Model choice
        self.lbl_model = wx.StaticText(self, label=txt["model_label"])
        self.modelCombo = wx.ComboBox(self, choices=[], style=wx.CB_READONLY)
        mainSizer.Add(self.lbl_model, 0, wx.ALL, 8)
        mainSizer.Add(self.modelCombo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)
        self.updateModelList(cur_cat, self.config.get("model", ""))

        # 5. MVSEP API Token (Password masked & Get Token / Clear Queue buttons)
        self.lbl_token = wx.StaticText(self, label=txt["token_label"])
        mainSizer.Add(self.lbl_token, 0, wx.ALL, 8)

        tokenSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.tokenInput = wx.TextCtrl(self, value=self.config.get("api_token", ""), style=wx.TE_PASSWORD)
        tokenSizer.Add(self.tokenInput, 1, wx.EXPAND | wx.RIGHT, 5)

        self.getTokenBtn = wx.Button(self, label=txt["get_token"])
        self.getTokenBtn.Bind(wx.EVT_BUTTON, self.onGetToken)
        tokenSizer.Add(self.getTokenBtn, 0, wx.RIGHT, 5)

        self.clearQueueBtn = wx.Button(self, label=txt["clear_queue"])
        self.clearQueueBtn.Bind(wx.EVT_BUTTON, self.onClearQueue)
        tokenSizer.Add(self.clearQueueBtn, 0)
        mainSizer.Add(tokenSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 6. Output Format choice (WAV vs MP3)
        self.lbl_fmt = wx.StaticText(self, label=txt["format_label"])
        self.formatCombo = wx.ComboBox(self, choices=FORMATS, style=wx.CB_READONLY)
        cur_fmt = self.config.get("format", FORMATS[0])
        if cur_fmt not in FORMATS:
            cur_fmt = FORMATS[0]
        self.formatCombo.SetSelection(FORMATS.index(cur_fmt))
        mainSizer.Add(self.lbl_fmt, 0, wx.ALL, 8)
        mainSizer.Add(self.formatCombo, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 7. Output Folder
        self.lbl_out = wx.StaticText(self, label=txt["output_label"])
        mainSizer.Add(self.lbl_out, 0, wx.ALL, 8)
        outSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.outDirInput = wx.TextCtrl(self, value=self.config.get("output_dir", DEFAULT_OUT_DIR))
        outSizer.Add(self.outDirInput, 1, wx.EXPAND | wx.RIGHT, 5)
        self.browseOutBtn = wx.Button(self, label=txt["browse_out"])
        self.browseOutBtn.Bind(wx.EVT_BUTTON, self.onBrowseOut)
        outSizer.Add(self.browseOutBtn, 0)
        mainSizer.Add(outSizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # 8. Action Buttons (Start, Cancel, and Check Update at the VERY END)
        btnSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.processBtn = wx.Button(self, label=txt["start_btn"])
        self.processBtn.Bind(wx.EVT_BUTTON, self.onProcess)
        self.processBtn.SetDefault()
        btnSizer.Add(self.processBtn, 0, wx.RIGHT, 10)

        self.cancelBtn = wx.Button(self, wx.ID_CANCEL, label=txt["cancel_btn"])
        btnSizer.Add(self.cancelBtn, 0, wx.RIGHT, 15)

        self.checkUpdateBtn = wx.Button(self, label=txt["check_update"])
        self.checkUpdateBtn.Bind(wx.EVT_BUTTON, self.onCheckUpdate)
        btnSizer.Add(self.checkUpdateBtn, 0)

        mainSizer.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 12)

        self.SetSizer(mainSizer)
        mainSizer.Fit(self)
        self.CenterOnScreen()

    def apply_language(self, lang):
        t = TEXTS.get(lang, TEXTS["id"])
        self.SetTitle(t["dialog_title"])
        self.browseBtn.SetLabel(t["browse"])
        self.lbl_cat.SetLabel(t["cat_label"])
        self.lbl_model.SetLabel(t["model_label"])
        self.lbl_token.SetLabel(t["token_label"])
        self.getTokenBtn.SetLabel(t["get_token"])
        self.clearQueueBtn.SetLabel(t["clear_queue"])
        self.lbl_fmt.SetLabel(t["format_label"])
        self.lbl_lang.SetLabel(t["lang_label"])
        self.lbl_out.SetLabel(t["output_label"])
        self.browseOutBtn.SetLabel(t["browse_out"])
        self.processBtn.SetLabel(t["start_btn"])
        self.cancelBtn.SetLabel(t["cancel_btn"])
        self.checkUpdateBtn.SetLabel(t["check_update"])
        self.Layout()

    def onLanguageChange(self, evt):
        sel = self.langCombo.GetStringSelection()
        self.lang = LANG_MAP.get(sel, "id")
        self.config["language"] = self.lang
        save_config(self.config)
        self.apply_language(self.lang)
        cur_cat = self.catCombo.GetStringSelection()
        cur_model = self.modelCombo.GetStringSelection()
        self.updateModelList(cur_cat, cur_model)
        ui.message("Bahasa diubah ke Bahasa Indonesia" if self.lang == "id" else "Language changed to English")

    def onCheckUpdate(self, evt):
        threading.Thread(target=check_for_updates, args=(CURRENT_VERSION, self.lang), daemon=True).start()

    def updateModelList(self, category, preferred_model=""):
        models = MODELS_PER_CAT.get(category, [])
        self.modelCombo.Clear()
        pref_idx = 0
        clean_pref = preferred_model.split("\n")[0].strip() if preferred_model else ""
        for idx, m in enumerate(models):
            desc_obj = MODEL_DESCRIPTIONS.get((category, m)) or MODEL_DESCRIPTIONS.get(m, {})
            desc = desc_obj.get(self.lang, desc_obj.get("en", ""))
            display_label = f"{m}\n{desc}" if desc else m
            self.modelCombo.Append(display_label)
            if m == clean_pref or display_label == preferred_model:
                pref_idx = idx
        if models:
            self.modelCombo.SetSelection(pref_idx)

    def onCategoryChange(self, evt):
        selected_cat = self.catCombo.GetStringSelection()
        self.updateModelList(selected_cat)

    def onGetToken(self, evt):
        webbrowser.open("https://mvsep.com/user-api")
        t = TEXTS.get(self.lang, TEXTS["id"])
        ui.message(t["open_token_page"])

    def onClearQueue(self, evt):
        t = TEXTS.get(self.lang, TEXTS["id"])
        api_token = self.tokenInput.GetValue().strip()
        if not api_token:
            ui.message(t["err_no_token"])
            return
        threading.Thread(target=self._runClearQueue, args=(api_token, self.lang), daemon=True).start()

    def _runClearQueue(self, api_token, lang):
        t = TEXTS.get(lang, TEXTS["id"])
        ui.message(t["checking_queue"])
        count = cancel_active_queue(api_token)
        if count > 0:
            ui.message(t["queue_cleared"].format(count=count))
        else:
            ui.message(t["queue_empty"])

    def onBrowse(self, evt):
        t = TEXTS.get(self.lang, TEXTS["id"])
        wildcard = "Audio Files (*.mp3;*.wav;*.flac;*.m4a;*.ogg)|*.mp3;*.wav;*.flac;*.m4a;*.ogg|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, t["select_file_dlg"], wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.selected_file = dlg.GetPath()
            fn = os.path.basename(self.selected_file)
            ui.message(t["file_selected"].format(filename=fn))
        dlg.Destroy()

    def onBrowseOut(self, evt):
        t = TEXTS.get(self.lang, TEXTS["id"])
        dlg = wx.DirDialog(self, t["select_folder_dlg"], defaultPath=self.outDirInput.GetValue(), style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.outDirInput.SetValue(dlg.GetPath())
        dlg.Destroy()

    def onProcess(self, evt):
        t = TEXTS.get(self.lang, TEXTS["id"])
        audio_file = self.selected_file.strip()
        category = self.catCombo.GetStringSelection()
        selected_model_str = self.modelCombo.GetStringSelection()
        model_name = selected_model_str.split("\n")[0].strip()
        api_token = self.tokenInput.GetValue().strip()
        out_format = self.formatCombo.GetStringSelection()
        out_dir = self.outDirInput.GetValue().strip()

        if not audio_file or not os.path.isfile(audio_file):
            ui.message(t["err_no_file"])
            return

        try:
            if os.path.getsize(audio_file) == 0:
                ui.message(t["err_empty_file"])
                return
        except Exception:
            pass

        if not api_token:
            ui.message(t["err_no_token"])
            return

        self.config["category"] = category
        self.config["model"] = model_name
        self.config["api_token"] = api_token
        self.config["format"] = out_format
        self.config["language"] = self.lang
        self.config["output_dir"] = out_dir
        save_config(self.config)

        self.Close()

        threading.Thread(
            target=self.run_mvsep_separation,
            args=(audio_file, category, model_name, api_token, out_format, out_dir, self.lang),
            daemon=True
        ).start()

    def run_mvsep_separation(self, audio_file, category, model_name, api_token, out_format, out_dir, lang):
        t = TEXTS.get(lang, TEXTS["id"])
        os.makedirs(out_dir, exist_ok=True)
        filename = os.path.basename(audio_file)
        base_name, _ = os.path.splitext(filename)

        cfg_params = MVSEP_CONFIG.get((category, model_name)) or MVSEP_CONFIG.get(model_name)
        if not cfg_params:
            ui.message(f"Error: Konfigurasi model {model_name} tidak ditemukan.")
            return

        sep_type, add_opt1, add_opt2 = cfg_params
        output_format_code = FORMAT_MAP.get(out_format, "1")

        ui.message(t["uploading"].format(filename=filename, model_name=model_name, out_format=out_format))
        try:
            winsound.Beep(880, 150)
        except Exception:
            pass

        try:
            create_url = "https://mvsep.com/api/separation/create"
            fields = {
                "api_token": api_token,
                "sep_type": str(sep_type),
                "output_format": output_format_code,
                "is_demo": "0"
            }
            if add_opt1 is not None:
                fields["add_opt1"] = str(add_opt1)
            if add_opt2 is not None:
                fields["add_opt2"] = str(add_opt2)
            files = {"audiofile": audio_file}
            content_type, body = encode_multipart(fields, files)

            req = urllib.request.Request(
                create_url,
                data=body,
                headers={"Content-Type": content_type, "User-Agent": "Mozilla/5.0"},
                method="POST"
            )

            resp_json = None
            max_wait_attempts = 120
            last_queue_announced = 0

            for attempt in range(max_wait_attempts):
                try:
                    with urllib.request.urlopen(req, timeout=180) as resp:
                        resp_json = json.loads(resp.read().decode('utf-8'))
                    if attempt > 0:
                        ui.message(t["turn_arrived"])
                        try:
                            winsound.Beep(880, 150)
                        except Exception:
                            pass
                    break
                except urllib.error.HTTPError as e:
                    raw_err = e.read().decode('utf-8', errors='ignore')
                    if "unprocessed file in queue" in raw_err.lower():
                        now_ts = time.time()
                        try:
                            winsound.Beep(587, 60)
                        except Exception:
                            pass

                        order_info = ""
                        try:
                            u_req = urllib.request.Request(f"https://mvsep.com/api/app/user?api_token={api_token}", headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(u_req, timeout=10) as u_resp:
                                u_data = json.loads(u_resp.read().decode('utf-8'))
                                q_list = u_data.get("data", {}).get("current_queue", [])
                                if q_list:
                                    active_hash = q_list[0]
                                    q_req = urllib.request.Request(f"https://mvsep.com/api/separation/get?hash={active_hash}&api_token={api_token}", headers={"User-Agent": "Mozilla/5.0"})
                                    with urllib.request.urlopen(q_req, timeout=10) as q_resp:
                                        q_data = json.loads(q_resp.read().decode('utf-8'))
                                        stat = q_data.get("status")
                                        d_info = q_data.get("data", {})
                                        if stat == "waiting":
                                            c_ord = d_info.get("current_order")
                                            order_info = f"Antrian {c_ord}" if c_ord is not None else ("Dalam antrian" if lang == "id" else "In queue")
                                        elif stat == "processing":
                                            order_info = "Sedang diproses di GPU" if lang == "id" else "Processing on GPU"
                        except Exception:
                            pass

                        if (now_ts - last_queue_announced) >= 15 or attempt == 0:
                            if order_info:
                                ui.message(order_info)
                            else:
                                ui.message(t["waiting_turn"])
                            last_queue_announced = now_ts

                        time.sleep(5)
                        continue
                    else:
                        detail = ""
                        try:
                            err_json = json.loads(raw_err)
                            detail = err_json.get("message") or err_json.get("data", {}).get("message")
                            if not detail and err_json.get("errors"):
                                detail = ", ".join(str(x) for x in err_json.get("errors"))
                        except Exception:
                            pass
                        if detail:
                            ui.message(f"Error server: {detail}")
                        else:
                            ui.message(f"Error server: HTTP {e.code}")
                        return

            if not resp_json or not resp_json.get("success"):
                err_msg = resp_json.get("message") if resp_json else "Gagal membuat tugas pemisahan."
                if not err_msg and resp_json:
                    err_msg = resp_json.get("data", {}).get("message", "Gagal membuat tugas pemisahan.")
                ui.message(f"Gagal: {err_msg}")
                return

            task_hash = resp_json.get("data", {}).get("hash")
            if not task_hash:
                ui.message("Gagal mendapatkan kode tugas pemisahan dari server.")
                return

            ui.message(t["upload_done"])
            try:
                winsound.Beep(988, 120)
            except Exception:
                pass

            get_url = f"https://mvsep.com/api/separation/get?hash={task_hash}&api_token={api_token}"
            download_files = None
            last_status = None
            last_order = None
            last_announced_time = 0

            for i in range(240):
                time.sleep(5)
                get_req = urllib.request.Request(get_url, headers={"User-Agent": "Mozilla/5.0"})
                try:
                    with urllib.request.urlopen(get_req, timeout=30) as g_resp:
                        g_json = json.loads(g_resp.read().decode('utf-8'))
                except Exception:
                    continue

                status = g_json.get("status")
                data_obj = g_json.get("data", {})

                if status == "failed":
                    fail_reason = data_obj.get("message") or "Pemisahan gagal di server."
                    try:
                        winsound.Beep(440, 300)
                    except Exception:
                        pass
                    ui.message(t["sep_failed"].format(reason=fail_reason))
                    return

                if status == "done":
                    download_files = data_obj.get("files", [])
                    try:
                        winsound.Beep(1046, 120)
                        winsound.Beep(1318, 150)
                    except Exception:
                        pass
                    ui.message(t["sep_done"])
                    break

                now_ts = time.time()
                if status == "waiting":
                    try:
                        winsound.Beep(587, 60)
                    except Exception:
                        pass
                    cur_order = data_obj.get("current_order")
                    order_str = f"Antrian {cur_order}" if cur_order is not None else ("Dalam antrian" if lang == "id" else "In queue")
                    
                    if cur_order != last_order or (now_ts - last_announced_time) >= 15:
                        ui.message(order_str)
                        last_order = cur_order
                        last_announced_time = now_ts
                    last_status = status

                elif status == "processing":
                    if last_status != "processing" or (now_ts - last_announced_time) >= 15:
                        ui.message(t["server_processing"])
                        try:
                            winsound.Beep(659, 80)
                        except Exception:
                            pass
                        last_announced_time = now_ts
                    last_status = status

                elif status in ("distributing", "merging"):
                    if last_status != status or (now_ts - last_announced_time) >= 15:
                        ui.message(t["stage_merging"].format(status=status))
                        last_announced_time = now_ts
                    last_status = status

            if not download_files:
                ui.message(t["timeout"])
                return

            for idx, item in enumerate(download_files, 1):
                f_url = item.get("link") or item.get("url")
                raw_type = item.get("type") or item.get("download") or (os.path.basename(f_url.split("?")[0]) if f_url else "")

                ext = os.path.splitext(f_url.split("?")[0])[1] if f_url else ""
                if not ext:
                    ext = ".mp3" if "MP3" in out_format else ".wav"

                clean_base = clean_filename_part(base_name)
                clean_stem = clean_filename_part(get_clean_stem_name(raw_type, category, model_name))
                clean_model = clean_filename_part(model_name)
                target_filename = f"{clean_base} ({clean_stem}) ({clean_model}){ext}"
                target_file_path = os.path.join(out_dir, target_filename)

                ui.message(t["downloading_stem"].format(idx=idx, total=len(download_files), stem=clean_stem))
                if f_url:
                    urllib.request.urlretrieve(f_url, target_file_path)

            try:
                winsound.Beep(1320, 200)
                winsound.Beep(1760, 250)
            except Exception:
                pass

            ui.message(t["all_saved"].format(out_dir=out_dir))
            os.startfile(out_dir)

        except urllib.error.HTTPError as e:
            detail = ""
            try:
                raw_err = e.read().decode('utf-8', errors='ignore')
                err_json = json.loads(raw_err)
                detail = err_json.get("message") or err_json.get("data", {}).get("message")
                if not detail and err_json.get("errors"):
                    detail = ", ".join(str(x) for x in err_json.get("errors"))
            except Exception:
                pass
            if detail:
                ui.message(f"Error server: {detail}")
            else:
                ui.message(f"Error server: HTTP {e.code}")
        except urllib.error.URLError as e:
            ui.message(f"Koneksi internet bermasalah: {e.reason}")
        except Exception as e:
            ui.message(f"Terjadi kesalahan: {e}")


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    @script(
        description="Membuka dialog NVDA Vocal Remover (BS-Roformer)",
        category="Audio",
        gesture="kb:NVDA+shift+x"
    )
    def script_openVocalRemover(self, gesture):
        wx.CallAfter(self._showDialog)

    def _showDialog(self):
        gui_main = gui.mainFrame
        d = VocalRemoverDialog(gui_main)
        d.ShowModal()
        d.Destroy()
