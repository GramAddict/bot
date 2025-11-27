#!/bin/bash
# Skrypt instalacyjny dla Ollama i wymaganych narzędzi
# Instaluje Ollama oraz opcjonalnie polecane modele

set -e

echo "========================================"
echo "Instalacja Ollama"
echo "========================================"

# Funkcja sprawdzająca system operacyjny
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

# Instalacja Ollama
install_ollama() {
    local os=$(detect_os)

    echo "Wykryto system: $os"

    case $os in
        "linux")
            echo "Instalacja Ollama dla Linux..."
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        "macos")
            echo "Instalacja Ollama dla macOS..."
            if command -v brew &> /dev/null; then
                brew install ollama
            else
                echo "Homebrew nie jest zainstalowany. Pobieranie ze strony ollama.com..."
                curl -fsSL https://ollama.com/install.sh | sh
            fi
            ;;
        "windows")
            echo "Dla Windows, pobierz instalator z: https://ollama.com/download/windows"
            echo "Lub użyj: winget install Ollama.Ollama"
            exit 1
            ;;
        *)
            echo "Nieznany system operacyjny. Odwiedź https://ollama.com dla instrukcji."
            exit 1
            ;;
    esac
}

# Sprawdzenie czy Ollama jest już zainstalowana
if command -v ollama &> /dev/null; then
    echo "✓ Ollama jest już zainstalowana!"
    ollama --version
    read -p "Czy chcesz zaktualizować Ollama? (t/n): " update_choice
    if [[ $update_choice == "t" ]] || [[ $update_choice == "T" ]]; then
        install_ollama
    fi
else
    install_ollama
fi

echo ""
echo "========================================"
echo "Konfiguracja Ollamy"
echo "========================================"

# Uruchomienie serwisu Ollama
echo "Uruchamianie serwisu Ollama..."
if [[ $(detect_os) == "linux" ]]; then
    # Dla systemd
    if command -v systemctl &> /dev/null; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
        echo "✓ Serwis Ollama uruchomiony przez systemd"
    else
        # Uruchom w tle
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        echo "✓ Ollama uruchomiona w tle"
    fi
elif [[ $(detect_os) == "macos" ]]; then
    # macOS - ollama serve w tle
    brew services start ollama 2>/dev/null || (nohup ollama serve > /tmp/ollama.log 2>&1 &)
    echo "✓ Serwis Ollama uruchomiony"
fi

# Poczekaj chwilę na uruchomienie serwisu
sleep 3

echo ""
echo "========================================"
echo "Instalacja polecaných modeli"
echo "========================================"

# Polecane modele dla projektu
MODELS=(
    "llama3.2:latest"
    "qwen2.5:latest"
    "codellama:latest"
)

echo "Polecane modele dla tego projektu:"
for i in "${!MODELS[@]}"; do
    echo "  $((i+1)). ${MODELS[$i]}"
done

read -p "Czy chcesz zainstalować polecane modele? (t/n): " install_models

if [[ $install_models == "t" ]] || [[ $install_models == "T" ]]; then
    for model in "${MODELS[@]}"; do
        echo ""
        echo "Pobieranie modelu: $model"
        ollama pull "$model"
    done
    echo "✓ Wszystkie modele zainstalowane"
else
    echo "Możesz zainstalować modele później używając: ollama pull <nazwa-modelu>"
fi

echo ""
echo "========================================"
echo "Instalacja dodatkowych narzędzi"
echo "========================================"

# Opcjonalna instalacja Open WebUI
read -p "Czy chcesz zainstalować Open WebUI (wymaga Docker)? (t/n): " install_webui

if [[ $install_webui == "t" ]] || [[ $install_webui == "T" ]]; then
    if command -v docker &> /dev/null; then
        echo "Instalacja Open WebUI..."
        docker run -d \
            -p 3000:8080 \
            --add-host=host.docker.internal:host-gateway \
            -v open-webui:/app/backend/data \
            --name open-webui \
            --restart always \
            ghcr.io/open-webui/open-webui:main
        echo "✓ Open WebUI uruchomione na http://localhost:3000"
    else
        echo "⚠ Docker nie jest zainstalowany. Pomiń instalację Open WebUI."
    fi
fi

echo ""
echo "========================================"
echo "Instalacja bibliotek Python dla Ollama"
echo "========================================"

# Instalacja ollama-python
if command -v pip &> /dev/null || command -v pip3 &> /dev/null; then
    PIP_CMD=$(command -v pip3 &> /dev/null && echo "pip3" || echo "pip")

    echo "Instalacja ollama-python..."
    $PIP_CMD install ollama

    echo "Instalacja dodatkowych bibliotek..."
    $PIP_CMD install langchain langchain-community llama-index

    echo "✓ Biblioteki Python zainstalowane"
else
    echo "⚠ pip nie jest dostępny. Zainstaluj ręcznie: pip install ollama langchain llama-index"
fi

echo ""
echo "========================================"
echo "✓ Instalacja zakończona!"
echo "========================================"
echo ""
echo "Ollama jest gotowa do użycia!"
echo ""
echo "Podstawowe komendy:"
echo "  ollama list                    # Lista zainstalowanych modeli"
echo "  ollama run llama3.2           # Uruchom model interaktywnie"
echo "  ollama pull <model>           # Pobierz nowy model"
echo "  ollama serve                  # Uruchom serwer Ollama"
echo ""
echo "API dostępne pod: http://localhost:11434"
if [[ $install_webui == "t" ]] || [[ $install_webui == "T" ]]; then
    echo "Open WebUI dostępne pod: http://localhost:3000"
fi
echo ""
