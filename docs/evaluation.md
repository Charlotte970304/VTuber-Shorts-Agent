# Evaluation / 如何測試選片品質

## 產品主要驗證問題

與僅使用 SRT 比較，聲音分析是否真的增加「第一次看到這名 VTuber 也覺得有趣」的片段？

## 待建立的 A/B/C 比較

- A：Transcript-only（純文字）
- B：Transcript + physical audio features（音量、音高、停頓）
- C：Transcript + features + sound events（含笑聲/嘆氣等預訓練模型預測）

每種方法都從**同一組直播影片**產生相同數量候選片段，使用同一個評分規範。避免知道來自 A/B/C 才評分；相同片段需去重。

### 人工評分規範（提案，尚未校準）

各維度可用 1–5 分，評分人可另外選 `not enough context`：

1. `hook`: 前 1–3 秒是否有足夠吸引力？
2. `understandability`: 沒有粉絲背景知識是否看得懂？
3. `personality`: 是否呈現 VTuber 本人的辨識度或魅力？
4. `payoff`: 30–40 秒內是否有完整的期待與回報？
5. `clipability`: 不破壞上下文下能否剪成合理長度？

**注意：** 分數是評估框架，不是模型實際已達到的成效。先收集一批人工審核片段、定義一致的評分示例，再制定是否優於基準的門檻。每次測試需紀錄直播 ID、LLM / prompt 版本、候選數量與人工評估者。
