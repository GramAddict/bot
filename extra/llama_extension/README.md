# LLaMA Qwen 3/8 B Multimodal Extension

Ten moduł jest szkicem rozszerzenia dla modelu rodziny LLaMA/Qwen o nowoczesne możliwości pracy z multimodalnymi danymi i kontekstową interakcją. Poniżej zebrano główne funkcje, które można zaimplementować w projekcie produkcyjnym.

## Najważniejsze funkcje
1. **Obsługa obrazów** – wstępne przetwarzanie (`Pillow`, `opencv-python`), ekstrakcja cech (np. `CLIP`, `BLIP`) i przekazywanie embeddingów jako dodatkowego kontekstu do modelu językowego.
2. **Integracja z Google** – autoryzacja OAuth 2.0 oraz wykorzystanie API (Drive, Docs, Calendar) do wymiany danych i synchronizacji. W Pythonie można wykorzystać `google-auth` + `google-api-python-client`.
3. **Udostępnianie i interakcja z ekranem** – prototypowe rozwiązanie może bazować na `pyautogui`, `opencv-python` i `websockets`/`FastAPI` do przekazywania obrazu, interakcji kursora i komend.
4. **Pełna obsługa języka polskiego** – dobranie odpowiedniego tokenizer-a, fine-tuning na polskich korpusach oraz ustawienie domyślnej konfiguracji językowej (`language="pl"`).
5. **Analiza psychologiczna i trening** – moduł psychologiczny śledzący ton wypowiedzi, harmonogramy treningowe oraz ładowanie najnowszych korpusów terapeutycznych.
6. **Czytanie dowolnych formatów plików** – warstwa ingestii rozpoznająca tekst, dokumenty biurowe, multimedia i archiwa z możliwością dalszego przetwarzania (w tym tryb uniwersalny dla nieznanych rozszerzeń).
7. **Bazy wiedzy domenowej** – integracja źródeł z zakresu etycznego hakowania, gotowania, pisania i redagowania książek, hardeningu systemów, szyfrowania i maskowania wrażliwych danych.
8. **Profile korporacyjne Google i Samsung** – możliwość włączania aktualnych materiałów referencyjnych wraz z harmonogramem odświeżania.
9. **Generowanie kodu Python w czacie** – moduł tworzący szkice funkcji, z informacją o środowisku i konwencjach formatowania.
10. **Maskowanie danych i biały szum** – warstwa ochrony redagująca hasła/tokeny i dodająca informację o zastosowanym maskowaniu.
11. **Optymalizacja pod konkretny komputer** – profilowanie (np. `psutil`) i dynamiczna regulacja zużycia zasobów (limit GPU RAM, zarządzanie batch size, kwantyzacja 4bit/8bit).
12. **Syntezator mowy w języku polskim** – generowanie instrukcji produkcji audio (np. Azure TTS) z wyborem głosu, tempa i formatu.
13. **Syntezator mowy w języku ormiańskim** – analogiczna warstwa TTS dla języka ormiańskiego z osobną konfiguracją głosu i formatu.
14. **Wspomaganie interakcji ekranowych** – gotowe komunikaty podkreślające elementy UI i sugerujące kliknięcia z kolorem podświetlenia.
15. **Podwójne generowanie kodu** – oprócz Pythona dostępne są szkice komend PowerShell wraz z profilem i polityką wykonania.
16. **Mostek do Windows Voice Control** – możliwość przekierowania polskiej i ormiańskiej syntezy mowy do sterowania głosowego Windows 11 (Voice Access), wraz z instrukcjami przygotowania makr.
17. **Zarządzanie pamięcią modeli** – przydzielanie szyfrowanej pamięci długoterminowej dla modeli Ollamy i LLaMA na podstawie explicite potwierdzonych próśb użytkownika.
18. **Profil psychologiczny i preferencyjny użytkownika** – przechowywanie tonu, formalności, zainteresowań i notatek terapeutycznych z opcją automatycznej aktualizacji podczas interakcji.
19. **Wymóg potwierdzeń użytkownika** – każda akcja (generowanie, trening, synteza, dostęp do pamięci itd.) jest blokowana do czasu uzyskania zgody użytkownika, wraz z audytem zatwierdzonych czynności.
20. **Intuicyjny wybór specjalistów modeli** – moduł routingu rozpoznaje, czy zapytanie dotyczy kodowania, analizy danych Google czy rozmowy psychologicznej i deleguje je do odpowiedniego eksperta, podpisując odpowiedź nazwą wybranego AI.
21. **Integracje z innymi AI tylko na żądanie** – połączenia z zewnętrznymi asystentami są uruchamiane dopiero po potwierdzeniu użytkownika, a w ich pamięci zapisywany jest wyłącznie biały szum zamiast treści rozmowy.
22. **Offline'owe magazynowanie planów** – wszystkie dane i plany są zapisywane lokalnie dla Ollamy; konfiguracja wymusza tryb offline i przypomina o braku synchronizacji z chmurą.

