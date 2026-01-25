# Аналіз Шляхів Моделей у Fresh Install

**Дата**: 2026-01-25  
**Статус**: ✅ ПЕРЕВІРЕНО

---

## 📋 ЗАВДАННЯ

Перевірити чи fresh install ставить AI моделі в правильні шляхи та чи синхронізовано це з темплейтами та конфігами.

---

## 🔧 АНАЛІЗ ШЛЯХІВ

### **1. Офіційні Шляхи (config.py)**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/src/brain/config.py:44-47`

```python
# Централізовані шляхи для моделей
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
MODELS_DIR = CONFIG_ROOT / "models" / "tts"
WHISPER_DIR = CONFIG_ROOT / "models" / "faster-whisper"
STANZA_DIR = CONFIG_ROOT / "models" / "stanza"
NLTK_DIR = CONFIG_ROOT / "models" / "nltk"
```

✅ **Правильні шляхи** відповідно до XDG standard

---

### **2. Fresh Install Behavior**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/scripts/fresh_install.sh:133-158`

#### **Збереження Моделей:**
```bash
DELETE_MODELS="n"  # За замовчуванням НЕ видаляти
if [ "$DELETE_MODELS" == "n" ] && [ -d "$HOME/.config/atlastrinity/models" ]; then
    TEMP_MODELS="/tmp/atlastrinity_models_backup"
    mv "$HOME/.config/atlastrinity/models" "$TEMP_MODELS"
    rm -rf "$HOME/.config/atlastrinity"
    mkdir -p "$HOME/.config/atlastrinity"
    mv "$TEMP_MODELS" "$HOME/.config/atlastrinity/models"
    echo "✅ ~/.config/atlastrinity видалено (Models збережено)"
fi
```

✅ **Правильна поведінка** - моделі зберігаються при fresh install

---

### **3. Setup Dev Paths**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/scripts/setup_dev.py:61-73`

```python
DIRS = {
    "config": CONFIG_ROOT,
    "logs": CONFIG_ROOT / "logs",
    "memory": CONFIG_ROOT / "memory",
    "screenshots": CONFIG_ROOT / "screenshots",
    "tts_models": CONFIG_ROOT / "models" / "tts",      # ✅ Відповідає config.py
    "stt_models": CONFIG_ROOT / "models" / "faster-whisper",  # ✅ Відповідає config.py
    "mcp": CONFIG_ROOT / "mcp",
    "workspace": CONFIG_ROOT / "workspace",
    "vibe_workspace": CONFIG_ROOT / "vibe_workspace",
    "stanza": CONFIG_ROOT / "models" / "stanza",       # ✅ Відповідає config.py
    "huggingface": CONFIG_ROOT / "models" / "huggingface",
}
```

✅ **Синхронізовано** - всі шляхи відповідають config.py

---

### **4. Model Download Logic**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/scripts/setup_dev.py:716-727`

```python
stt_dir = DIRS["stt_models"]  # ~/.config/atlastrinity/models/faster-whisper
tts_dir = DIRS["tts_models"]  # ~/.config/atlastrinity/models/tts

# Перевірка наявності
stt_exists = (stt_dir / "model.bin").exists() or (stt_dir / model_name / "model.bin").exists()
tts_exists = any(tts_dir.iterdir()) if tts_dir.exists() else False
```

✅ **Правильна логіка** - перевіряє правильні шляхи

---

### **5. TTS Model Installation**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/scripts/setup_dev.py:775-781`

```python
cache_dir = Path('{tts_dir}')  # ~/.config/atlastrinity/models/tts
cache_dir.mkdir(parents=True, exist_ok=True)
os.chdir(str(cache_dir))
TTS(cache_folder='.', device='cpu')
```

✅ **Правильний шлях** - TTS встановлюється в `~/.config/atlastrinity/models/tts`

---

### **6. STT Model Installation**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/scripts/setup_dev.py:758`

```python
f"from faster_whisper import WhisperModel; WhisperModel('{model_name}', device='cpu', compute_type='int8', download_root='{stt_dir}')"
```

