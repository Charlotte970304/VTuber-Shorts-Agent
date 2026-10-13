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

## planned — candidates.json

見 `examples/candidates.example.json`：

- `start/end`: 建議成品裁切區間。
- `context_start/context_end`: 人工審核或二輪分析需要的額外上下文。
- `reason`, `hook_suggestion`: 評分理由與可能的開頭策略。
- `evidence_segment_ids`: 對應轉錄來源。
- `scores`: 未來必須有定義明確的量尺與評分策略版本。
- `review_status`: `pending / approved / rejected`。

範例全部是虛構內容，不代表模型實際產出。