## Rekomendowane narzędzia dla Ollamy
- **Narzędzia deweloperskie:** `litellm`, `ollama-python`, `langchain`, `llama-index`.
- **Interfejsy użytkownika:** Open WebUI, Ollama Desktop, chatbox.
- **Integracje:** `ollama-js`, `ollama-ruby`, `ollama-go`.
- **Monitorowanie:** `prometheus-ollama-exporter`, dashboardy Grafany.
- **Dodatkowe funkcje:** text-generation-webui, ollama-supervisor, model-converters.
- **Wersje konteneryzowane:** oficjalny obraz Docker Ollamy, helm chart/manifest `ollama-kubernetes`.
- **Szybki start Open WebUI:**
  ```bash
  docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway \
    -v open-webui:/app/backend/data --name open-webui --restart always \
    ghcr.io/open-webui/open-webui:main
  ```

## Struktura
```
extra/llama_extension/
├── README.md            # dokumentacja i lista zadań
├── config.py            # definicje konfiguracji
├── assistant.py         # logika asystenta i integracje
└── demo.py              # przykładowa aplikacja CLI / HTTP
```

## Kroki implementacji
1. **Model i tokenizer** – w pliku `assistant.py` dodać ładowanie modelu z `transformers` albo środowiska llama.cpp. Umożliwić tryb 4/8-bit (`bitsandbytes`, `ggml`).
2. **Ekstrakcja z obrazów** – moduł w `assistant.py` z pipeline np. `OpenAI/CLIP` i przekazywanie opisów do modeli tekstowych.
3. **Integracja Google** – w `config.py` przygotować schemat danych na poświadczenia; w `assistant.py` zaimplementować klasę `GoogleConnector` bazującą na API.
4. **Interakcja z ekranem** – w `demo.py` pokazać podstawowe API oparte o `FastAPI` + `websocket`, które udostępnia obraz pulpitu oraz przyjmuje komendy (kliknięcia, zaznaczenia, wpisywanie tekstu).
5. **Analiza psychologiczna** – wykorzystać klasę `PsychologyAnalyzer`, by połączyć prompt z wnioskami psychologicznymi i zsynchronizować trening modeli.
6. **Ingestia plików** – zaimplementować `FileIngestionManager`, który potrafi dekodować tekst, odczytywać dokumenty i delegować multimedia do wyspecjalizowanych pipeline'ów.
7. **Szczegóły językowe** – w `assistant.py` ustawić polskie predefiniowane prompty i słowniki, ewentualnie translację wejść/wyjść.

## Jak korzystać z rekomendacji narzędzi
- W demo CLI dostępna jest flaga `--list-tooling`, która wypisuje rekomendowane pakiety i kończy działanie programu.
- Rekomendacje pojawiają się również w odpowiedzi asystenta; można je wyłączyć flagą `--disable-tooling-advice` lub modyfikować polecenie instalacji Open WebUI poprzez `--open-webui-command`.

