# Instrukcja instalacji

Ten dokument opisuje proces instalacji wszystkich wymaganych programów i zależności dla projektu GramAddict z rozszerzeniem LLaMA.

## Spis treści

- [Wymagania systemowe](#wymagania-systemowe)
- [Instalacja Ollama](#instalacja-ollama)
- [Instalacja zależności Python](#instalacja-zależności-python)
- [Konfiguracja rozszerzenia LLaMA](#konfiguracja-rozszerzenia-llama)
- [Weryfikacja instalacji](#weryfikacja-instalacji)

---

## Wymagania systemowe

### Minimalne wymagania:
- **System operacyjny:** Linux (Ubuntu 20.04+), macOS 11+, lub Windows 10/11
- **RAM:** 8 GB (16 GB zalecane dla większych modeli)
- **Dysk:** 20 GB wolnego miejsca
- **Python:** 3.8 lub nowszy
- **Git:** Do klonowania repozytorium

### Opcjonalne:
- **Docker:** Do uruchomienia Open WebUI
- **GPU:** NVIDIA GPU z CUDA dla szybszego wnioskowania (opcjonalne)

---

## Instalacja Ollama

Ollama to lokalne środowisko do uruchamiania dużych modeli językowych (LLM). Jest kluczowym komponentem dla rozszerzenia LLaMA w tym projekcie.

### Automatyczna instalacja (zalecane)

Użyj dostarczonego skryptu instalacyjnego:

```bash
cd scripts
./install_ollama.sh
```

Skrypt automatycznie:
- Wykryje Twój system operacyjny
- Zainstaluje Ollama
- Uruchomi serwis Ollama
- Zaproponuje instalację polecaných modeli
- Opcjonalnie zainstaluje Open WebUI
- Zainstaluje biblioteki Python dla Ollama

### Instalacja ręczna

#### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Uruchom serwis:
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

#### macOS

Przy użyciu Homebrew:
```bash
brew install ollama
brew services start ollama
```

Lub pobierz z [ollama.com](https://ollama.com/download/mac)

#### Windows

Pobierz instalator z [ollama.com/download/windows](https://ollama.com/download/windows)

Lub użyj winget:
```bash
winget install Ollama.Ollama
```

### Instalacja modeli

Po zainstalowaniu Ollama, pobierz polecane modele:

```bash
# Ogólny model LLaMA 3.2
ollama pull llama3.2:latest

# Model Qwen 2.5 (dobry dla języka polskiego)
ollama pull qwen2.5:latest

# Model dla generowania kodu
ollama pull codellama:latest
```

Sprawdź zainstalowane modele:
```bash
ollama list
```

---

## Instalacja zależności Python

### 1. Zainstaluj podstawowe zależności projektu

```bash
pip install -r requirements.txt
```

### 2. Zainstaluj biblioteki dla Ollama i LLaMA

```bash
pip install ollama
pip install langchain langchain-community
pip install llama-index
```

### 3. Opcjonalne biblioteki dla zaawansowanych funkcji

```bash
# Dla przetwarzania obrazów
pip install Pillow opencv-python

# Dla integracji z Google
pip install google-auth google-api-python-client

# Dla przetwarzania plików
pip install python-docx openpyxl PyPDF2

# Dla syntezy mowy
pip install azure-cognitiveservices-speech
```

---

## Konfiguracja rozszerzenia LLaMA

### 1. Konfiguracja podstawowa

Utwórz plik konfiguracyjny `config/llama_config.yml`:

```yaml
model:
  model_path: "~/.ollama/models"
  quantization_bits: 8
  context_window: 4096
  language: "pl"

ollama:
  host: "http://localhost:11434"
  default_model: "qwen2.5:latest"

speech:
  enable: true
  voice: "pl-PL-EwaNeural"
  speaking_rate: 1.0
  audio_format: "mp3"
```

### 2. Opcjonalna konfiguracja Google

Jeśli chcesz używać integracji z Google:

1. Pobierz plik `credentials.json` z [Google Cloud Console](https://console.cloud.google.com)
2. Umieść go w `config/google_credentials.json`
3. Zaktualizuj konfigurację:

```yaml
google:
  credentials_file: "config/google_credentials.json"
  scopes:
    - "https://www.googleapis.com/auth/drive"
    - "https://www.googleapis.com/auth/docs"
```

---

## Weryfikacja instalacji

### 1. Sprawdź Ollama

```bash
ollama --version
ollama list
```

Powinieneś zobaczyć wersję Ollama i listę zainstalowanych modeli.

### 2. Sprawdź API Ollama

```bash
curl http://localhost:11434/api/tags
```

Powinieneś otrzymać JSON z listą modeli.

### 3. Test rozszerzenia LLaMA

```bash
cd extra/llama_extension
python demo.py --model-path ~/.ollama/models --confirm "Witaj, świecie!"
```

### 4. Test integracji z projektem głównym

```bash
python -c "from extra.llama_extension import LlamaMultimodalAssistant; print('✓ Import sukces')"
```

---

## Opcjonalne narzędzia

### Open WebUI

Open WebUI to nowoczesny interfejs webowy dla Ollama.

**Instalacja przez Docker:**

```bash
docker run -d \
  -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

Otwórz w przeglądarce: http://localhost:3000

### Ollama Desktop

Graficzny interfejs dla Ollama:
- Pobierz z [ollama.com/download](https://ollama.com/download)

---

## Rozwiązywanie problemów

### Ollama nie uruchamia się

**Linux:**
```bash
sudo systemctl status ollama
sudo journalctl -u ollama -f
```

**macOS/Linux (ręczne uruchomienie):**
```bash
ollama serve
```

### Port 11434 jest zajęty

Zmień port w konfiguracji:
```bash
OLLAMA_HOST=0.0.0.0:11435 ollama serve
```

### Brak pamięci przy uruchamianiu modelu

Użyj mniejszego modelu lub kwantyzacji:
```bash
ollama pull llama3.2:7b-q4_0  # 4-bitowa kwantyzacja
```

### Python nie znajduje modułu ollama

```bash
pip install --upgrade ollama
```

---

## Dodatkowe zasoby

- [Dokumentacja Ollama](https://github.com/ollama/ollama/blob/main/README.md)
- [Lista dostępnych modeli](https://ollama.com/library)
- [Dokumentacja LangChain](https://python.langchain.com/)
- [LLaMA Index](https://docs.llamaindex.ai/)

---

## Pomoc

Jeśli napotkasz problemy:

1. Sprawdź [Issues](../../issues) w repozytorium
2. Przeczytaj [FAQ](./FAQ.md)
3. Utwórz nowy Issue z opisem problemu

---

**Ostatnia aktualizacja:** 2025-11-27
