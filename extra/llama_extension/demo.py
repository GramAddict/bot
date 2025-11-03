"""Przykładowa aplikacja CLI/HTTP dla LlamaMultimodalAssistant.

Skrypt pokazuje, jak można podłączyć wszystkie elementy w jedną prostą
aplikację serwerową. W realnym wdrożeniu warto dodać obsługę błędów,
autoryzację i testy jednostkowe.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .assistant import (
    AssistantConfig,
    FilePayload,
    GoogleConfig,
    ImagePayload,
    LlamaMultimodalAssistant,
    ModelConfig,
    ScreenSharingConfig,
)
from .config import (
    ArmenianSpeechSynthesisConfig,
    ConfirmationWorkflowConfig,
    CorporateKnowledgeConfig,
    DataProtectionConfig,
    DevelopmentAssistantConfig,
    DomainKnowledgeConfig,
    ExternalAIIntegrationConfig,
    FileIngestionConfig,
    InteractionHints,
    MemoryAccessConfig,
    ModelRoutingConfig,
    PsychologyConfig,
    OfflineDataPolicyConfig,
    SpeechSynthesisConfig,
    ToolingRecommendationConfig,
    UserProfileConfig,
    WindowsVoiceControlConfig,
)


def _load_image(path: Path) -> ImagePayload:
    data = path.read_bytes()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return ImagePayload(bytes_data=data, mime_type=mime)


def build_assistant(args: argparse.Namespace) -> LlamaMultimodalAssistant:
    model_cfg = ModelConfig(
        model_path=Path(args.model_path),
        quantization_bits=args.quantization_bits,
        context_window=args.context_window,
        language="pl",
    )

    google_cfg: Optional[GoogleConfig] = None
    if args.google_credentials:
        google_cfg = GoogleConfig(Path(args.google_credentials))

    screen_cfg = ScreenSharingConfig(port=args.screen_port)
    interaction = InteractionHints()
    psychology_cfg = PsychologyConfig(
        enable_analysis=not args.disable_psychology,
        dataset_paths=[Path(p) for p in args.psychology_dataset],
    )
    file_ingestion_cfg = FileIngestionConfig()
    domain_cfg = DomainKnowledgeConfig(
        ethical_hacking_sources=[Path(p) for p in args.ethical_hacking],
        cooking_compendiums=[Path(p) for p in args.cooking],
        book_writing_guides=[Path(p) for p in args.book_writing],
        editing_checklists=[Path(p) for p in args.editing],
        security_hardening_manuals=[Path(p) for p in args.security],
    )
    corporate_cfg = CorporateKnowledgeConfig(
        google_documents=[Path(p) for p in args.google_db],
        samsung_documents=[Path(p) for p in args.samsung_db],
        refresh_interval_hours=args.refresh_hours,
    )
    development_cfg = DevelopmentAssistantConfig(
        enable_python_generation=not args.disable_python_generation,
        default_environment=args.python_environment,
        formatting_style=args.python_format,
        enable_powershell_generation=not args.disable_powershell_generation,
        powershell_profile=args.powershell_profile,
        execution_policy=args.powershell_policy,
    )
    data_protection_cfg = DataProtectionConfig(
        enable_masking=not args.disable_masking,
        noise_level_db=args.noise_level_db,
    )
    routing_cfg = ModelRoutingConfig(
        enable_routing=not args.disable_routing,
        default_specialist=args.routing_default_specialist,
        sign_responses=not args.disable_routing_signatures,
    )
    allowed_partners = (
        tuple(args.external_partner)
        if args.external_partner
        else ("assistant-lab", "assistant-sandbox")
    )
    external_ai_cfg = ExternalAIIntegrationConfig(
        enable_integrations=not args.disable_external_ai,
        on_demand_only=not args.external_ai_continuous,
        allowed_partners=allowed_partners,
        memory_white_noise_token=args.external_white_noise_token,
    )
    offline_policy_cfg = OfflineDataPolicyConfig(
        enforce_offline_only=not args.disable_offline_enforcement,
        local_storage_directory=Path(args.offline_directory)
        if args.offline_directory
        else None,
        allow_cloud_sync=args.allow_offline_cloud_sync,
    )
    tooling_cfg = ToolingRecommendationConfig(
        include_recommendations=not args.disable_tooling_advice,
        open_webui_install=args.open_webui_command,
    )
    speech_cfg = SpeechSynthesisConfig(
        enable=not args.disable_speech,
        voice=args.speech_voice,
        speaking_rate=args.speech_rate,
        audio_format=args.speech_format,
    )
    armenian_speech_cfg = ArmenianSpeechSynthesisConfig(
        enable=not args.disable_armenian_speech,
        voice=args.armenian_voice,
        speaking_rate=args.armenian_rate,
        audio_format=args.armenian_format,
    )
    windows_voice_cfg = WindowsVoiceControlConfig(
        enable_bridge=args.enable_windows_voice_bridge,
        voice_access_profile=args.voice_access_profile,
        auto_start_voice_access=not args.disable_voice_access_autostart,
        command_script=(
            args.voice_access_command_script
            or "Start-Process -FilePath \"C:\\Windows\\System32\\voiceaccess.exe\" -WindowStyle Hidden"
        ),
        audio_drop_directory=(
            Path(args.voice_access_audio_dir)
            if args.voice_access_audio_dir
            else None
        ),
    )
    memory_cfg = MemoryAccessConfig(
        enable_memory=not args.disable_memory,
        available_models=tuple(args.memory_model) if args.memory_model else ("ollama", "llama"),
        retention_policy_days=args.memory_retention_days,
        storage_backend=args.memory_backend,
        storage_path=Path(args.memory_storage_path) if args.memory_storage_path else None,
        require_explicit_user_request=not args.allow_memory_without_request,
    )
    user_profile_cfg = UserProfileConfig(
        enable_psychological_profile=not args.disable_psych_profile,
        enable_preference_profile=not args.disable_preference_profile,
        default_tone=args.default_user_tone,
        default_formality=args.default_user_formality,
        auto_update_on_interaction=not args.disable_auto_profile_update,
    )
    confirmation_cfg = ConfirmationWorkflowConfig(
        require_confirmation=not args.allow_unconfirmed_actions,
        confirmation_prompt_template=args.confirmation_prompt,
    )

    assistant_cfg = AssistantConfig(
        model=model_cfg,
        google=google_cfg,
        screen=screen_cfg,
        interaction=interaction,
        psychology=psychology_cfg,
        file_ingestion=file_ingestion_cfg,
        domain_knowledge=domain_cfg,
        corporate_knowledge=corporate_cfg,
        development=development_cfg,
        data_protection=data_protection_cfg,
        routing=routing_cfg,
        external_ai=external_ai_cfg,
        offline_policy=offline_policy_cfg,
        tooling=tooling_cfg,
        speech=speech_cfg,
        armenian_speech=armenian_speech_cfg,
        windows_voice_control=windows_voice_cfg,
        memory=memory_cfg,
        user_profile=user_profile_cfg,
        confirmation=confirmation_cfg,
    )
    assistant = LlamaMultimodalAssistant(assistant_cfg)
    assistant.load_model()
    return assistant


def cli() -> None:
    parser = argparse.ArgumentParser(description="Demo LLaMA Qwen 3/8 B")
    parser.add_argument("prompt", help="Polecenie dla asystenta")
    parser.add_argument("--image", help="Ścieżka do obrazu dołączonego do zapytania")
    parser.add_argument("--model-path", required=True, help="Katalog z plikami modelu")
    parser.add_argument("--quantization-bits", type=int, default=8)
    parser.add_argument("--context-window", type=int, default=4096)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Potwierdza wykonanie głównej odpowiedzi oraz operacji wymagających zgody",
    )
    parser.add_argument(
        "--confirmation-prompt",
        default=(
            "Potwierdź proszę działanie: '{action}'. Odpowiedz jednym z zaakceptowanych słów, aby kontynuować."
        ),
        help="Szablon komunikatu proszącego o potwierdzenie",
    )
    parser.add_argument(
        "--allow-unconfirmed-actions",
        action="store_true",
        help="Wyłącza globalny wymóg potwierdzania każdej akcji (niezalecane)",
    )
    parser.add_argument(
        "--disable-routing",
        action="store_true",
        help="Wyłącza intuicyjny wybór specjalistów modelowych",
    )
    parser.add_argument(
        "--routing-default-specialist",
        default="Ollama Ogólny",
        help="Nazwa domyślnego specjalisty odpowiadającego na pytania",
    )
    parser.add_argument(
        "--disable-routing-signatures",
        action="store_true",
        help="Wyłącza podpisywanie odpowiedzi nazwą specjalisty",
    )
    parser.add_argument(
        "--describe-routing",
        action="store_true",
        help="Wypisuje reguły routowania modeli",
    )
    parser.add_argument("--screen-port", type=int, default=8765)
    parser.add_argument("--google-credentials")
    parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Ścieżka do pliku dołączonego do kontekstu (można podać wiele razy)",
    )
    parser.add_argument(
        "--psychology-dataset",
        action="append",
        default=[],
        help="Ścieżki do korpusów treningowych modułu psychologicznego",
    )
    parser.add_argument(
        "--disable-psychology",
        action="store_true",
        help="Wyłącza analizę i trening psychologiczny",
    )
    parser.add_argument(
        "--disable-psych-profile",
        action="store_true",
        help="Wyłącza budowanie profilu psychologicznego użytkownika",
    )
    parser.add_argument(
        "--disable-preference-profile",
        action="store_true",
        help="Wyłącza profil preferencyjny użytkownika",
    )
    parser.add_argument(
        "--default-user-tone",
        default="empatyczny",
        help="Domyślny ton wypowiedzi w profilu użytkownika",
    )
    parser.add_argument(
        "--default-user-formality",
        default="średnia",
        help="Domyślny poziom formalności profilu użytkownika",
    )
    parser.add_argument(
        "--disable-auto-profile-update",
        action="store_true",
        help="Wyłącza automatyczne aktualizacje profilu na podstawie interakcji",
    )
    parser.add_argument(
        "--train-psychology",
        action="store_true",
        help="Uruchamia trening modułu psychologicznego przed wygenerowaniem odpowiedzi",
    )
    parser.add_argument(
        "--confirm-train-psychology",
        action="store_true",
        help="Potwierdza wykonanie treningu modułu psychologicznego",
    )
    parser.add_argument(
        "--ethical-hacking",
        action="append",
        default=[],
        help="Ścieżki z bazą etycznego hakowania",
    )
    parser.add_argument(
        "--cooking",
        action="append",
        default=[],
        help="Ścieżki z przepisami kulinarnymi",
    )
    parser.add_argument(
        "--book-writing",
        action="append",
        default=[],
        help="Materiały o pisaniu książek",
    )
    parser.add_argument(
        "--editing",
        action="append",
        default=[],
        help="Checklisty redakcyjne",
    )
    parser.add_argument(
        "--security",
        action="append",
        default=[],
        help="Manuale zabezpieczeń i hardeningu",
    )
    parser.add_argument(
        "--google-db",
        action="append",
        default=[],
        help="Dokumenty referencyjne Google",
    )
    parser.add_argument(
        "--samsung-db",
        action="append",
        default=[],
        help="Dokumenty referencyjne Samsung",
    )
    parser.add_argument(
        "--refresh-hours",
        type=int,
        default=24,
        help="Co ile godzin odświeżać bazy Google/Samsung",
    )
    parser.add_argument(
        "--disable-python-generation",
        action="store_true",
        help="Wyłącza generowanie kodu Python",
    )
    parser.add_argument(
        "--python-environment",
        default="python3.11",
        help="Opis docelowego środowiska dla kodu Python",
    )
    parser.add_argument(
        "--python-format",
        default="black",
        help="Konwencja formatowania kodu Python",
    )
    parser.add_argument(
        "--python-task",
        help="Jeżeli ustawione – wygeneruj dodatkowo szkic kodu Python",
    )
    parser.add_argument(
        "--confirm-python",
        action="store_true",
        help="Potwierdza wygenerowanie szkicu kodu Python",
    )
    parser.add_argument(
        "--disable-powershell-generation",
        action="store_true",
        help="Wyłącza generowanie komend PowerShell",
    )
    parser.add_argument(
        "--powershell-profile",
        default="PowerShell 7",
        help="Profil środowiska PowerShell używany w szkicach",
    )
    parser.add_argument(
        "--powershell-policy",
        default="RemoteSigned",
        help="ExecutionPolicy dołączane do szkiców PowerShell",
    )
    parser.add_argument(
        "--powershell-task",
        help="Jeżeli ustawione – wygeneruj szkic komend PowerShell",
    )
    parser.add_argument(
        "--confirm-powershell",
        action="store_true",
        help="Potwierdza przygotowanie szkicu komend PowerShell",
    )
    parser.add_argument(
        "--disable-masking",
        action="store_true",
        help="Wyłącza warstwę maskowania danych i biały szum",
    )
    parser.add_argument(
        "--noise-level-db",
        type=float,
        default=-25.0,
        help="Poziom białego szumu dodawanego do odpowiedzi",
    )
    parser.add_argument(
        "--disable-external-ai",
        action="store_true",
        help="Wyłącza integracje z zewnętrznymi systemami AI",
    )
    parser.add_argument(
        "--external-ai-continuous",
        action="store_true",
        help="Pozwala na ciągłe połączenie zewnętrznych AI (domyślnie tylko na żądanie)",
    )
    parser.add_argument(
        "--external-partner",
        action="append",
        default=[],
        help="Identyfikator zewnętrznego AI dopuszczonego do połączeń (można podać wiele razy)",
    )
    parser.add_argument(
        "--external-white-noise-token",
        default="[BIAŁY-SZUM]",
        help="Token wykorzystywany jako biały szum w pamięci partnerów AI",
    )
    parser.add_argument(
        "--describe-external-ai",
        action="store_true",
        help="Wypisuje status integracji zewnętrznych AI",
    )
    parser.add_argument(
        "--disable-memory",
        action="store_true",
        help="Wyłącza przydzielanie pamięci dla modeli",
    )
    parser.add_argument(
        "--memory-model",
        action="append",
        default=[],
        help="Nazwa modelu, który może korzystać z pamięci (można podać wiele razy)",
    )
    parser.add_argument(
        "--memory-retention-days",
        type=int,
        default=30,
        help="Liczba dni przechowywania danych pamięci",
    )
    parser.add_argument(
        "--memory-backend",
        default="local-encrypted",
        help="Backend pamięci modeli",
    )
    parser.add_argument(
        "--memory-storage-path",
        help="Ścieżka do katalogu przechowującego dane pamięci modeli",
    )
    parser.add_argument(
        "--allow-memory-without-request",
        action="store_true",
        help="Nie wymaga dodatkowego potwierdzenia przydziału pamięci",
    )
    parser.add_argument(
        "--disable-tooling-advice",
        action="store_true",
        help="Ukrywa rekomendacje narzędzi Ollamy w odpowiedziach",
    )
    parser.add_argument(
        "--open-webui-command",
        default=(
            "docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway "
            "-v open-webui:/app/backend/data --name open-webui --restart always "
            "ghcr.io/open-webui/open-webui:main"
        ),
        help="Polecenie instalacji Open WebUI umieszczane w rekomendacjach",
    )
    parser.add_argument(
        "--list-tooling",
        action="store_true",
        help="Wypisuje rekomendowane pakiety i rozszerzenia oraz kończy działanie",
    )
    parser.add_argument(
        "--disable-speech",
        action="store_true",
        help="Wyłącza generowanie instrukcji syntezy mowy",
    )
    parser.add_argument(
        "--speech-voice",
        default="pl-PL-EwaNeural",
        help="Identyfikator głosu polskiej syntezy mowy",
    )
    parser.add_argument(
        "--speech-rate",
        type=float,
        default=1.0,
        help="Tempo wypowiedzi syntezatora mowy",
    )
    parser.add_argument(
        "--speech-format",
        default="mp3",
        help="Format pliku audio generowanego przez syntezator",
    )
    parser.add_argument(
        "--speak-response",
        action="store_true",
        help="Po wygenerowaniu odpowiedzi przygotuj również instrukcję syntezy mowy",
    )
    parser.add_argument(
        "--confirm-speech",
        action="store_true",
        help="Potwierdza wykonanie instrukcji syntezy mowy po polsku",
    )
    parser.add_argument(
        "--disable-armenian-speech",
        action="store_true",
        help="Wyłącza generowanie instrukcji syntezy mowy po ormiańsku",
    )
    parser.add_argument(
        "--armenian-voice",
        default="hy-AM-HaykNeural",
        help="Identyfikator głosu ormiańskiej syntezy mowy",
    )
    parser.add_argument(
        "--armenian-rate",
        type=float,
        default=1.0,
        help="Tempo wypowiedzi syntezatora mowy po ormiańsku",
    )
    parser.add_argument(
        "--armenian-format",
        default="wav",
        help="Format pliku audio generowanego przez syntezator ormiański",
    )
    parser.add_argument(
        "--speak-response-armenian",
        action="store_true",
        help="Po wygenerowaniu odpowiedzi przygotuj instrukcję syntezy mowy po ormiańsku",
    )
    parser.add_argument(
        "--confirm-armenian-speech",
        action="store_true",
        help="Potwierdza wykonanie instrukcji syntezy mowy po ormiańsku",
    )
    parser.add_argument(
        "--enable-windows-voice-bridge",
        action="store_true",
        help="Włącza mostek do sterowania głosowego Windows 11 (Voice Control)",
    )
    parser.add_argument(
        "--voice-access-profile",
        default="Windows Voice Access",
        help="Nazwa profilu sterowania głosowego Windows 11 obsługującego komendy",
    )
    parser.add_argument(
        "--voice-access-command-script",
        help="Polecenie PowerShell uruchamiające moduł Voice Access",
    )
    parser.add_argument(
        "--disable-voice-access-autostart",
        action="store_true",
        help="Wyłącza automatyczne uruchamianie Voice Access",
    )
    parser.add_argument(
        "--voice-access-audio-dir",
        help="Katalog, do którego zapisywane są pliki audio dla Voice Access",
    )
    parser.add_argument(
        "--bridge-response",
        action="store_true",
        help="Po wygenerowaniu odpowiedzi przygotuj instrukcje dla Windows Voice Control",
    )
    parser.add_argument(
        "--confirm-bridge",
        action="store_true",
        help="Potwierdza przekazanie odpowiedzi do Windows Voice Control",
    )
    parser.add_argument(
        "--bridge-response-armenian",
        action="store_true",
        help="Przekieruj odpowiedź ormiańską do Windows Voice Control",
    )
    parser.add_argument(
        "--confirm-armenian-bridge",
        action="store_true",
        help="Potwierdza przekazanie ormiańskiej odpowiedzi do Windows Voice Control",
    )
    parser.add_argument(
        "--screen-action",
        type=int,
        help="Numer instrukcji interakcji ekranowej do wypisania",
    )
    parser.add_argument("--user-tone", help="Aktualizuje ton wypowiedzi w profilu użytkownika")
    parser.add_argument(
        "--user-formality",
        help="Aktualizuje oczekiwany poziom formalności w profilu użytkownika",
    )
    parser.add_argument(
        "--user-interests",
        help="Aktualizuje kluczowe zainteresowania w profilu użytkownika",
    )
    parser.add_argument(
        "--user-goals",
        help="Aktualizuje cele użytkownika w profilu preferencji",
    )
    parser.add_argument(
        "--user-note",
        help="Dodaje notatkę psychologiczną do profilu użytkownika",
    )
    parser.add_argument(
        "--confirm-profile",
        action="store_true",
        help="Potwierdza aktualizację profilu użytkownika",
    )
    parser.add_argument(
        "--describe-profile",
        action="store_true",
        help="Wypisuje bieżący profil użytkownika",
    )
    parser.add_argument(
        "--request-memory-model",
        help="Model, dla którego należy przydzielić pamięć (ollama/llama lub inny)",
    )
    parser.add_argument(
        "--request-memory-purpose",
        help="Cel wykorzystania pamięci przy składaniu wniosku",
    )
    parser.add_argument(
        "--confirm-memory",
        action="store_true",
        help="Potwierdza przydzielenie pamięci dla modelu",
    )
    parser.add_argument(
        "--describe-memory",
        action="store_true",
        help="Wypisuje aktualne sesje pamięci modeli",
    )
    parser.add_argument(
        "--show-confirmation-log",
        action="store_true",
        help="Prezentuje historię potwierdzonych działań",
    )
    parser.add_argument(
        "--disable-offline-enforcement",
        action="store_true",
        help="Wyłącza wymóg przechowywania danych wyłącznie offline",
    )
    parser.add_argument(
        "--allow-offline-cloud-sync",
        action="store_true",
        help="Zezwala na synchronizację z chmurą mimo trybu offline",
    )
    parser.add_argument(
        "--offline-directory",
        help="Ścieżka katalogu, w którym przechowywane są plany offline",
    )
    parser.add_argument(
        "--describe-offline-policy",
        action="store_true",
        help="Prezentuje zasady trybu offline",
    )
    parser.add_argument(
        "--connect-partner",
        help="Nawiązuje połączenie z wybranym partnerem AI",
    )
    parser.add_argument(
        "--connect-snapshot",
        help="Ręcznie podany kontekst rozmowy dla partnera AI",
    )
    parser.add_argument(
        "--confirm-external-ai",
        action="store_true",
        help="Potwierdza nawiązanie połączenia zewnętrznego AI",
    )
    parser.add_argument(
        "--store-plan-name",
        help="Nazwa planu do zapisania w magazynie offline",
    )
    parser.add_argument(
        "--store-plan-content",
        help="Treść planu do zapisania offline (domyślnie ostatnia odpowiedź)",
    )
    parser.add_argument(
        "--confirm-store-plan",
        action="store_true",
        help="Potwierdza zapis planu w magazynie offline",
    )

    args = parser.parse_args()
    assistant = build_assistant(args)

    if args.list_tooling:
        print(assistant.list_tooling_recommendations())
        return

    if args.describe_routing:
        print("\n[Routing modeli]\n")
        print(assistant.describe_model_routing())

    if args.describe_external_ai:
        print("\n[Integracje zewnętrzne AI]\n")
        print(assistant.describe_external_integrations())

    if args.describe_offline_policy:
        print("\n[Tryb offline]\n")
        print(assistant.describe_offline_policy())

    if any(
        [
            args.user_tone,
            args.user_formality,
            args.user_interests,
            args.user_goals,
            args.user_note,
        ]
    ):
        profile_update = assistant.update_user_profile(
            tone=args.user_tone,
            formality=args.user_formality,
            interests=args.user_interests,
            goals=args.user_goals,
            psychological_note=args.user_note,
            user_confirmation=args.confirm_profile,
        )
        print("\n[Profil użytkownika – aktualizacja]\n")
        print(profile_update)

    if args.describe_profile:
        print("\n[Profil użytkownika – podsumowanie]\n")
        print(assistant.describe_user_profile())

    if args.request_memory_model:
        memory_purpose = args.request_memory_purpose or "Brak określonego celu"
        print("\n[Pamięć modeli – wniosek]\n")
        print(
            assistant.request_memory_session(
                args.request_memory_model,
                memory_purpose,
                user_confirmation=args.confirm_memory,
            )
        )

    if args.describe_memory:
        print("\n[Pamięć modeli – aktywne sesje]\n")
        print(assistant.describe_memory_sessions())

    image_payload = _load_image(Path(args.image)) if args.image else None
    file_payloads = [
        FilePayload(name=Path(path).name, bytes_data=Path(path).read_bytes())
        for path in args.file
    ]

    if args.train_psychology:
        print(
            assistant.train_psychology_module(
                user_confirmation=args.confirm_train_psychology
            )
        )

    response = assistant.interact(
        args.prompt,
        image_payload,
        file_payloads,
        user_confirmation=args.confirm,
    )
    print(response)

    if args.python_task:
        print("\n[Szkic kodu Python]\n")
        print(
            assistant.generate_python_code(
                args.python_task, user_confirmation=args.confirm_python
            )
        )
    if args.powershell_task:
        print("\n[Szkic komend PowerShell]\n")
        print(
            assistant.generate_powershell_commands(
                args.powershell_task, user_confirmation=args.confirm_powershell
            )
        )
    if args.screen_action is not None:
        print("\n[Instrukcja interakcji z ekranem]\n")
        print(assistant.guide_screen_interaction(args.screen_action))
    if args.speak_response:
        print("\n[Syntezator mowy]\n")
        print(
            assistant.synthesize_response(
                response, user_confirmation=args.confirm_speech
            )
        )
    if args.speak_response_armenian:
        print("\n[Syntezator mowy – ormiański]\n")
        print(
            assistant.synthesize_armenian_response(
                response, user_confirmation=args.confirm_armenian_speech
            )
        )
    if args.bridge_response:
        print("\n[Windows Voice Control – mostek]\n")
        print(
            assistant.bridge_speech_to_windows_voice_control(
                response, user_confirmation=args.confirm_bridge
            )
        )
    if args.bridge_response_armenian:
        print("\n[Windows Voice Control – mostek (ormiański)]\n")
        print(
            assistant.bridge_armenian_speech_to_windows_voice_control(
                response, user_confirmation=args.confirm_armenian_bridge
            )
        )

    if args.store_plan_name:
        plan_content = args.store_plan_content or response
        print("\n[Zapis planu offline]\n")
        print(
            assistant.store_plan_offline(
                args.store_plan_name,
                plan_content,
                user_confirmation=args.confirm_store_plan,
            )
        )

    if args.connect_partner:
        print("\n[Integracja zewnętrzna AI – połączenie]\n")
        print(
            assistant.connect_external_ai(
                args.connect_partner,
                conversation_snapshot=args.connect_snapshot,
                user_confirmation=args.confirm_external_ai,
            )
        )

    if args.show_confirmation_log:
        print("\n[Historia potwierdzeń]\n")
        print(assistant.confirmation_audit_report())


async def async_share_screen(
    assistant: LlamaMultimodalAssistant, *, user_confirmation: bool = False
) -> str:
    """Asynchroniczny wrapper na potrzeby testów modułu udostępniania ekranu."""

    return await assistant.share_screen(user_confirmation=user_confirmation)


if __name__ == "__main__":
    cli()
