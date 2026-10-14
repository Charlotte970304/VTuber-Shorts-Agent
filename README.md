# VTuber Shorts Agent 🐼

> A modular Python pipeline to find newcomer-friendly Shorts moments from Japanese VTuber livestreams.
>
> 以日文 VTuber 長直播為輸入，逐步建立「轉錄 → 聲音分析 → 事件分段 → 三輪選片 → 人工審核 → Shorts 輸出 → 成效回饋」的可擴充系統。

**專案狀態：v0.3.0 — Physical Audio Features**。提供日文轉錄、純文字事件搜尋、三輪 Prompt 匯出，以及本機 RMS 音量、低音量停頓與週期性音高分析。聲音與文字的選片整合、三輪 LLM 自動執行、影片渲染及平台 API 尚未實作；見 [開發路線圖](docs/roadmap.md)。

## 目標

- 輸入約 4–6 小時的日文直播（MP4 / 常見影音格式）。
- 尋找讓**初次認識 VTuber 的觀眾**也感興趣、具有上下文與表現力的片段。
- 最終產出長度約 30–40 秒的 9:16 Shorts，保留原直播的重要畫面。
- 比較僅使用逐字稿、增加聲學特徵及增加聲音事件的選片品質。
- 初期必須人工審核；不把 AI 的情緒猜測當作事實。

## 已完成功能（v0.1）

- 本機 `faster-whisper` 日文轉錄，可產生逐字稿段落及可選詞級時間戳。
- JSON（保留資料供後續 Agent 使用），以及 SRT（方便剪輯軟體使用）。
- 驗證 JSON 結構與時間戳；命令列可檢查指定檔案。
- 測試與 GitHub Actions CI（不下載模型、不包含任何直播影片）。

## Windows 快速開始（PowerShell）

**需求：** Python 3.11 或 3.12（建議先用 3.11）、可連網下載模型；實際轉錄速度依硬體與模型不同。v0.1 轉錄依賴可選套件 `faster-whisper`。FFmpeg 命令列工具會在後續剪輯版本使用，**v0.1 CLI 的轉錄功能不強制要求你另外安裝 ffmpeg.exe**。

```powershell
# 進入剛剛解壓縮的專案資料夾
cd .\vtuber-shorts-agent

# 建立獨立 Python 環境
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安裝專案（包含轉錄與測試所需套件）
python -m pip install --upgrade pip
python -m pip install -e ".[transcribe,dev]"

# 查看指令
vtuber-shorts --help

# 把自己的影片放在 input\livestream.mp4 後再執行
vtuber-shorts transcribe --input "input\livestream.mp4" --output "data\livestream\transcript.json" --srt "data\livestream\transcript.srt" --model small --device cpu --compute-type int8

# 驗證轉錄結果
vtuber-shorts validate-transcript --input "data\livestream\transcript.json"

# 不用下載任何語音模型的自動化測試
python -m pytest -q
```

提示：本例預設 CPU 運行，適合先確認功能。若之後想用 NVIDIA GPU，需另外檢查 CUDA / cuDNN 與所安裝的 CTranslate2 版本是否相容。模型第一次使用時可能下載較大量的資料。

若 PowerShell 無法啟動虛擬環境（Execution Policy），可不用啟用它，而是將所有 `python` / `vtuber-shorts` 指令分別改用 `\.venv\Scripts\python.exe` / `\.venv\Scripts\vtuber-shorts.exe` 直接執行。

> **注意：** `transcribe` 可能需要很長的處理時間。此版本還沒有中途儲存進度／斷點續跑功能。建議第一次先用自己有權使用的短測試片段。輸入檔仍留在本機，不會由這份程式碼自動上傳任何影音；首次使用模型需要連線下載模型檔案。

## 命令列指令

