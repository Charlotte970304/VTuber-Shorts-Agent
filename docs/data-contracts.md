# Data Contracts / 資料格式

## 通用原則

- 每個 JSON 都必須有 `schema_version`，範例目前採用 `1.0`。
- `start`、`end` 是相對原始影片開頭的**秒數**，`0 <= start < end`。
- 不允許各模組私自把原始時間換成 VAD 後的壓縮時間。
- 各模組使用 `source_id` 或 `source_media` 關聯同一來源；原始本機絕對路徑避免寫入公開範例。
- `null` 應用於**未知／不可計算**，不應以 `0` 當作未量測。
- 類似 `emotion_candidate` 的欄位是**推測**，不是確定診斷；必須記錄來源與可信度。

## v0.1 — transcript.json（已實作）

見 `examples/transcript.example.json`。頂層欄位：

- `schema_version`: 現為 `1.0`。
- `source_media`: 僅檔名，不包含本機路徑。
- `duration_seconds`: 模型回傳的媒體時長，非手動估計。
- `language`: 預期 `ja`。
- `created_at_utc`: ISO 8601 UTC。
- `model`: 模型名稱與計算設定。
- `segments`: `{id, start, end, text, words}` 陣列；word timestamp 的最小單位由模型決定，不保證日文自然斷詞。

注意：Whisper 類型的時間戳是**近似估計**，實際字幕輸出前仍需檢查。

## planned — audio_features.json

見 `examples/audio_features.example.json`：時窗包含單位、數值、資料來源、模型和信心度。不能把任意 0.8 當作可跨模型比較的「可愛程度」。聲音事件模型尚未整合，此例只示範結構。

## v0.2 — events.json

`discover-events` 輸出 `schema_version="1.0"`、`source_media`、`duration_seconds`、
`selection_strategy="text-cues-v1"`、`created_at_utc`、`settings`、`events`。
每個事件包含唯一 `id`、原始 `start/end`、包覆事件的 `context_start/context_end`、
`summary`（原字幕節錄）、`interesting_reason`（文字線索說明）、
`evidence_segment_ids`、`needs_more_context`。
本機基準另附 `text_cues`（段落 ID 與線索類別）、`priority`（不同線索類別數量）。
`priority` 不表示魅力、情緒或觀看成效，事件不是最終裁切。

`events` 可為空陣列。來源段落 ID 必須唯一，亂序輸入按原始時間排列。
SRT 匯入將字幕序號轉為 1 起算段落 ID，使用 SRT 檔名作為來源，
時長以最後一筆字幕結束時間作可用上限，不宣稱為實際完整影片時長。

## v0.2 — candidates.json（已實作驗證；自動生成尚未實作）

見 `examples/candidates.example.json`：

- `start/end`: 建議成品裁切區間。
- `context_start/context_end`: 人工審核或二輪分析需要的額外上下文。
- `reason`, `hook_suggestion`: 評分理由與可能的開頭策略。
- `evidence_segment_ids`: 對應轉錄來源。
- `scores`: 必填；未知為 `null`。評分物件須包含 `hook`、`understandability`、
  `personality`、`payoff`、`clipability`，各 1–5 分，並附非空 `score_rubric_version`。
- `review_status`: `pending / approved / rejected`。

範例全部是虛構內容，不代表模型實際產出。

事件與候選 schema 位於 `src/vtuber_shorts_agent/resources/*.schema.json`，
允許額外欄位，以保留未來分析資訊與相容既有候選範例。
`validate-selection` 額外要求 `0 <= context_start <= start < end <= context_end`、
唯一事件／候選 ID 與非空整數引用陣列。附上 `--transcript` 可檢查來源一致、
上下文不超過來源時長、引用 ID 存在且與上下文重疊。
未附逐字稿時無法驗證引用真實性；schema 本身不驗證跨欄位時間關係。
候選格式驗證不強制所有範例長度為 30–40 秒；三輪 Prompt 則將此作為剪輯目標。

## v0.2 — Prompt bundle

`prepare-prompts` 輸出 `schema_version`、`prompt_version="three-round-v1"`、
`source_media`、`duration_seconds`、`settings`、`prompts`、`schemas`、
`round_1_inputs` 與操作說明。每塊包含 `chunk_id`、`start/end` 與原始 `segments`；
跨邊界段落保留完整內容與原時間，分塊重疊可能產生重複引用。
第二／三輪 Prompt 是待填上下文與模型結果的模板，不代表已產生分析結果。
