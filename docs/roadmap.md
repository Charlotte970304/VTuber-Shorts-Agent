# Roadmap / 里程碑

**原則：每個版本可單獨執行與測試。** `planned` 代表規劃，並非功能已完成。

| 版本 | 狀態 | 完成定義（Definition of Done） |
|---|---|---|
| v0.1 | ✅ scaffold + transcript CLI | MP4 可轉為 JSON / SRT；格式驗證、單元測試、CI |
| v0.2 | planned | SRT / JSON 純文字候選事件搜尋；三輪 prompt 初版；JSON schema |
| v0.3 | planned | 基本聲學特徵：RMS、停頓、pitch（可靠時）、時窗；保留模型/單位 |
| v0.4 | planned | 事件分段、文字與聲音特徵整合、三輪比較和候選片段排序 |
| v0.5 | planned | 候選片段預覽、核准/拒絕、標籤與原因記錄 |
| v0.6 | planned | FFmpeg 準確切片、日文字幕、可設定 9:16 布局 |
| v0.7 | planned | 針對必要片段進行視覺輔助分析，建立可選服務 |
| v1.0 | planned | 批次任務、錯誤重試、任務狀態、可重現設定 |
| v2.0 | planned | 受授權平台數據收集、評估與策略實驗 |

## 建議第一批 GitHub Issues

- [ ] `feat: benchmark Japanese transcript accuracy` — 以合法短片驗證時戳、擬聲詞、台詞誤差。
- [ ] `feat: transcript chunk checkpointing` — 長直播中途失敗可續跑。
- [ ] `feat: round-1 text-based event discovery` — 不使用聲音，先產出多個候選事件。
- [ ] `test: candidate JSON validation` — 把時間範圍和理由欄位視為 contract。
- [ ] `feat: review labels and score rubric` — 對候選片段建立人工黃金資料集。
- [ ] `experiment: transcript-only baseline` — 建立聲音模型加入前的基準成效。

## 不要過早投入

- 不要先接自動發佈或訂閱 API。
- 不要先全量下載 4–6 小時直播的視覺影格做高成本分析。
- 不要在缺少人工評估基準時，就堆疊多個聲音／情緒模型。
