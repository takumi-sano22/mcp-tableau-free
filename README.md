# mcp-tableau-free

ローカルにインストールした **Tableau の無料版**を、AI（Claude Code など）から扱うための道具一式です。
お金をかけずに、データの準備からワークブックの生成までを AI に任せることを目指しています。

入っているものは2つです。

1. **ローカル MCP サーバ** — `.hyper` ファイルの中身を AI から直接読めるようにします
2. **スキル2つ** — Tableau 分析の進め方と、ローカル MCP の登録手順を AI に教えます

Tableau Cloud / Server は使いません。すべて手元のファイルで完結します。

---

## 前提

- **Tableau の無料版が PC にインストール済み**であること（`.hyper` を開いて中身を確認するために使います）
- 64 ビット版 Python 3.11〜3.14
- Claude Code または Claude Cowork（ChatGPT Work からも使えます。[後述](#chatgpt-work-から使う)）

WSL で作業する場合、Tableau 本体は Windows 側のままで構いません。ファイルの受け渡しだけ気をつけます。

---

## 導入

### 1. clone してセットアップ

**WSL / Linux / macOS**

```bash
git clone https://github.com/takumi-sano22/mcp-tableau-free.git
cd mcp-tableau-free
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[tableau]"
./.venv/bin/python examples/create_sample_hyper.py
```

**Windows（PowerShell）**

```powershell
git clone https://github.com/takumi-sano22/mcp-tableau-free.git
cd mcp-tableau-free
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[tableau]"
.\.venv\Scripts\python.exe examples/create_sample_hyper.py
```

仮想環境の有効化は不要です。`create_sample_hyper.py` は、架空の売上データを `data/sample.hyper` に作ります。
実データなしで接続確認ができます。

### 2. Claude Code に接続する

リポジトリ直下の `.mcp.json` が接続設定です。**リポジトリ直下で `claude` を起動**してください（既定値が相対パスのため）。

```bash
claude
```

1. 起動時にプロジェクトの MCP サーバを使うか聞かれるので、承認する
2. `claude mcp list` で `tableau-local` が `✔ Connected` になることを確認する

承認するまでは `Pending approval` のままで tool を呼べません。`.mcp.json` を変更したときは Claude Code を再起動します。

別の場所から起動したい場合は、次の環境変数を絶対パスで指定します。

| 環境変数 | 既定値 | 用途 |
| --- | --- | --- |
| `TABLEAU_MCP_PYTHON` | `.venv/bin/python` | 起動する Python。Windows では `.venv\Scripts\python.exe` |
| `TABLEAU_DATA_DIR` | `data` | `.hyper` を探すディレクトリ |

### 3. 動かしてみる

Claude Code で、次の順に tool を呼ばせます。

```
sample.hyper の中身を見せて
```

| tool | 返るもの |
| --- | --- |
| `list_hyper_files()` | `sample.hyper` |
| `list_hyper_tables(filename="sample.hyper")` | `Extract` / `Sales` |
| `preview_hyper_table(filename="sample.hyper", schema="Extract", table="Sales", limit=10)` | 東京 1200・大阪 900・福岡 600 の3行 |

同じファイルを Tableau で開いて、値が一致することを確認できます（[Tableau との併用](#tableau-との併用)）。

### 4. スキルを入れる

このリポジトリの中で `claude` を起動する場合、`.claude/skills/` のスキルは**そのまま使えます**。
ほかのプロジェクトでも使いたい場合は、ホームへコピーします。

```bash
cp -r .claude/skills/tableau-analysis ~/.claude/skills/
cp -r .claude/skills/mcp-local-server ~/.claude/skills/
```

Claude Code を再起動すると読み込まれます。会話の内容から自動で起動しますが、`/tableau-analysis` のように名前を指定しても呼べます。

---

## スキルの説明

### `tableau-analysis` — Tableau 分析を AI 駆動で進める

Tableau で分析するときに AI が踏みがちな落とし穴を、先回りで潰すためのスキルです。

| reference | 内容 |
| --- | --- |
| `data-handoff.md` | データを `.hyper` へ渡す作法。long 形式・0 件の扱い・ファイルロック回避 |
| `workbook-generation.md` | `.twb` / `.twbx` をコードから生成する手順と、実測した失敗の記録 |
| `analysis-recipes.md` | 「何を見たいか」からシート構成を決める型 |
| `official-sources.md` | 公式の仕様・操作手順の調べ方と、情報源の優先順位 |

| script / asset | 用途 |
| --- | --- |
| `scripts/build_hyper.py` | CSV 群を型を明示して `.hyper` に格納する |
| `scripts/validate_twb.py` | 公式 XSD で `.twb` を構文検証する（`lxml` が要る。`pip install -e ".[twb]"`） |
| `scripts/build_workbook_from_template.py` | 雛形を土台にワークブックを組み立てる実装例（要編集） |
| `assets/ref-dashboard-2026.2.twb` | Tableau 2026.2 が実際に書き出した `.twb`（構造の参照用） |

**このスキルの一番大事な主張**は「ワークブックの XML を推測で書かない」ことです。
Tableau のワークブック形式は公開仕様（公式 XSD）と実装が食い違い、**XSD を通ったファイルが Tableau で開けない**ことを実測しています。
そのため、まず実機で雛形を1つ作ってもらい、その骨格を流用して生成します。

プロジェクト固有の事情は `references/projects/<名前>/` に置きます。書き方は同ディレクトリの `README.md` にあります。

### `mcp-local-server` — ローカル MCP の登録と確認

stdio 形式の MCP サーバを Claude Code に登録し、**実際に tool を呼べるところまで**確認する手順です。
スコープ（user / project / local）の選び方、承認と再起動の要否、繋がらないときの切り分け、`claude -p` を使った tool の実呼び出し検証を扱います。

このリポジトリの `.mcp.json` は、このスキルが説明している project スコープの実例そのものです。

---

## 使っている Tableau の API

| 使っているもの | 何に使うか |
| --- | --- |
| **[Tableau Hyper API](https://tableau.github.io/hyper-db/docs/)**（Python 版 `tableauhyperapi`） | `.hyper` の作成・テーブル定義・行の挿入・読み取り。MCP サーバとスクリプトの中心 |
| **[Tableau Document Schemas](https://github.com/tableau/tableau-document-schemas)**（公式 XSD） | `.twb` の構文検証。**足切りにしか使えません**（通っても Tableau が開けないことがあります） |

`.twb` / `.twbx` の生成は、公式 API ではなく**ファイル形式（XML / zip）を直接扱っています**。
Tableau にはワークブックを書き出す公式のローカル API がないためです。だからこそ、実機の出力を正とする進め方をとっています。

**使っていない API**（無料版のローカル運用では不要、または使えません）

- Tableau REST API / Metadata API / VizQL Data Service — Tableau Cloud / Server 向け
- Extensions API / Embedding API — ダッシュボード埋め込み向け
- Tableau Server Client（`tableauserverclient`）— 発行先のサーバが必要

Hyper API はローカルで `hyperd` プロセスを起動して動きます。実行すると作業ディレクトリに `hyperd.log` ができます（`.gitignore` 済み）。
テレメトリは `DO_NOT_SEND_USAGE_DATA_TO_TABLEAU` で無効にしています。

---

## MCP サーバの tool

| tool | 内容 |
| --- | --- |
| `list_hyper_files()` | データディレクトリ直下の `.hyper` 一覧 |
| `list_hyper_tables(filename)` | スキーマ名とテーブル名の一覧 |
| `preview_hyper_table(filename, schema, table, limit)` | 列名と先頭行（1〜100 行） |

読み取り専用です。任意 SQL は受け付けず、`TABLEAU_DATA_DIR` の外は拒否します。
値は型の違いによる転送エラーを避けるため、文字列か null で返します。行の並び順は保証しません。

> **注意**: tool の戻り値は AI の会話に渡ります。機微なデータを置くディレクトリを指定しないでください。

---

## Tableau との併用

**Hyper ファイルは読み取りだけでもプロセス間で排他されます。** Tableau で開いている間は MCP から読めず、逆も同様です
（`The database file is locked by another process`）。この場合、tool は日本語でロック競合を知らせます。

対処は簡単で、**Tableau に渡すのはコピーにする**ことです。

```bash
# WSL 側で、リポジトリ直下から実行する。<Windowsユーザー名> は自分の環境に合わせる
cp data/sample.hyper /mnt/c/Users/<Windowsユーザー名>/Desktop/sample_tableau.hyper
```

コピーした `.hyper` をダブルクリック（または Tableau へドラッグ＆ドロップ）して、`Extract` スキーマの `Sales` テーブルを開きます。
`\\wsl.localhost\<ディストリ名>\home\...` で WSL 上のファイルを直接開くこともできますが、ネットワークパス経由のロック挙動は未確認です。

ファイルを開かない `list_hyper_files` は、占有中でも動きます。

---

## ChatGPT Work から使う

OpenAI の [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) を経由すると、
このサーバを ChatGPT Work からも呼べます。`tunnel-client` が外向き HTTPS で接続してローカルの stdio MCP へ転送するため、
**サーバを HTTP 化する必要も、ポートを開ける必要もありません**。Claude Code 向けの起動方式をそのまま共用できます。

手順は [#4](https://github.com/takumi-sano22/mcp-tableau-free/issues/4) で扱っています。
**エンドツーエンドの動作は未確認**です。確認済みなのは Claude Code からの経路だけです。

ほかの MCP クライアントに登録する場合は、`examples/mcp-config.json` の `C:/path/to/...` を実際の絶対パスへ置き換えて使ってください
（`.mcp.json` の `${VAR:-既定値}` という書き方は Claude Code 固有の展開です）。

---

## ディレクトリ構成

```text
.claude/skills/
  tableau-analysis/      Tableau 分析スキル（reference・script・雛形）
  mcp-local-server/      ローカル MCP の登録・確認スキル
experiments/
  tableau_local/
    server.py            MCP サーバ本体
examples/
  create_sample_hyper.py 架空データの生成
  mcp-config.json        ほかのクライアント向けの設定例
data/                    ローカルデータ（Git 管理対象外）
.mcp.json                Claude Code 用のプロジェクト接続設定
```

---

## 動作確認済み環境

2026-09-12 に、MCP SDK 1.30.0 / tableauhyperapi 0.0.26558 で確認しました。

- **Windows / Python 3.14.3** — サンプル生成、stdio 接続、3 つの tool、対象外パスと行数上限の拒否
- **WSL2 Ubuntu 24.04 / Python 3.12.3** — 上記に加えて、Claude Code からの tool 呼び出し、ロック競合時のエラー、Windows 側へコピーした `.hyper` の読み取り

Windows 側へコピーしたサンプルを Tableau Desktop 2026.2 で開き、3 行の値が MCP の戻り値と一致することを確認しています。

`tableau-analysis` スキルのワークブック生成まわりの記述は、Tableau Desktop 2026.2（Windows）での実測にもとづきます。
**版が変われば構造も変わります。** 雛形は必ず対象環境で取り直してください。

---

## 参考

- [Hyper API](https://tableau.github.io/hyper-db/docs/) / [Hyper ファイルの読み取り](https://tableau.github.io/hyper-db/docs/guides/hyper_file/read/) / [接続とファイルロック](https://tableau.github.io/hyper-db/docs/hyper-api/connection/)
- [Tableau Document Schemas](https://github.com/tableau/tableau-document-schemas)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

今後の予定は [ROADMAP.md](ROADMAP.md) にあります。