## Nowe możliwości CLI
- **Synteza mowy:** dodano flagi `--speech-voice`, `--speech-rate`, `--speech-format` oraz przełącznik `--speak-response`, który po wygenerowaniu odpowiedzi wypisze instrukcję produkcji audio. Funkcję można wyłączyć flagą `--disable-speech`.
- **Synteza mowy (ormiański):** osobny zestaw przełączników `--armenian-voice`, `--armenian-rate`, `--armenian-format`, `--speak-response-armenian` oraz `--disable-armenian-speech` pozwala przygotować instrukcję audio także w języku ormiańskim.
- **Mostek Windows Voice Control:** `--enable-windows-voice-bridge` aktywuje generowanie instrukcji przekierowujących audio do Voice Access. Parametry makr można dostosować poprzez `--voice-access-profile`, `--voice-access-command-script`, `--disable-voice-access-autostart`, `--voice-access-audio-dir`, a flagi `--bridge-response` oraz `--bridge-response-armenian` wypisują końcowy opis integracji (dla polskiej lub ormiańskiej ścieżki TTS).
- **PowerShell obok Pythona:** oprócz `--python-task` dostępna jest flaga `--powershell-task`, a zachowanie konfiguruje się poprzez `--powershell-profile`, `--powershell-policy` oraz `--disable-powershell-generation`.
- **Interakcje ekranowe:** `--screen-action` wyświetla podpowiedź kursora z wykorzystaniem predefiniowanych komunikatów z konfiguracji `InteractionHints`.
- **Profil użytkownika:** flagi `--user-tone`, `--user-formality`, `--user-interests`, `--user-goals`, `--user-note` oraz `--confirm-profile` pozwalają aktualizować profil preferencji i notatek terapeutycznych; `--describe-profile` wypisuje jego aktualny stan.
- **Pamięć modeli:** `--request-memory-model`, `--request-memory-purpose` oraz `--confirm-memory` umożliwiają przydział zaszyfrowanej pamięci; `--describe-memory` zwraca aktywne sesje.
- **Globalne potwierdzenia:** większość operacji wymaga flag potwierdzających (`--confirm`, `--confirm-python`, `--confirm-powershell`, `--confirm-speech`, `--confirm-bridge`, itd.), a `--show-confirmation-log` pozwala przejrzeć audyt zatwierdzonych działań. Komunikat potwierdzenia można dostosować parametrem `--confirmation-prompt`.
- **Routowanie specjalistów:** `--describe-routing` wypisuje aktywne reguły, a każda odpowiedź jest automatycznie podpisywana nazwą dobranego eksperta. Dodatkowe opcje `--disable-routing`, `--routing-default-specialist` i `--disable-routing-signatures` kontrolują zachowanie systemu.
- **Integracje z innymi AI:** `--describe-external-ai` pokazuje status dozwolonych partnerów, `--connect-partner` (z opcjonalnym `--connect-snapshot`) inicjuje połączenie tylko po potwierdzeniu `--confirm-external-ai`, a token białego szumu można zmienić flagą `--external-white-noise-token`.
- **Magazyn offline:** `--describe-offline-policy` prezentuje zasady przechowywania danych, a `--store-plan-name` (opcjonalnie z `--store-plan-content` i `--confirm-store-plan`) zapisuje wynik pracy w lokalnym repozytorium bez wycieku do chmury.

## Dodatkowe notatki
- Kod w repozytorium stanowi szkic. Wdrożenie produkcyjne będzie wymagało dodania mechanizmów bezpieczeństwa, autoryzacji i monitoringu.
- Wszystkie dane robocze pozostają offline, dlatego przy integracji z chmurą należy jasno zaznaczyć, że synchronizacja jest domyślnie blokowana.
- W razie potrzeby można rozszerzyć repozytorium o folder `assets/` na przykładowe pliki konfiguracyjne i obrazy do testów.

