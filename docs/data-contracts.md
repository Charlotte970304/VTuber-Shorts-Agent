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

## v0.3 — audio_features.json（schema 1.1）

原先 `1.0` 是未實作提案；新增必要時長、分析設定、版本與停頓欄位，
音訊格式升為 `1.1`，其他格式維持 `1.0`。舊音訊提案需重新生成。
範例為合成 200 Hz 正弦波與靜音的實際分析，非直播資料。

頂層包含 `source_media`（僅檔名）、`duration_seconds`（分析到的原始時間上限，
不是完整影音時長保證）、`created_at_utc`、`generated_by="physical-audio-v1"`、
`analysis`、`feature_definitions`、`windows`、`pauses`。
`analysis` 記錄解碼器／NumPy 版本、16 kHz 單聲道、音軌索引、時窗、
低音量門檻、最短停頓、預覽上限與音高方法設定。
使用 [PyAV AudioResampler](https://pyav.org/docs/stable/api/audio.html#audio-resamplers)
串流解碼，以 frame PTS 減去容器起始時間，保留原始影音相對秒數。
不使用 VAD 壓縮時間。時間戳缺失或倒退回報錯誤，缺口保留為未量測區間，
不偽造靜音；音軌起始延遲仍保留。

| 欄位 | 意義／單位 |
|---|---|
| `start/end` | 原始秒數，末窗或缺口邊緣可能較短 |
| `rms` | 重採樣單聲道線性振幅，不做音量正規化 |
| `rms_dbfs` | 20 log10(RMS)，數位零為 null；不是 LUFS |
| `pitch_median_hz` | 正規化自相關週期性幀中位數 Hz；不足為 null |
| `pitch_periodicity` | 自相關相似度 0–1，不是語音或情緒機率 |
| `voiced_fraction` | 通過週期性檢查的幀比例，不保證是人聲；停用 pitch 為 null |
| `low_energy_fraction` | 低於門檻的分幀樣本比例 |
| `speech_detected/laughter_probability` | 未量測，固定 null |

音高以 40 ms 分幀、搜尋約 60–600 Hz，自相關峰至少 0.85、
窗內至少半數幀通過才填音高；這些是篩選門檻，不是準確率保證。
背景音樂、混音、多人聲與倍頻可能誤判，低音量或不規則發聲可能略過。
`pauses` 是低音量連續區間 `{start, end}`，預設 -40 dBFS、至少 0.3 秒；
跨時窗合併，但不跨未量測缺口，不代表任何心理狀態。

schema 位於 `src/vtuber_shorts_agent/resources/audio_features.schema.json`。
`validate-audio` 另檢查時間順序、非重疊、時長上限、有限數值、
音高／比例範圍與未量測欄位。尚未與逐字稿或選片排名整合。

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
