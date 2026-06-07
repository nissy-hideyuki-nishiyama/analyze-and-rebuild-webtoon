# WEBTOONコミックのコマ切り出しと画像分析

## WEBTOONコミックのコマ切り出し

### プロンプト
```bash
ComfyUIでStabledifusionで画像生成および画像解析をしています。
下記の要件を満たすComfyUIのワークフロー案を複数リストアップして下さい

[システム構成]
- Ryzen 8700G + DDR5-5600 128GB + NVME SSD1TB + Geforce RTX5700Ti
- Ubuntu 24.04.LTS + Dockerコンテナ
- Dockerコンテナ上で、下記を稼働させて、画像生成をしている
  - Python3.12.3 + Pythorch 2.9.1 + CUDA 13.0
  - ComfyUI 0.17.1 + ComfyUI_frontend v1.41.19 + Templates v0.9.21 + ComfyUI-Manager V3.39.2

[前提条件]
- 所定のディレクトリに保存された複数のWEBTOONの画像ファイルが保存されている

[要件]
- 機能: WEBTOONの画像ファイルを読み込み、コマ毎に1つの画像ファイルとして出力する
  - 所定ディレクトリで画像ファイルをファイル名で昇順にシーケンシャルに読み込み、1ファイルずつ処理する
  - 読み込んだ画像ファイルに対して、画像解析をして、コマ毎にシーケンシャルな番号を付けて画像ファイルとして保存する
```

