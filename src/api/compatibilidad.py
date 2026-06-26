# --- PARCHES DE COMPATIBILIDAD DE PYTORCH Y LIBRERÍAS ---
import torch
import torchaudio
import omegaconf
import sys, types
import numpy as np

# 1. Parche para torchaudio >= 2.1 con pyannote
if not hasattr(torchaudio, "AudioMetaData"):
    torchaudio.AudioMetaData = type('AudioMetaData', (object,), {})
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]
if not hasattr(torchaudio, "set_audio_backend"):
    torchaudio.set_audio_backend = lambda backend: None
if not hasattr(torchaudio, "get_audio_backend"):
    torchaudio.get_audio_backend = lambda: "soundfile"

if 'torchaudio.backend' not in sys.modules:
    tb = types.ModuleType('torchaudio.backend')
    tb.__path__ = []
    sys.modules['torchaudio.backend'] = tb
    torchaudio.backend = tb

if 'torchaudio.backend.common' not in sys.modules:
    tbc = types.ModuleType('torchaudio.backend.common')
    tbc.AudioMetaData = type('AudioMetaData', (object,), {})
    sys.modules['torchaudio.backend.common'] = tbc
    tb.common = tbc

if not hasattr(np, "NaN"):
    np.NaN = np.nan
if not hasattr(np, "NAN"):
    np.NAN = np.nan

sys.modules['speechbrain.integrations.k2_fsa'] = types.ModuleType('speechbrain.integrations.k2_fsa')

# 2. Parche definitivo para PyTorch >= 2.6 (Weights only load failed)
_original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

# 3. Parche para huggingface_hub (Pyannote usa use_auth_token pero hf pide token)
import huggingface_hub
_old_hf_hub_download = huggingface_hub.hf_hub_download
def _safe_hf_hub_download(*args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _old_hf_hub_download(*args, **kwargs)
huggingface_hub.hf_hub_download = _safe_hf_hub_download
# --------------------------------------------------------
