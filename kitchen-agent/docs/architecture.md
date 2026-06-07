classDiagram
class ChatTurnRequest {
<<dataclass>> + str session_id + str user_message + str | None system_prompt + list[dict] images + list[str] context_files + str mode + list[str] note_ids + list[str] file_ids + bool use_tools + str | None provider + str | None model
}
class ChatTurnResponse {
<<dataclass>> + str session_id + str assistant_message + list[dict] ui_history + str user_turn_id + str assistant_turn_id + list[str] tool_calls_made + list[dict] tool_logs + dict tokens_used + str provider_name + str model_name
}
class ChatService {
+handle_turn(ChatTurnRequest request) ChatTurnResponse
+stream_turn(ChatTurnRequest request) Iterator[dict]
}
class Settings { + model_config + str app_title + str app_description + bool debug + Path data_dir + Path prompts_dir + str gemini_model + float gemini_temperature + str | None anthropic_api_key + str anthropic_model + float anthropic_temperature + int anthropic_max_tokens + str | None mimo_api_key + str mimo_base_url + str mimo_model + float mimo_temperature + int mimo_max_tokens + str llm_provider + list[str] allowed_origins
+db_path() Path
+prompt_log_path() Path
+parse_origins(object v) list[str]
}
class ExportService {
+export_markdown(str session_id) str
+export_llm_json(str session_id, list[dict[str, Any]] | None tool_schemas) dict[str, Any]
}
class TestDelayMiddleware {
+dispatch(Request request, call_next)
}
class EditError {
}
class MessageEditService {
+edit_message(str session_id, str turn_id, str new_content) None
+delete_message(str session_id, str turn_id, bool delete_pair) None
+truncate_turns(str session_id, int n) None
+get_system_prompt(str session_id) str | None
+update_system_prompt(str session_id, str system_prompt) None
}
class ToolCallDict { + str id + str name + dict[str, Any] arguments
}
class MessageDict { + str role + str | list[dict[str, Any]] content + list[ToolCallDict] tool_calls + str tool_call_id + str turn_id
}
class PromptMode { + str id + str label + str eyebrow + str content + bool tools_enabled_default
}
class PromptManager {
+reload_prompts() None
+get_all_modes() list[dict]
+get_mode(str mode_id) PromptMode | None
+get_system_instruction(str mode_id) str
}
class TokenCounterProtocol {
+count(str text) int
+count_message(dict message) int
+trim_to(str text, int max_tokens) str
}
class PromptManagerProtocol {
+get_system_instruction(str mode) str
}
class NoteManagerProtocol {
+get_for_context(str session_id, int max_tokens) str
}
class FileManagerProtocol {
+get_for_context(list[str] file_paths, int max_tokens) str
}
class SearchCoordinatorProtocol {
+search(str query, int limit, list[str] | None backends) list[Any]
}
class ToolRegistryProtocol {
+get_handler(str name) Any
}
class ChatImagePart { + str mime_type + str data
}
class ChatRequest { + str session_id + str message + str mode_id + str | None system_prompt + list[ChatImagePart] | None images + list[str] | None context_files + str | None provider + str | None model + bool tools_enabled
}
class ToolLog { + str name + dict[str, Any] args + dict[str, Any] result
}
class ChatResponse { + str text + list[ToolLog] tools_used + str | None user_turn_id + str | None assistant_turn_id + str | None provider + str | None model
}
class ForkRequest { + int turn_index
}
class ForkResponse { + str new_session_id
}
class SessionSummary { + str id + str | None title + str | None updated_at + str | None parent_id + int | None fork_turn_index + str | None root_id + str | None archived_at
}
class SessionNode { + str id + str | None title + str | None updated_at + str | None parent_id + int | None fork_turn_index + str | None root_id + str | None archived_at + list['SessionNode'] children
}
class FileReadResponse { + str filepath + str content
}
class FileWriteRequest { + str content
}
class FileAppendRequest { + str filepath + str content
}
class FileListItem { + str path + str name
}
class RevertResponse { + bool success + str message
}
class NoteCreateRequest { + str selected_text + str source_role + str note
}
class NoteResponse { + str id + str session_id + str selected_text + str note + str source_role + str created_at
}
class LlmExportMetadata { + str session_id + str title + int turn_count + str export_timestamp
}
class LlmExportConfig { + str model + float temperature + str | None system_instruction + list[dict[str, Any]] tools
}
class LlmExportTurn { + str role + list[dict[str, Any]] parts
}
class LlmExportResponse { + LlmExportMetadata metadata + LlmExportConfig config + list[LlmExportTurn] turns
}
class PromptModeResponse { + str id + str label + str eyebrow
}
class PromptModeDetail { + str id + str label + str eyebrow + str content
}
class MessageEditRequest { + str new_content
}
class MessageEditResponse { + bool updated + str turn_id
}
class MessageDeleteResponse { + bool deleted + str turn_id + bool delete_pair
}
class TruncateRequest { + int n
}
class TruncateResponse { + bool truncated + int turns_removed
}
class SystemPromptUpdateRequest { + str system_prompt
}
class SystemPromptResponse { + str session_id + str | None system_prompt
}
class SystemPromptUpdateResponse { + bool updated
}
class TokenEstimateRequest { + str user_message + list[ChatImagePart] | None images + list[str] | None context_files + str | None system_prompt + int history_token_count
}
class SessionTokensResponse { + str session_id + int text_tokens + int image_tokens + int context_file_tokens + int system_prompt_tokens + int history_tokens + int total_tokens + bool fallback_used
}
class TokenEstimateResponse { + int text_tokens + int image_tokens + int context_file_tokens + int system_prompt_tokens + int history_tokens + int total_tokens + bool fallback_used
}
class ModelInfo { + str id + str label + int context_k
}
class ProviderInfo { + str id + str label + str default_model + list[ModelInfo] models
}
class ActiveProvider { + str provider + str model
}
class AppInfo { + str title + str description
}
class TokenEstimate { + int text_tokens + int image_tokens + int context_file_tokens + int system_prompt_tokens + int history_tokens + int total_tokens + bool fallback_used
}
class TokenCounter {
+count(str text) int
+count_message(dict message) int
+trim_to(str text, int max_tokens) str
}
class ContextSlot { + SYSTEM_PROMPT + CONVERSATION_HISTORY + ATTACHED_NOTES + ATTACHED_FILES + SEARCH_RESULTS + TOOL_RESULTS
}
class ContextBudget {
<<dataclass>> + int total + dict[ContextSlot, float] allocations
+tokens_for(ContextSlot slot) int
}
class AssembledContext {
<<dataclass>> + str system_prompt + list[dict] messages + int total_tokens_estimated + dict[ContextSlot, int] slots_used + list[dict] images + list[str] context_files + list[dict] tool_schemas
}
class ContextAssembler {
+assemble(dict session, str mode, str user_message, list[str] | None note_ids, list[str] | None file_ids) AssembledContext
}
class ToolCall {
<<dataclass>> + str id + str name + dict arguments
}
class ToolResult {
<<dataclass>> + str tool_call_id + str name + str content + bool is_error
}
class ToolExecutor {
+execute_all(list[ToolCall] tool_calls) list[ToolResult]
}
class TurnInput {
<<dataclass>> + str user_message + str mode + str | None system_prompt + list[str] note_ids + list[str] file_ids + list[dict] images + list[str] context_files + bool use_tools + str | None provider + str | None model
}
class ToolCallDetail {
<<dataclass>> + str id + str name + dict arguments + str result_content + bool is_error
}
class TurnOutput {
<<dataclass>> + str assistant_message + list updated_api_history + str user_turn_id + str assistant_turn_id + list[ToolCall] tool_calls_made + list[dict] tool_logs + dict tokens_used + str provider_name + str model_name + dict context_slots
}
class MaxToolIterationsError {
}
class TurnOrchestrator {
+run(dict session, TurnInput turn_input) TurnOutput
+stream(dict session, TurnInput turn_input) Iterator[dict]
}
class SeedRequest { + int pairs + str | None title
}
class SeedResponse { + str session_id + int message_count + list[dict[str, str]] turn_ids
}
class FileManager {
+get_for_context(list[str] file_paths, int max_tokens) str
+read_file(str filepath) dict
}
class Note {
<<dataclass>> + str id + str session_id + str selected_text + str note + str source_role + str created_at
}
class NoteRepositoryProtocol {
+add_note(str session_id, str selected_text, str source_role, str note) dict
+list_notes(str session_id) list[dict]
+delete_note(str note_id, str session_id) bool
}
class NoteManager {
+create(str session_id, str selected_text, str source_role, str note) Note
+list_notes(str session_id) list[Note]
+delete(str note_id, str session_id) bool
+get_for_context(str session_id, int max_tokens) str
+search(str query, int limit) list[Any]
}
class SearchResult {
<<dataclass>> + str source + str content + float score + dict metadata
}
class SearchBackend {
+search(str query, int limit, Any **kwargs) list[SearchResult]
}
class SearchCoordinator {
+search(str query, int limit, list[str] | None backends, Any **kwargs) list[SearchResult]
}
class GrepSearchBackend {
+search(str query, int limit, Any \*\*kwargs) list[SearchResult]
}
class AnthropicProvider {
+complete('AssembledContext' context) Any
+complete_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Any
+stream('AssembledContext' context) Iterator[Any]
+stream_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Iterator[Any]
}
class LLMProvider {
+complete(AssembledContext context) Any
+complete_with_tools(AssembledContext context, list[ToolCall] tool_calls, list[ToolResult] tool_results) Any
+stream(AssembledContext context) Iterator[Any]
+stream_with_tools(AssembledContext context, list[ToolCall] tool_calls, list[ToolResult] tool_results) Iterator[Any]
}
class GeminiProvider {
+complete('AssembledContext' context) Any
+complete_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Any
+stream('AssembledContext' context) Iterator[Any]
+stream_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Iterator[Any]
}
class MimoProvider {
+complete('AssembledContext' context) Any
+complete_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Any
+stream('AssembledContext' context) Iterator[Any]
+stream_with_tools('AssembledContext' context, list['ToolCall'] tool_calls, list['ToolResult'] tool_results) Iterator[Any]
}
class NormalizedResponse {
<<dataclass>> + str text + bool has_tool_calls + list[ToolCall] tool_calls + dict usage + Any raw
}
class ResponseNormalizer {
+normalize(Any raw, str provider) NormalizedResponse
+normalize_chunk(Any chunk, str provider) str
}
class SessionRepository {
+save_session(str session_id, str title, str api_history_json, str ui_history_json, str | None parent_id, int | None fork_turn_index, str | None root_id, str | None system_prompt) None
+load_session(str session_id) tuple[str, str, str | None]
+list_sessions(bool include_archived) list[dict]
+get_session_tree(bool include_archived) list[dict]
+archive_session(str session_id) bool
+unarchive_session(str session_id) bool
+delete_session(str session_id) None
+fork_session(str source_session_id, int turn_index) str
+get_export_data(str session_id) dict
}
class NoteRepository {
+add_note(str session_id, str selected_text, str source_role, str note) dict
+list_notes(str session_id) list[dict]
+delete_note(str note_id, str session_id) bool
}
class SQLiteConnection {
+get_connection() sqlite3.Connection
}
class SQLiteNoteRepository {
+add_note(str session_id, str selected_text, str source_role, str note) dict
+list_notes(str session_id) list[dict]
+delete_note(str note_id, str session_id) bool
}
class SQLiteSessionRepository {
+save_session(str session_id, str title, str api_history_json, str ui_history_json, str | None parent_id, int | None fork_turn_index, str | None root_id, str | None system_prompt) None
+load_session(str session_id) tuple[str, str, str | None]
+list_sessions(bool include_archived) list[dict]
+get_session_tree(bool include_archived) list[dict]
+archive_session(str session_id) bool
+unarchive_session(str session_id) bool
+delete_session(str session_id) None
+fork_session(str source_session_id, int turn_index) str
+get_export_data(str session_id) dict
}
class ToolCategory { + DISCOVERY + FILE_OPERATIONS + SEARCH + NOTES + WEB
}
class ToolEntry {
<<dataclass>> + types.FunctionDeclaration declaration + Callable[..., dict] fn + ToolCategory category
}
class ToolRegistry {
+register(ToolEntry entry) None
+get_handler(str name) Callable[..., dict]
+tool_names() list[str]
+get_all_entries() list[ToolEntry]
+get_entries_by_category(list[ToolCategory] categories) list[ToolEntry]
+schemas_for_provider(str provider, list[ToolCategory] | None categories) list[Any]
}

    ChatService --> ChatTurnRequest
    MessageDict *-- ToolCallDict : tool_calls
    ChatRequest *-- ChatImagePart : images
    ChatResponse *-- ToolLog : tools_used
    LlmExportResponse *-- LlmExportMetadata : metadata
    LlmExportResponse *-- LlmExportConfig : config
    LlmExportResponse *-- LlmExportTurn : turns
    TokenEstimateRequest *-- ChatImagePart : images
    ProviderInfo *-- ModelInfo : models
    ContextBudget *-- ContextSlot : allocations
    ContextBudget --> ContextSlot
    AssembledContext *-- ContextSlot : slots_used
    ToolExecutor --> ToolCall
    TurnOutput *-- ToolCall : tool_calls_made
    TurnOrchestrator --> TurnInput
    AnthropicProvider --> AssembledContext
    AnthropicProvider --> ToolCall
    AnthropicProvider --> ToolResult
    LLMProvider --> AssembledContext
    LLMProvider --> ToolCall
    LLMProvider --> ToolResult
    GeminiProvider --> AssembledContext
    GeminiProvider --> ToolCall
    GeminiProvider --> ToolResult
    MimoProvider --> AssembledContext
    MimoProvider --> ToolCall
    MimoProvider --> ToolResult
    NormalizedResponse *-- ToolCall : tool_calls
    ToolEntry *-- ToolCategory : category
    ToolRegistry --> ToolEntry
    ToolRegistry --> ToolCategory

    class chat_service_module {
        <<module>>
        +_make_title(list[dict] ui_messages) str
        +_context_file_basenames(list[str] | None context_files) list[str] | None
    }
    class dependencies_module {
        <<module>>
        +get_settings()
        +get_db_connection()
        +get_tool_registry()
        +get_prompt_manager()
        +get_response_normalizer()
        +get_session_repo() 'SessionRepository'
        +get_note_repo()
        +get_llm_provider(str | None provider_name, str | None model_override)
        +get_token_counter()
        +get_search_coordinator()
        +get_note_manager()
        +get_file_manager()
        +get_context_budget()
        +get_context_assembler()
        +get_tool_executor()
        +get_turn_orchestrator() 'TurnOrchestrator'
        +get_chat_service('SessionRepository' session_repo, 'TurnOrchestrator' orchestrator) 'ChatService'
        +get_message_editor('SessionRepository' session_repo)
        +get_export_service('SessionRepository' session_repo) 'ExportService'
    }
    class exporter_module {
        <<module>>
        +_render_tool_call(dict[str, Any] tool) str
        +_render_message(dict[str, Any] message) str
        +export_session_to_markdown(list[dict[str, Any]] ui_messages, str title) str
        +build_config_block(str | None system_instruction, list[Any] | None tool_declarations) dict[str, Any]
        +_render_llm_part(dict[str, Any] item) dict[str, Any]
        +_render_llm_turn(dict[str, Any] item, bool already_has_parts) dict[str, Any]
        +export_session_to_llm_json(list[dict[str, Any]] api_items, str title, str session_id, str | None system_instruction, list[dict[str, Any]] | None tool_schemas) dict[str, Any]
    }
    class logger_module {
        <<module>>
        +setup_logging(bool is_local_dev) None
        +_add_request_context(logging.Logger logger, str method_name, dict event_dict) dict
        +bind_request_context(str | None **kwargs) None
        +clear_request_context() None
        +log_timing(structlog.BoundLogger log, str event, str | int | float **extra) Generator[dict, None, None]
    }
    class main_module {
        <<module>>
        +async lifespan(FastAPI app)
    }
    class message_editor_module {
        <<module>>
        +_load_histories(SessionRepository repo, str session_id) tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]
        +_save_histories(SessionRepository repo, str session_id, list[dict[str, Any]] api_items, list[dict[str, Any]] ui_messages, str | None system_prompt) None
        +_find_ui_by_turn_id(list[dict[str, Any]] ui_messages, str turn_id) int
    }
    class message_format_module {
        <<module>>
        +make_user_message(str content, str | None turn_id) MessageDict
        +make_assistant_message(str | list[dict[str, Any]] content, list[ToolCallDict] | None tool_calls, str | None turn_id) MessageDict
        +make_tool_message(str tool_call_id, str content, str | None turn_id) MessageDict
    }
    class prompt_logger_module {
        <<module>>
        +_last_date_in_log(Path target) str | None
        +_render_diff_lines(list[str] lines, str prefix, int max_lines) list[str]
        +_render_tool(int index, dict[str, Any] tool) list[str]
        +_build_entry(str user_message, list[dict[str, Any]] | None tool_logs, datetime now, Path target, str | None session_id, str | None session_title) str
        +log_turn(str | None user_message, list[dict[str, Any]] | None tool_logs, str | None session_id, str | None session_title, Path | str | None log_path) None
        +log_prompt(str prompt, Path | str | None log_path) None
    }
    class serializers_module {
        <<module>>
        +dehydrate_history(list history, list[str] | None turn_ids) str
        +_gemini_content_to_common(Any content, str | None turn_id) dict | None
        +hydrate_history(str json_string) list[dict]
    }
    class token_counter_module {
        <<module>>
        +estimate_tokens_for_text(str text) int
        +estimate_tokens_for_image(str b64_data, str mime_type) int
        +estimate_tokens_for_context_files(list[str] file_contents) int
        +build_pending_context_estimate(str user_message, list[dict] | None images, list[str] | None context_file_contents, str | None system_prompt, int history_token_count) TokenEstimate
        +count_session_tokens(str api_history_json, str | None system_prompt, str | None model) TokenEstimate
    }
    class api_chat_module {
        <<module>>
        +async chat(ChatRequest request, ChatService service, PromptManager pm) ChatResponse
        +async chat_stream(ChatRequest request, ChatService service, PromptManager pm)
        +estimate_pending_tokens(TokenEstimateRequest request) TokenEstimateResponse
        +get_session_token_count(str session_id, SessionRepository session_repo) SessionTokensResponse
        +_resolve_context_file_paths(list[str] | None context_files) list[str] | None
    }
    class api_files_module {
        <<module>>
        +list_files() list[FileListItem]
        +read_file_endpoint(str filepath) FileReadResponse
        +write_file_endpoint(str filepath, FileWriteRequest request) dict
        +append_to_file_endpoint(FileAppendRequest request) dict
        +revert_file_edit(str revert_id) RevertResponse
        +repo_map_endpoint() dict
        +_resolve_data_path(str filepath) Path
    }
    class api_notes_module {
        <<module>>
        +_note_to_response(Note note) NoteResponse
        +create_note(str session_id, NoteCreateRequest request, NoteManager note_manager) NoteResponse
        +list_notes(str session_id, NoteManager note_manager) list[NoteResponse]
        +delete_note(str session_id, str note_id, NoteManager note_manager) None
    }
    class api_prompts_module {
        <<module>>
        +get_prompt_modes(PromptManager pm) list[PromptModeResponse]
        +get_prompt_mode_detail(str mode_id, PromptManager pm) PromptModeDetail
        +reload_prompts(PromptManager pm) dict
    }
    class api_providers_module {
        <<module>>
        +list_providers() list[ProviderInfo]
        +get_active_provider() ActiveProvider
        +get_app_info() AppInfo
        +_default_model_for(str provider_id) str
    }
    class api_sessions_module {
        <<module>>
        +get_sessions(bool include_archived, SessionRepository session_repo) list[SessionSummary]
        +get_session_tree(bool include_archived, SessionRepository session_repo) list[SessionNode]
        +get_session(str session_id, SessionRepository session_repo) dict
        +get_session_state(str session_id, SessionRepository session_repo) dict
        +delete_session(str session_id, SessionRepository session_repo) None
        +archive_session(str session_id, SessionRepository session_repo) dict
        +unarchive_session(str session_id, SessionRepository session_repo) dict
        +fork_session(str session_id, ForkRequest request, SessionRepository session_repo) ForkResponse
        +export_session(str session_id, ExportService export_service) PlainTextResponse
        +export_session_llm(str session_id, ExportService export_service) LlmExportResponse
        +edit_message(str session_id, str turn_id, MessageEditRequest request, MessageEditService editor) MessageEditResponse
        +delete_message(str session_id, str turn_id, bool delete_pair, MessageEditService editor) MessageDeleteResponse
        +truncate_messages(str session_id, TruncateRequest request, MessageEditService editor) TruncateResponse
        +get_system_prompt(str session_id, MessageEditService editor) SystemPromptResponse
        +update_system_prompt(str session_id, SystemPromptUpdateRequest request, MessageEditService editor) SystemPromptUpdateResponse
    }
    class api_test_helpers_module {
        <<module>>
        +seed_session(SeedRequest request, SessionRepository session_repo) SeedResponse
    }
    class providers_base_module {
        <<module>>
        +get_provider(str | None provider_name, str | None model_override) LLMProvider
    }
    class providers_gemini_module {
        <<module>>
        +_build_default_registry()
        +_coerce_history_for_gemini(list history) list
    }
    class providers_mimo_provider_module {
        <<module>>
        +_build_default_registry()
    }
    class providers_schema_converters_module {
        <<module>>
        +schema_to_json_schema(Any schema) dict[str, Any]
        +declaration_to_anthropic_tool(Any declaration) dict[str, Any]
    }
    class tools_file_ops_module {
        <<module>>
        +_read_path(str filepath) tuple[Path, dict | None]
        +_create_backup(Path target_path, Path backup_dir) str
        +revert_backup(str revert_id, Path backup_dir) dict
        +read_file(str filepath) dict
        +edit_file(str filepath, str search_text, str replace_text, Path | None backup_dir) dict
        +create_file(str filepath, str content, Path | None backup_dir) dict
        +append_to_file(str filepath, str content, Path | None backup_dir) dict
        +search_knowledge_base(str query, str base_dir, int context_lines) dict
    }
    class tools_registry_module {
        <<module>>
        +_build_search_entry(Any | None search_coordinator) ToolEntry
        +build_default_registry(Any | None search_coordinator) ToolRegistry
    }
    class tools_repo_map_module {
        <<module>>
        +get_repo_map(str base_dir) dict
    }