```text
vtuber-shorts transcribe          將輸入音訊／影片轉成 JSON（可選 SRT）
vtuber-shorts validate-transcript 驗證現有 JSON 格式與時間戳
vtuber-shorts discover-events     從 JSON / SRT 搜尋文字線索候選事件
vtuber-shorts prepare-prompts     匯出三輪 Prompt、schema 與重疊逐字稿分塊
vtuber-shorts validate-selection  驗證 events / candidates JSON
vtuber-shorts analyze-audio       量測音量、低音量區間與週期性音高
vtuber-shorts validate-audio      驗證聲學特徵 JSON
```

執行 `vtuber-shorts transcribe --help` 可看可用參數。預設日文 `language=ja`，可加 `--vad-filter` 啟用可選 VAD，或用 `--overwrite` 覆寫既有輸出。時間戳單位為**相對原始影音開頭的秒數**。

## v0.2 純文字選片基準

已有 JSON 或 SRT 時，只需安裝 `pip install -e ".[dev]"`，不需要下載語音模型。
以下使用公開的虛構範例；未啟用虛擬環境時，將指令換成 `.\.venv\Scripts\vtuber-shorts.exe`。

```powershell
vtuber-shorts discover-events --input examples/transcript.example.json --output data/demo/events.json
vtuber-shorts validate-selection --kind events --input data/demo/events.json --transcript examples/transcript.example.json
vtuber-shorts prepare-prompts --input examples/transcript.example.json --output data/demo/prompts.json
vtuber-shorts validate-selection --input examples/candidates.example.json --transcript examples/transcript.example.json
```

`discover-events` 依字幕間隔（預設超過 3 秒）與段落長度（預設最多 90 秒，
單一字幕不切斷）聚合段落，搜尋問句、驚訝詞、故事詞、轉折詞與笑聲文字。
以不同線索類別數量排序，同分依原始時間排序，預設最多 20 個事件。
`summary` 是原字幕節錄；`priority` 是線索類別數，**不是有趣程度或情緒評分**。
可設定 `--gap-seconds`、`--max-event-seconds`、`--context-seconds`、`--max-events`。
沒有線索時合法輸出空事件；此基準可能漏掉安靜、隱含或依賴畫面的好片段。
事件尚未確認語意完整，也不是最終 30–40 秒裁切。

`prepare-prompts` 預設以 600 秒分塊、重疊 60 秒，保留完整字幕與原始時間戳，
可設定 `--chunk-seconds`、`--overlap-seconds`。匯出包含三輪指令、事件與候選 schema，
及第一輪逐字稿輸入；沒有呼叫模型或上傳資料。
後續實驗需自行逐塊執行第一輪、依時間與引用合併重複事件，再提供原始上下文給
第二輪，將可剪片段交給第三輪。模型產出需驗證並人工審核；詳見 [Prompt 說明](prompts/README.md)。

SRT 來源沒有完整媒體時長，匯入時以最後一筆字幕的結束時間作為可用時間上限，
`source_media` 使用 SRT 檔名。字幕序號會重新編成唯一段落 ID；所有分析保留原始秒數。
新指令預設拒絕覆寫輸出，加 `--overwrite` 可覆寫，但禁止輸出覆蓋輸入。

## v0.3 聲學特徵分析

