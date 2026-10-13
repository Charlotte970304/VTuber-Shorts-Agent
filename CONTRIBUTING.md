# Contributing

這是一個漸進式開發的 Python 專案，歡迎針對可重現的錯誤、資料格式、測試以及字幕品質提出建議。

1. 請先查看 `docs/roadmap.md`，避免把尚未實作的功能當成 Bug。
2. 在 `src/vtuber_shorts_agent/` 中新增功能；每個可測試的行為附上 `tests/` 測試。
3. `python -m pytest -q` 和 `ruff check .` 應通過，才發 Pull Request。
4. Issue 與 PR 不要附上未經授權的影片、歌詞、台詞、真實粉絲資料或任何帳號密鑰。
5. 模型輸出的情緒／魅力／語氣標籤必須明確區分測量與推論，避免假裝客觀事實。
6. 修改 JSON 欄位時，先更新 `docs/data-contracts.md` 與測試；不相容修改須提高 `schema_version`。
