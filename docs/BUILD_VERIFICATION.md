# 🔍 КОНТРОЛЬНА ПЕРЕВІРКА: AtlasTrinity Build & Config
## Дата: 2026-01-06

---

## 📦 Production Bundle (package.json)

### extraResources копіюються в .app/Contents/Resources/

✅ **Python код**:
- `src/brain/**/*.py` → `Resources/brain/`
- `providers/**/*.py` → `Resources/providers/`
- `src/mcp/**/*.py` → `Resources/mcp/`

✅ **Python venv**:
- `dist_venv/**/*` → `Resources/.venv/`
  - Створюється `build_mac_custom.sh` з `cp -HLR .venv dist_venv`
  - Follow symlinks для портабельності

✅ **Конфігураційні файли** (для production_setup.py):
- `.env` → `Resources/.env`
- `config.yaml` → `Resources/config.yaml`

❌ **НЕ копіюються** (і правильно):
- TTS моделі (`models/tts/`) - авто-завантаження ukrainian-tts
- STT моделі (Whisper) - авто-завантаження whisper

---

## 🔧 Build Scripts

### build_mac_custom.sh

✅ **Правильно**:
```bash
# 1. Disable spoofing
# 2. Clear env vars
# 3. Set MACOSX_DEPLOYMENT_TARGET=26.3
# 4. Set SDKROOT (Xcode Beta)
# 5. Create dist_venv з cp -HLR
# 6. npm run build
# 7. electron-builder
```

⚠️ **Потенційна проблема**: `dist_venv` може бути великим (~500MB+)

### npm run build:mac:custom

✅ Запускає `build_mac_custom.sh`

---

## 🛠️ Setup Scripts

### setup_dev.py

✅ **Створює структуру**:
```
~/.config/atlastrinity/
├── logs/
├── memory/
├── screenshots/
└── models/tts/
```

✅ **Копіює конфіги**:
- `.env` (project → ~/.config/)
- `config.yaml` (project → ~/.config/)

✅ **НЕ копіює моделі** (правильно):
- TTS: ukrainian-tts auto-download
- STT: Whisper auto-download

⚠️ **Інформація про синхронізацію**:
```
ℹ️  Важливо: Система працює з config.yaml!
   - Користувач працює з .env (зручно)
   - При старті .env автоматично синхронізується в config.yaml
   - Система читає ТІЛЬКИ config.yaml
```

### production_setup.py

✅ **Перевіряє production**:
```python
def is_production():
    return getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')
```