不需要重新轉錄；直接讀取原始影片。更新套件後，先分析前 60 秒：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[audio,dev]"
.\.venv\Scripts\vtuber-shorts.exe analyze-audio --input "input\livestream.mp4" --output "data\livestream\audio_features.preview.json" --max-seconds 60
.\.venv\Scripts\vtuber-shorts.exe validate-audio --input "data\livestream\audio_features.preview.json"
```

確認預覽後，分析整部影片：

```powershell
.\.venv\Scripts\vtuber-shorts.exe analyze-audio --input "input\livestream.mp4" --output "data\livestream\audio_features.json"
.\.venv\Scripts\vtuber-shorts.exe validate-audio --input "data\livestream\audio_features.json"
```

若輸出已存在，重跑加 `--overwrite`。分析開始及每約 60 秒原始音訊進度會印訊息。
音訊採串流解碼；特徵列表留到結束才寫 JSON，尚無斷點續跑。
預設第一個音軌、16 kHz 單聲道、每 1 秒一窗，保留原始影音時間戳。
末窗及時間戳缺口前後可能較短；缺口不補成靜音。
`--max-seconds` 是原始時間軸截止點，省略則分析全部可解碼音訊。

- `rms`／`rms_dbfs`：振幅與 dBFS，未做音量正規化；數位靜音的 dBFS 為 `null`。
- `pauses`：40 ms 分幀低音量區間，預設低於 -40 dBFS、至少 0.3 秒。
  不是已驗證的說話停頓；音樂與遊戲聲可能遮蔽真正停頓。
- `pitch_median_hz`：約 60–600 Hz 的週期性音高，證據不足為 `null`；
  樂器、多人聲及倍頻可能造成誤差，不能當作本人聲線或情緒的確定測量。

可用 `--window-seconds`、`--silence-dbfs`、`--min-pause-seconds` 調整設定；
`--no-pitch` 跳過音高計算。方法、套件版本、單位與門檻都記錄在輸出內。
此版產出獨立聲學資料，尚未改變 `discover-events` 的文字選片結果。
欄位與限制見 [資料格式](docs/data-contracts.md)。

## 預計架構（未實作部分為設計目標）

```text
Local MP4
  ├─ Transcription (v0.1 ✅)
  └─ Physical Audio Analysis (v0.3 ✅)
          ↓
    Event Segmentation (planned)
          ↓
    Transcript-only Events + Three-round Prompt Export (v0.2 ✅)
          ↓
    Automated Three-round Clip Selection (planned)
          ↓
    Candidate JSON → Human Review (planned)
          ↓
    FFmpeg Render (planned)
          ↓
    Platform Analytics & Feedback (later)
```

完整設計見 [架構文件](docs/architecture.md) 與 [資料格式](docs/data-contracts.md)。

## Repo 主要資料夾

```text
src/vtuber_shorts_agent/  Python 套件，含 v0.1 轉錄與 v0.2 純文字基準
examples/                 虛構、可公開的 JSON 範例
docs/                     架構、資料契約、路線圖與評估方法
tests/                    自動化測試
input/                    本機影音（Git 忽略）
data/                     真實轉錄／中間產物（Git 忽略）
output/                   渲染影片（Git 忽略）
.github/workflows/        自動測試
```

## 重要的版權與隱私原則

1. **不將直播 MP4、音檔、截圖、真實 SRT、真實逐字稿、模型下載檔推上 GitHub。** `.gitignore` 是輔助防呆，不會移除已提交進 Git 歷史的檔案。
2. 不在原始碼中寫 API 金鑰、Cookie、私人路徑或登入資訊。
3. 「允許剪輯或發佈」不等於「允許公開提供原始直播與轉錄資料」。使用素材、公開範例和再利用方式需依實際授權確認。
4. 如果未來對外發布工具，應先決定 **程式碼授權**（例如 MIT 或 Apache-2.0）；**目前尚未加入 LICENSE**，避免未經決定就套用授權。第三方模型和媒體仍有各自授權。
5. 真實素材與分析資料預設保存在本機；未來加雲端 LLM 時需先明確告知資料會傳至哪個服務。

## 開發文件

- [Architecture / 系統架構](docs/architecture.md)
- [Roadmap / 版本里程碑](docs/roadmap.md)
- [Three-round Selection / 三輪選片設計](docs/clip-selection.md)
- [Data Contracts / JSON 格式](docs/data-contracts.md)
- [Evaluation / 選片品質測試](docs/evaluation.md)
- [GitHub 發佈步驟](docs/github-setup.md)
- [Contributing / 開發規範](CONTRIBUTING.md)

**Language:** 主要文件使用繁體中文；程式碼、檔名與資料欄位使用英文，便於維護。