✅ **Правильний шлях** - STT встановлюється в `~/.config/atlastrinity/models/faster-whisper`

---

### **7. First Run Installer**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/src/brain/first_run_installer.py:31-36`

```python
from .config import CONFIG_ROOT, MCP_DIR, MODELS_DIR, WHISPER_DIR
# Fallback:
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
MODELS_DIR = CONFIG_ROOT / "models" / "tts"
WHISPER_DIR = CONFIG_ROOT / "models" / "faster-whisper"
```

✅ **Синхронізовано** - використовує ті ж шляхи

---

### **8. Voice Modules**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/src/brain/voice/stt.py:133`

```python
self.download_root = CONFIG_ROOT / "models" / "faster-whisper"
```

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/src/brain/voice/tts.py:262`

```python
if not MODELS_DIR.exists():  # ~/.config/atlastrinity/models/tts
```

✅ **Синхронізовано** - voice модулі використовують правильні шляхи

---

## 📊 СИНХРОНІЗАЦІЯ З КОНФІГАМИ

### **Config Template Variables**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/config/config.yaml.template`

```yaml
voice:
  tts:
    model_path: "~/.config/atlastrinity/models/tts"
  stt:
    model_path: "~/.config/atlastrinity/models/faster-whisper"
```

✅ **Синхронізовано** - темплейти використовують ті ж шляхи

---

### **Environment Variables**

**Файл:** `@/Users/hawk/Documents/GitHub/atlastrinity/src/brain/config.py:54-56`

```python
os.environ["STANZA_RESOURCES_DIR"] = str(STANZA_DIR)     # ~/.config/atlastrinity/models/stanza
os.environ["NLTK_DATA"] = str(NLTK_DIR)                # ~/.config/atlastrinity/models/nltk
os.environ["HF_HOME"] = str(CONFIG_ROOT / "models" / "huggingface")
```

✅ **Синхронізовано** - environment variables встановлюються правильно

---

## 🎯 ПЕРЕВІРКА РЕЗУЛЬТАТІВ

### **Очікувана структура після fresh install:**

```
~/.config/atlastrinity/
├── models/
│   ├── tts/                     # Ukrainian TTS models
│   │   ├── model.pth
│   │   ├── config.yaml
│   │   ├── feats_stats.npz
│   │   └── spk_xvector.ark
│   ├── faster-whisper/          # STT models
│   │   └── models--deepdml--faster-whisper-large-v3-ct2/
│   │       ├── config.json
│   │       ├── model.bin
│   │       └── tokenizer.json
│   ├── stanza/                  # NLP models
│   ├── nltk/                    # NLTK data
│   └── huggingface/             # HF cache
├── mcp/
├── logs/
├── memory/
└── workspace/
```

---

## ✅ ВИСНОВОК

| Компонент | Шлях | Статус |
|-----------|-------|--------|
| **TTS Models** | `~/.config/atlastrinity/models/tts` | ✅ Правильно |
| **STT Models** | `~/.config/atlastrinity/models/faster-whisper` | ✅ Правильно |
| **Stanza** | `~/.config/atlastrinity/models/stanza` | ✅ Правильно |
| **NLTK** | `~/.config/atlastrinity/models/nltk` | ✅ Правильно |
| **HF Cache** | `~/.config/atlastrinity/models/huggingface` | ✅ Правильно |

### **Перевірено:**

1. ✅ **Fresh Install** - зберігає моделі при очищенні конфігурації
2. ✅ **Setup Dev** - використовує правильні шляхи для завантаження
3. ✅ **First Run Installer** - синхронізовано з config.py
4. ✅ **Voice Modules** - використовують правильні шляхи
5. ✅ **Config Templates** - відповідають реальним шляхам
6. ✅ **Environment Variables** - встановлені правильно

---

## 📝 РЕКОМЕНДАЦІЇ

**Система працює правильно!** ✅

- Fresh install коректно зберігає моделі
- Всі шляхи синхронізовані між компонентами
- Config templates відповідають реальності
- Environment variables встановлені правильно

**Немає потреби в змінах.**
