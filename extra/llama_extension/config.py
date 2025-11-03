"""Konfiguracje wykorzystywane przez moduł LLaMA Qwen 3/8 B.

Moduł jest szkicem – implementacja właściwa powinna docelowo zaciągać
konfigurację z plików YAML/JSON oraz zmiennych środowiskowych. Tutaj
definiujemy podstawowe klasy `dataclass`, które porządkują dane.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import List, Tuple


@dataclass
class ModelConfig:
    """Konfiguracja samego modelu językowego.

    Attributes:
        model_path: Ścieżka do plików modelu (gguf/ggml lub transformers).
        quantization_bits: Liczba bitów (np. 4 lub 8) – ułatwia dopasowanie
            modelu do sprzętu z mniejszą ilością RAM/GPU.
        context_window: Liczba tokenów kontekstu.
        language: Domyślny język interakcji (ustawiony na polski).
    """

    model_path: Path
    quantization_bits: int = 8
    context_window: int = 4096
    language: str = "pl"


@dataclass
class GoogleConfig:
    """Informacje do połączenia z API Google."""

    credentials_file: Path
    scopes: Tuple[str, ...] = ("https://www.googleapis.com/auth/drive",)


@dataclass
class ScreenSharingConfig:
    """Minimalna konfiguracja modułu udostępniania ekranu."""

    host: str = "0.0.0.0"
    port: int = 8765
    frame_rate: int = 12
    capture_region: Tuple[int, int, int, int] | None = None


@dataclass
class SpeechSynthesisConfig:
    """Parametry syntezatora mowy w języku polskim."""

    enable: bool = True
    voice: str = "pl-PL-EwaNeural"
    speaking_rate: float = 1.0
    audio_format: str = "mp3"


@dataclass
class ArmenianSpeechSynthesisConfig:
    """Parametry syntezatora mowy w języku ormiańskim."""

    enable: bool = True
    voice: str = "hy-AM-HaykNeural"
    speaking_rate: float = 1.0
    audio_format: str = "wav"


@dataclass
class WindowsVoiceControlConfig:
    """Mostek łączący syntezę mowy ze sterowaniem głosowym Windows 11."""

    enable_bridge: bool = False
    voice_access_profile: str = "Windows Voice Access"
    auto_start_voice_access: bool = True
    command_script: str = (
        "Start-Process -FilePath \"C:\\Windows\\System32\\voiceaccess.exe\" -WindowStyle Hidden"
    )
    audio_drop_directory: Path | None = None


@dataclass
class InteractionHints:
    """Słownik pomocniczy dla ruchów kursora i interakcji z UI."""

    highlight_color: Tuple[int, int, int] = (255, 0, 0)
    annotation_messages: List[str] = field(
        default_factory=lambda: [
            "Kliknij tutaj", "Zaznacz ten element", "Edytuj kod w tym miejscu"
        ]
    )


@dataclass
class PsychologyConfig:
    """Konfiguracja modułu analizy i treningu psychologicznego."""

    enable_analysis: bool = True
    dataset_paths: List[Path] = field(default_factory=list)
    training_schedule: Tuple[str, ...] = ("codziennie", "co tydzień", "co miesiąc")
    knowledge_cutoff: date = field(default_factory=date.today)
    preferred_framework: str = "pytorch"


@dataclass
class FileIngestionConfig:
    """Konfiguracja odczytu dowolnych formatów plików przekazywanych do asystenta."""

    allow_binary: bool = True
    text_encodings: Tuple[str, ...] = ("utf-8", "cp1250")
    supported_formats: Tuple[str, ...] = (
        ".txt",
        ".md",
        ".rtf",
        ".pdf",
        ".docx",
        ".xlsx",
        ".csv",
        ".json",
        ".xml",
        ".html",
        ".pptx",
        ".png",
        ".jpg",
        ".jpeg",
        ".mp3",
        ".wav",
        ".mp4",
        ".zip",
    )
    chunk_size: int = 2048


@dataclass
class DomainKnowledgeConfig:
    """Konfiguracja źródeł wiedzy tematycznej."""

    ethical_hacking_sources: List[Path] = field(default_factory=list)
    cooking_compendiums: List[Path] = field(default_factory=list)
    book_writing_guides: List[Path] = field(default_factory=list)
    editing_checklists: List[Path] = field(default_factory=list)
    security_hardening_manuals: List[Path] = field(default_factory=list)
    encryption_patterns: List[str] = field(
        default_factory=lambda: [
            "AES-256-GCM",
            "ChaCha20-Poly1305",
            "HybrID: ECDH + XChaCha20",
        ]
    )
    visual_masking_presets: List[str] = field(
        default_factory=lambda: [
            "white-noise-overlay",
            "gaussian-blur-sensitive-areas",
            "pixelate-personally-identifiable-info",
        ]
    )


@dataclass(frozen=True)
class ModelRoutingRule:
    """Reguła przypisująca specjalistę modelowego do kategorii zapytań."""

    name: str
    model_identifier: str
    expertise_tags: Tuple[str, ...]
    trigger_keywords: Tuple[str, ...]
    description: str = ""


@dataclass
class ModelRoutingConfig:
    """Steruje intuicyjnym wyborem eksperta modelowego."""

    enable_routing: bool = True
    rules: Tuple[ModelRoutingRule, ...] = (
        ModelRoutingRule(
            name="Ollama Kodowanie",
            model_identifier="ollama-coding",
            expertise_tags=("python", "powershell", "code", "development"),
            trigger_keywords=("kod", "python", "powershell", "skrypt", "program"),
            description=(
                "Ekspert programistyczny odpowiadający za generowanie i analizę kodu."
            ),
        ),
        ModelRoutingRule(
            name="Ollama Analityka Google",
            model_identifier="ollama-google-analytics",
            expertise_tags=("google", "analytics", "bigquery", "dane"),
            trigger_keywords=("google", "dane", "analiza", "bigquery", "raport"),
            description=(
                "Ekspert analizy danych i integracji z usługami Google dla dużych zbiorów."
            ),
        ),
        ModelRoutingRule(
            name="LLaMA Psychologia",
            model_identifier="llama-psychology",
            expertise_tags=("psychologia", "emocje", "wsparcie"),
            trigger_keywords=("psychologia", "emocjonalnie", "terapia", "wellbeing"),
            description=(
                "Specjalista empatyczny odpowiadający za rozmowy i analizy psychologiczne."
            ),
        ),
    )
    default_specialist: str = "Ollama Ogólny"
    sign_responses: bool = True


@dataclass
class ExternalAIIntegrationConfig:
    """Parametry połączeń z zewnętrznymi systemami AI."""

    enable_integrations: bool = True
    on_demand_only: bool = True
    allowed_partners: Tuple[str, ...] = ("assistant-lab", "assistant-sandbox")
    memory_white_noise_token: str = "[BIAŁY-SZUM]"
    shareable_metadata: Tuple[str, ...] = ("temat", "cel", "status")


@dataclass
class OfflineDataPolicyConfig:
    """Zapewnia, że wszystkie plany i dane pozostają offline."""

    enforce_offline_only: bool = True
    local_storage_directory: Path | None = None
    plan_repository_name: str = "ollama_offline_plans"
    allow_cloud_sync: bool = False
    reminder: str = (
        "Wszystkie dane i plany są przechowywane lokalnie i nie są wysyłane do chmury."
    )


@dataclass
class CorporateKnowledgeConfig:
    """Źródła wiedzy korporacyjnej (Google, Samsung)."""

    google_documents: List[Path] = field(default_factory=list)
    samsung_documents: List[Path] = field(default_factory=list)
    refresh_interval_hours: int = 24


@dataclass
class DevelopmentAssistantConfig:
    """Ustawienia modułu tworzącego kod w czacie (Python)."""

    enable_python_generation: bool = True
    default_environment: str = "python3.11"
    formatting_style: str = "black"
    enable_powershell_generation: bool = True
    powershell_profile: str = "PowerShell 7"
    execution_policy: str = "RemoteSigned"


@dataclass
class DataProtectionConfig:
    """Parametry maskowania danych wrażliwych i generowania białego szumu."""

    enable_masking: bool = True
    noise_level_db: float = -25.0
    redaction_keywords: Tuple[str, ...] = (
        "hasło",
        "password",
        "token",
        "sekret",
        "secret",
    )


@dataclass
class ToolingRecommendationConfig:
    """Sugerowane pakiety i rozszerzenia wspierające Ollamę."""

    include_recommendations: bool = True
    developer_tools: Tuple[str, ...] = (
        "litellm",
        "ollama-python",
        "langchain",
        "llama-index",
    )
    user_interfaces: Tuple[str, ...] = (
        "Open WebUI",
        "Ollama Desktop",
        "chatbox",
    )
    integrations: Tuple[str, ...] = (
        "ollama-js",
        "ollama-ruby",
        "ollama-go",
    )
    monitoring: Tuple[str, ...] = (
        "prometheus-ollama-exporter",
        "grafana dashboards",
    )
    extra_features: Tuple[str, ...] = (
        "text-generation-webui",
        "ollama-supervisor",
        "model-converters",
    )
    containerized: Tuple[str, ...] = (
        "Ollama Docker",
        "ollama-kubernetes",
    )
    open_webui_install: str = (
        "docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway "
        "-v open-webui:/app/backend/data --name open-webui --restart always "
        "ghcr.io/open-webui/open-webui:main"
    )


@dataclass
class MemoryAccessConfig:
    """Umożliwia przydzielenie pamięci długoterminowej dla modeli."""

    enable_memory: bool = True
    available_models: Tuple[str, ...] = ("ollama", "llama")
    require_explicit_user_request: bool = True
    retention_policy_days: int = 30
    storage_backend: str = "local-encrypted"
    storage_path: Path | None = None


@dataclass
class UserProfileConfig:
    """Definiuje parametry profilu użytkownika (psychologicznego i preferencyjnego)."""

    enable_psychological_profile: bool = True
    enable_preference_profile: bool = True
    default_tone: str = "empatyczny"
    default_formality: str = "średnia"
    preference_fields: Tuple[str, ...] = ("tone", "formality", "interests", "goals")
    auto_update_on_interaction: bool = True


@dataclass
class ConfirmationWorkflowConfig:
    """Opisuje wymagania dotyczące potwierdzeń użytkownika dla każdej akcji."""

    require_confirmation: bool = True
    confirmation_prompt_template: str = (
        "Potwierdź proszę działanie: '{action}'. Odpowiedz jednym z zaakceptowanych "
        "słów, aby kontynuować."
    )
    accepted_responses: Tuple[str, ...] = ("tak", "zgadzam się", "yes")
    denied_responses: Tuple[str, ...] = ("nie", "no", "odrzuć")
    audit_log_enabled: bool = True


@dataclass
class AssistantConfig:
    """Łączy wszystkie pod-konfiguracje."""

    model: ModelConfig
    google: GoogleConfig | None = None
    screen: ScreenSharingConfig = ScreenSharingConfig()
    interaction: InteractionHints = InteractionHints()
    psychology: PsychologyConfig = PsychologyConfig()
    file_ingestion: FileIngestionConfig = FileIngestionConfig()
    domain_knowledge: DomainKnowledgeConfig = DomainKnowledgeConfig()
    corporate_knowledge: CorporateKnowledgeConfig = CorporateKnowledgeConfig()
    development: DevelopmentAssistantConfig = DevelopmentAssistantConfig()
    data_protection: DataProtectionConfig = DataProtectionConfig()
    tooling: ToolingRecommendationConfig = ToolingRecommendationConfig()
    speech: SpeechSynthesisConfig = SpeechSynthesisConfig()
    armenian_speech: ArmenianSpeechSynthesisConfig = ArmenianSpeechSynthesisConfig()
    windows_voice_control: WindowsVoiceControlConfig = WindowsVoiceControlConfig()
    memory: MemoryAccessConfig = MemoryAccessConfig()
    user_profile: UserProfileConfig = UserProfileConfig()
    confirmation: ConfirmationWorkflowConfig = ConfirmationWorkflowConfig()
    routing: ModelRoutingConfig = ModelRoutingConfig()
    external_ai: ExternalAIIntegrationConfig = ExternalAIIntegrationConfig()
    offline_policy: OfflineDataPolicyConfig = OfflineDataPolicyConfig()