以下に、**WEBTOON画像を自動で読み込み → コマ検出 → コマごとに保存**するための  
**ComfyUIワークフロー案を複数パターン**でまとめました。  
検索結果から、特に **ComfyUI-AutoSplitGridImage** が有力であることが確認できます。   [Github](https://github.com/stormcenter/ComfyUI-autosplitgridimage)  [runcomfy.com](https://www.runcomfy.com/comfyui-nodes/ComfyUI-AutoSplitGridImage)

---

# ⭐ **WEBTOON コマ分割ワークフロー案（複数パターン）**

---

# 🟦 **ワークフロー案 A：AutoSplitGridImage（エッジ検出）による自動コマ分割**

### 📌 特徴
- **エッジ検出で縦長WEBTOONのコマ境界を自動推定**
- コマ数が一定でないWEBTOONに最適
- カスタムノード **ComfyUI-AutoSplitGridImage** を利用

### 📐 構成ノード例
1. **Load Image from Folder（バッチ読み込み）**
   - 指定ディレクトリを昇順で読み込み  
   - 1枚ずつ処理

2. **AutoSplitGridImage（Edge Detection モード）**
   - Columns：Edge detection  
   - Rows：Uniform（または Edge detection）
   - 出力：  
     - Preview（確認用）  
     - **Split Cells（コマ画像のテンソル）**

3. **ForEach（テンソル → 個別画像）**
   - コマごとにループ処理

4. **Save Image**
   - 保存名例：  
     ```
     {元ファイル名}_panel_{seq:03}.png
     ```

### 👍 適した用途
- コマ境界が白枠・黒枠で明確なWEBTOON
- コマ数がページごとに異なる作品

---

# 🟩 **ワークフロー案 B：縦方向のエッジ検出＋横方向固定分割（WEBTOON特化）**

### 📌 特徴
- WEBTOONは **縦スクロール形式** のため、  
  **縦方向（Y軸）だけエッジ検出** → コマ境界を抽出  
- 横方向は基本1列なので **Columns=1**

### 📐 構成ノード例
1. Load Image from Folder  
2. AutoSplitGridImage  
   - Rows：Edge detection（縦方向のコマ境界）  
   - Columns：Uniform（1列）  
3. ForEach  
4. Save Image

### 👍 適した用途
- 典型的な縦スクロールWEBTOON  
- コマ境界が横線で明確な作品

---

# 🟧 **ワークフロー案 C：OpenCV系ノード（カスタム）で輪郭抽出 → コマ切り出し**

### 📌 特徴
- AutoSplitGridImage がうまく分割できない場合の代替案
- OpenCV ノード（Canny → Contour → Bounding Box）でコマ領域を抽出

### 📐 構成ノード例
1. Load Image from Folder  
2. Convert to Grayscale  
3. Canny Edge Detection  
4. Find Contours  
5. Extract Bounding Boxes  
6. Crop Image（各Bounding Boxで切り出し）  
7. Save Image

### 👍 適した用途
- コマ境界が不規則  
- 背景色とコマ枠のコントラストが弱い作品

---

# 🟨 **ワークフロー案 D：固定高さスキャン（高さしきい値で分割）**

### 📌 特徴
- WEBTOONのコマ高さが比較的均一な場合  
- 画像を一定高さごとにスキャンし、白帯（空白）を検出して分割

### 📐 構成ノード例
1. Load Image from Folder  
2. Image Statistics（行ごとの平均輝度を取得）  
3. Detect Blank Lines（しきい値で空白行を検出）  
4. Split Image at Blank Lines  
5. Save Image

### 👍 適した用途
- コマ間に明確な白帯があるWEBTOON

---

# 🟥 **ワークフロー案 E：LLM画像解析（Qwen-VL など）でコマ領域を推定 → Crop**

### 📌 特徴
- コマ枠が曖昧な作品でも、  
  **画像理解モデル（Qwen-VL など）** でコマ領域を推定可能
- ComfyUI の Vision-Language ノードを利用

### 📐 構成ノード例
1. Load Image from Folder  
2. Qwen-VL / LLaVA などで「コマ領域」を検出  
3. JSON → Bounding Box  
4. Crop Image  
5. Save Image

### 👍 適した用途
- コマ枠がほぼ無い作品  
- 背景とコマが混ざる作品

---

# 🟦 **ワークフロー案 F：バッチ処理特化（1000枚以上対応）**

検索結果より、ComfyUIは大規模バッチ処理に適していることが確認できます。   [apatero.com](https://www.apatero.com/blog/batch-process-1000-images-comfyui-guide-2025)

### 📌 特徴
- 大量のWEBTOON画像を夜間バッチで処理  
- エラー時のスキップ・ログ保存などを追加

### 📐 構成ノード例
1. Directory Loader（昇順読み込み）  
2. Try-Catch（エラー処理）  
3. AutoSplitGridImage  
4. ForEach  
5. Save Image  
6. Log Node（処理結果を記録）

---

# 📁 **保存ファイル命名規則（推奨）**

```
{episode}_{page:03}_{panel:03}.png
例： ep12_004_007.png
```

---

# 🔧 **必要なカスタムノード**

| ノード名 | 用途 | 出典 |
|---------|------|------|
| **ComfyUI-AutoSplitGridImage** | コマ分割（エッジ検出/グリッド） |   [Github](https://github.com/stormcenter/ComfyUI-autosplitgridimage)  [runcomfy.com](https://www.runcomfy.com/comfyui-nodes/ComfyUI-AutoSplitGridImage) |
| OpenCV系ノード | Canny / Contour | ComfyUI Manager |
| ForEach / Batch ノード | テンソル → 個別画像 | 標準 or カスタム |

---

# 📌 次にできること
英之さんの環境（Ubuntu + Docker + RTX 5700Ti + ComfyUI 0.17.1）なら  
**ワークフロー案 A または B が最も安定して動作**します。

---

# 👉 **必要なら、以下も作成できます**
- 実際の **ComfyUI JSON ワークフローの生成**  
- ノード接続図（テキスト版）  
- Docker内での自動バッチ処理スクリプト  
- コマ検出精度を上げるためのチューニング案

どの案をベースにしたいですか？  
それとも「実際のComfyUIワークフローJSON」をすぐ生成しましょうか？


## コマの画像分析