✅ **Знаходить Resources/**:
```python
def get_resources_path():
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    elif getattr(sys, 'frozen', False):
        return Path(sys.executable).parent.parent / "Resources"
```

✅ **Копіює конфіги** (якщо не існують):
- `Resources/.env` → `~/.config/atlastrinity/.env`
- `Resources/config.yaml` → `~/.config/atlastrinity/config.yaml`

---

## 📝 Config Files

### config.yaml (системний)

**Розташування**:
- Dev: `~/.config/atlastrinity/config.yaml` (копія з project)
- Production: `~/.config/atlastrinity/config.yaml` (копія з Resources)

✅ **Структура**:
```yaml
api:               # API ключі (з .env)
agents:            # Налаштування агентів
  atlas:
    model: "raptor-mini"
  tetyana:
    model: "gpt-4o"
  grisha:
    vision_model: "gpt-4o"
mcp:               # MCP сервери
  terminal:
    model: "gpt-4o"
  whisper:         # ✅ Є конфіг Whisper
    model: "base"
    language: "uk"
security:          # Dangerous commands
voice:             # TTS/STT налаштування
  tts:
    device: "mps"
  stt:
    model: "base"
    language: "uk"
logging:           # Логування
```

### .env

**Розташування**:
- Dev: `~/.config/atlastrinity/.env` (копія з project)
- Production: `~/.config/atlastrinity/.env` (копія з Resources)

✅ **Синхронізація**: `.env` → `config.yaml` при старті (config_sync.py)

---

## 🗣️ Voice Configuration

### TTS (ukrainian-tts)

**Моделі**:
```
~/.config/atlastrinity/models/tts/
├── model.pth
├── config.yaml          # ❗ TTS config (НЕ системний!)
├── feats_stats.npz
└── spk_xvector.ark
```

**Завантаження**: Автоматично ukrainian-tts з Hugging Face

✅ **Код читає з правильного місця** (tts.py):
```python
from ..config import MODELS_DIR  # ~/.config/atlastrinity/models/tts/

self._tts = TTS(cache_folder=str(MODELS_DIR), device=self.device)
```

❌ **НЕ читає device з config.yaml**:
```python
# Зараз:
def __init__(self, agent_name: str, device: str = "mps"):
    self.device = device  # Hardcoded default

# Має бути:
def __init__(self, agent_name: str, device: str = None):
    voice_config = config.get("voice.tts", {})
    self.device = device or voice_config.get("device", "mps")
```

### STT (OpenAI Whisper)

**Моделі**: `~/.cache/whisper/` (стандартне Whisper розташування)

**Завантаження**: Автоматично whisper.load_model()

❌ **НЕ читає з config.yaml**:
```python
# Зараз:
def __init__(self, model_name: str = "base", device: str = None):
    self.model_name = model_name  # Hardcoded default

# Має бути:
def __init__(self, model_name: str = None, device: str = None):
    stt_config = config.get("voice.stt", {})
    self.model_name = model_name or stt_config.get("model", "base")
```

---

## 🔄 Runtime Config Loading

### server.py (FastAPI brain server)

✅ **При старті**:
```python
from .config_sync import sync_env_to_config, get_api_key

# 1. Синхронізація .env → config.yaml
sync_env_to_config()

# 2. Завантаження API ключів
copilot_key = get_api_key("copilot_api_key")
os.environ["COPILOT_API_KEY"] = copilot_key
```

✅ **Пріоритет**: `config.yaml > .env > defaults`

### Агенти

✅ **Atlas**:
```python
from ..config_loader import config

agent_config = config.get_agent_config("atlas")
final_model = agent_config.get("model") or os.getenv("COPILOT_MODEL", "raptor-mini")
```

✅ **Tetyana**:
```python
agent_config = config.get_agent_config("tetyana")
final_model = agent_config.get("model") or os.getenv("COPILOT_MODEL", "gpt-4o")
```

✅ **Grisha**:
```python
agent_config = config.get_agent_config("grisha")
security_config = config.get_security_config()

final_model = agent_config.get("vision_model") or os.getenv("VISION_MODEL", "gpt-4o")
self.dangerous_commands = security_config.get("dangerous_commands", self.BLOCKLIST)
```

---

## 🎯 Глобальна папка ~/.config/atlastrinity/

### ✅ Правильно розташовані:

```
~/.config/atlastrinity/
├── .env                    # API ключі (source для синхронізації)
├── config.yaml             # Системний конфіг (головний)
├── logs/
│   ├── atlas.log
│   ├── tetyana.log
│   └── grisha.log
├── memory/
│   └── (plan_memory, execution_memory)
├── screenshots/
│   └── (verification screenshots)
└── models/
    └── tts/
        ├── model.pth
        ├── config.yaml     # TTS тренувальний конфіг
        ├── feats_stats.npz
        └── spk_xvector.ark
```

### ⚠️ Поза глобальною папкою:

```
~/.cache/whisper/
├── base.pt                 # Whisper model
└── (інші моделі)
```

**Пояснення**: Це стандартне розташування Whisper, змінювати недоцільно.

---

## 🚨 Виявлені проблеми

### ❌ КРИТИЧНО:

**1. TTS не читає device з config.yaml**
```python
# src/brain/voice/tts.py line ~72
def __init__(self, agent_name: str, device: str = "mps"):
    self.device = device  # Треба читати з config!
```

**2. STT не читає model з config.yaml**
```python
# src/brain/voice/stt.py line ~48
def __init__(self, model_name: str = "base", device: str = None):
    self.model_name = model_name  # Треба читати з config!
```

**3. MCP сервери не читають моделі з config.yaml**
- `terminal_server.py` - має використовувати `mcp.terminal.model`
- `playwright_server.py` - має використовувати `mcp.playwright.model`
- `computer_use.py` - має використовувати `mcp.computer_use.model`
- `whisper_server.py` - має використовувати `mcp.whisper.model`

### ⚠️ СЕРЕДНЬО:

**4. dist_venv може бути занадто великим**
- Розмір: ~500MB+
- Рішення: Можна оптимізувати, видаливши тести/docs з бібліотек

### ℹ️ ІНФОРМАЦІЯ:

**5. Whisper моделі поза ~/.config/atlastrinity/**
- Це нормально - стандартне розташування Whisper
- Можна змінити через `whisper.load_model(..., download_root=)`

---

## ✅ План виправлень

### 1. Інтегрувати config_loader в TTS
```python
from ..config_loader import config

class UkrainianTTS:
    def __init__(self, agent_name: str, device: str = None):
        voice_config = config.get("voice.tts", {})
        self.device = device or voice_config.get("device", "mps")
```

### 2. Інтегрувати config_loader в STT
```python
from ..config_loader import config

class WhisperSTT:
    def __init__(self, model_name: str = None, device: str = None):
        stt_config = config.get("voice.stt", {})
        self.model_name = model_name or stt_config.get("model", "base")
        self.language = stt_config.get("language", "uk")
```

### 3. Додати моделі в MCP конфіг
```yaml
mcp:
  whisper:
    enabled: true
    model: "base"      # tiny, base, small, medium, large
    language: "uk"
```

### 4. Інтегрувати config_loader в MCP сервери
```python
# whisper_server.py
from src.brain.config_loader import config

mcp_config = config.get_mcp_config()
whisper_config = mcp_config.get("whisper", {})
model = whisper_config.get("model", "base")
```

---

## 📋 Контрольний чеклист

### Dev workflow

- [x] `./scripts/setup.sh` створює `~/.config/atlastrinity/`
- [x] Копіюється `.env` та `config.yaml`
- [x] `npm run dev` синхронізує `.env` → `config.yaml`
- [x] Агенти читають моделі з `config.yaml`
- [x] TTS читає device з `config.yaml` ✅ ВИПРАВЛЕНО
- [x] STT читає model з `config.yaml` ✅ ВИПРАВЛЕНО
- [ ] MCP сервери читають моделі з `config.yaml`

### Production workflow

- [x] `build_mac_custom.sh` створює `dist_venv`
- [x] `electron-builder` пакує все в `.app`
- [x] `.env` та `config.yaml` в `Resources/`
- [x] При першому запуску `production_setup.py` копіює конфіги
- [x] `server.py` синхронізує `.env` → `config.yaml`
- [x] Агенти читають моделі з `config.yaml`
- [x] TTS читає device з `config.yaml` ✅ ВИПРАВЛЕНО
- [x] STT читає model з `config.yaml` ✅ ВИПРАВЛЕНО
- [ ] MCP сервери читають моделі з `config.yaml`

### Моделі та конфіги

- [x] TTS моделі: `~/.config/atlastrinity/models/tts/`
- [x] TTS автозавантаження: ukrainian-tts
- [x] STT моделі: `~/.config/atlastrinity/models/whisper/` ✅ ВИПРАВЛЕНО
- [x] STT автозавантаження: whisper.load_model()
- [x] Системний конфіг: `~/.config/atlastrinity/config.yaml`
- [x] TTS тренувальний конфіг: `~/.config/atlastrinity/models/tts/config.yaml`

---

## 🎯 Висновок

### ✅ Працює правильно:

1. **Build процес** - всі файли копіюються в bundle
2. **Setup scripts** - створюють правильну структуру
3. **Config синхронізація** - `.env` → `config.yaml`
4. **Агенти** - читають моделі з `config.yaml`
5. **Глобальна папка** - все в `~/.config/atlastrinity/`

### ❌ Треба виправити:

1. ~~**TTS** - не читає `device` з `config.yaml`~~ ✅ ВИПРАВЛЕНО
2. ~~**STT** - не читає `model` з `config.yaml`~~ ✅ ВИПРАВЛЕНО
3. ~~**STT** - моделі в `~/.cache/` замість глобальної папки~~ ✅ ВИПРАВЛЕНО
4. ~~**MCP Whisper** - не читає конфіг з `config.yaml`~~ ✅ ВИПРАВЛЕНО
5. **MCP Terminal/Playwright/Computer Use** - не читають моделі з `config.yaml` (не критично)

### 📝 Рекомендації:

1. Інтегрувати `config_loader` в TTS/STT
2. Додати моделі в MCP конфіг
3. Протестувати production build
4. Оптимізувати `dist_venv` (опціонально)
