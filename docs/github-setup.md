# 第一次放上 GitHub（Windows PowerShell）

1. 在 GitHub 建立一個**空白**的 Repository，名稱建議 `vtuber-shorts-agent`。最初可選 `Private`，確認沒有把真實直播或秘密檔案推上去之後再改成 Public。
2. 將本專案解壓縮到一個沒有其他 Git Repository 的資料夾。
3. 專案根目錄開 PowerShell，執行：

```powershell
git init
git branch -M main
git status
git add .
git status --short
git commit -m "chore: initialize vtuber shorts agent"
$GitHubUser = "YOUR_GITHUB_USERNAME"
git remote add origin "https://github.com/$GitHubUser/vtuber-shorts-agent.git"
git push -u origin main
```

**請先確認 `git status --short` 沒有 `input/` 中的影片、`data/` 真實逐字稿或金鑰。** 將 `YOUR_GITHUB_USERNAME` 換成自己的 GitHub 使用者名稱（保留雙引號）。GitHub 可能需要瀏覽器授權或設定 Git Credential Manager。

## 建議 GitHub 設定

- Description: `Modular Python pipeline for Japanese VTuber livestream highlight discovery and Shorts creation.`
- Topics: `python`, `vtuber`, `shorts`, `speech-recognition`, `video-editing`, `multimodal-ai`
- `main` 分支保留可運作版本；新功能用 `feat/...` 分支。
- 設定 Pull Request 時檢查 `.github/workflows/ci.yml` 測試。
- 先以 v0.1.0 建立第一個 Tag / Release，描述已完成的是轉錄，**不是**自動選片。
- 正式對外授權前，先決定 LICENSE；「Public」與「允許他人自由使用原始碼」是不同概念。

## 如果不小心加入影片或金鑰

`.gitignore` 對已追蹤的內容無效。如果誤把 API Key 放進 Git 提交紀錄，不能只刪檔案；應立即撤銷／輪換憑證，之後處理 Git 歷史。若誤上傳了未授權媒體，要清理遠端與歷史並確認平台快取／複製風險。
