# Prompt Experiments / v0.2

三輪 Prompt 初版 `three-round-v1` 隨套件安裝，唯一維護來源在
`src/vtuber_shorts_agent/resources/round1.md`、`round2.md`、`round3.md`。
事件與候選 JSON schema 也放在同一資料夾。`prepare-prompts` 將指令、schema 與
第一輪重疊逐字稿分塊匯出成單一 JSON，沒有連線模型或自動執行三輪。

1. 對每個 `round_1_inputs` 使用 `prompts.round_1`，另外提供 bundle 的來源與時長。
2. 以原始時間區間和引用 ID 合併跨分塊重複事件；驗證 `events` JSON。
3. 依各事件 `context_start/context_end`，從原始逐字稿取回上下文段落，使用第二輪。
   上下文不足時補取原始段落；`not_clippable` 或 `needs_more_context` 不進入排名。
4. 將可剪的第二輪結果、原台詞與人工確認提供給第三輪，產生 `candidates` JSON。
5. 用 `validate-selection --transcript ...` 驗證候選，再由人播放原片確認。

第二輪輸出格式直接列在 Prompt 內；事件與最終候選有 Draft 2020-12 JSON schema。
schema 檢查欄位型別，CLI 另外檢查時間包覆、來源、唯一 ID、引用及評分。
保存每次實驗的模型名稱、設定、Prompt 版本、分塊設定及人工評估結果。

- 每份 Prompt 要有版本、輸入資料 schema、預期輸出格式。
- 輸入實際直播台詞前，確認使用的模型是否把資料傳至雲端。
- 不能把真實直播逐字稿或有版權的原始素材 commit 進來。
- 最初版本應先從 Transcript-only baseline 測試；目前沒有正式整合 LLM。

詳見 `docs/clip-selection.md`。
