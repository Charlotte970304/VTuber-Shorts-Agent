# Architecture / 系統架構

## 產品目標

本專案不是「找最大聲的一段」，而是辨識**陌生觀眾也看得懂、對 VTuber 本人產生興趣**的 30–40 秒片段。長直播不直接按固定時間切成 Shorts，而是先找事件，再決定範圍。

## 資料流

```text
[input/stream.mp4] ────────────────────────┐
    │                                      │
    ├── Transcript Service (v0.1)          ├── Audio Feature Service (v0.3)
    │       │                              │           │
    │       └── transcript.json            └── audio_features.json
    │                       │                    │
    │                       └──── time alignment ┘
    │                                  │
    │                        Event Segmentation
    │                                  │
    │                     Round 1: Event Discovery
    │                                  │
    │                     Round 2: Context & Timing
    │                                  │
    │                     Round 3: New Viewer Ranking
    │                                  │
    │                         candidates.json
    │                                  │
    │                         Manual Review + Tags
    │                                  │
    │                          FFmpeg Shorts Render
    │                                  │
    └──────────────────── optional visual review
```

## 模組邊界（planned 不表示已實作）

| 模組 | 輸入 | 輸出 | 版本 |
|---|---|---|---|
| Transcription | 本機影音 | 帶時間戳逐字稿 JSON / SRT | v0.1 已完成 |
| Text-based Clip Selection | JSON / SRT | 文字線索候選事件、三輪 Prompt 實驗輸入 | v0.2 已完成本機基準；LLM 自動執行未實作 |
| Audio Analysis | 第一個本機音軌 | RMS / dBFS、低音量區間、週期性音高 JSON | v0.3 已完成；非語音／情緒／聲音事件分類器 |
| Event Segmentation | 台詞 + 聲音特徵 | Events | v0.4 planned |
| Three-round Selection | 事件 + 前後文 | Candidates | v0.4 planned |
| Review | Candidates + 影音 | 人工標記 | v0.5 planned |
| Render | 影音 + 核准結果 | 9:16 MP4 | v0.6 planned |
| Visual Analysis | 少量必要畫面 | 輔助判斷 | v0.7 planned |
| Orchestration | 各模組的輸入輸出 | 可重跑任務 | v1.0 planned |
| Analytics | 已發佈影片的合法可得資料 | 評估與規則建議 | v2.0 planned |

## 設計原則

- 以原始影片 0 秒作為唯一共同時間原點，單位秒（float），`start` 包含、`end` 不包含。
- AI 是建議工具，不能以聲學特徵直接證實害羞、生氣等心理狀態。
- 預設不使用第三方雲端 API；未來若引入，需明確設置與揭露。
- 模型與 Prompt 版本必須記錄，避免無法重現。
- 不提前引入龐大 Agent 框架；流程穩定後再導入重試、快取與任務編排。
- 同一個 `transcript.json` 可以重跑不同選片策略，而不必重做語音轉錄。
- v0.1 提供轉錄與驗證；v0.2 增加 `discover-events`、`prepare-prompts`、`validate-selection`。Prompt 匯出與實際模型執行分開。

## 資料儲存

早期以 JSON + 本機目錄存放，未來有大量影片、片段、實驗版本及成效資料時才加入 SQLite。
