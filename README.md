# mcp-tableau-free

ローカルにインストールした **Tableau の無料版**を、AI（Claude Code や ChatGPT Work）から扱うための道具一式です。
お金をかけずに、データの準備からワークブックの生成までを AI に任せることを目指しています。

入っているものは3つです。

1. **ローカル MCP サーバ** — `.hyper` ファイルの中身を AI から直接読めるようにします
2. **Claude Code 用スキル2つ** — Tableau 分析の進め方と、ローカル MCP の登録手順を AI に教えます
3. **ChatGPT / Codex 用 Plugin** — 同じ分析知識と ChatGPT Work 向けの安全な接続・確認手順を配布します

Tableau Cloud / Server は使いません。すべて手元のファイルで完結します。

---

## 前提

- **Tableau の無料版が PC にインストール済み**であること（`.hyper` を開いて中身を確認するために使います）
- 64 ビット版 Python 3.11〜3.14
- Claude Code、または Developer mode と Secure MCP Tunnel を利用できる ChatGPT workspace
- ChatGPT Work で Skill も使う場合は、Plugin のインストールまたは workspace への公開権限

WSL で作業する場合、Tableau 本体は Windows 側のままで構いません。ファイルの受け渡しだけ気をつけます。

---

## 導入

### 1. clone してセットアップ

**WSL / Linux / macOS**（動作確認は WSL2 のみ）

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

**Windows では、起動前に Python の場所を指定してください。** 既定値は WSL / macOS 向けの綴りなので、そのままでは起動できません。

```powershell
$env:TABLEAU_MCP_PYTHON = ".venv\Scripts\python.exe"
claude
```

設定は次の2つです。リポジトリ直下以外から起動する場合は、両方を絶対パスで指定します。

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

#### Claude Code

このリポジトリの中で `claude` を起動する場合、`.claude/skills/` のスキルは**そのまま使えます**。何もしなくて構いません。

会話の内容から自動で起動しますが、`/tableau-analysis` のように名前を指定しても呼べます。
ほかのプロジェクトや全プロジェクトで使いたい場合は、[リポジトリの外から使う](#リポジトリの外から使う)を見てください。

#### ChatGPT Work / Codex

ChatGPT Work は `.claude/skills/` を直接読みません。`plugins/mcp-tableau-free/` に、ChatGPT と Codex が扱える Plugin として次を同梱しています。

- `tableau-analysis` — Claude Code 版と同じ reference・script・雛形を含む、提供元に依存しない版
- `tableau-local-mcp` — Secure MCP Tunnel の準備、3 tool の呼び出し順、未確認事項の切り分け

repo marketplace は `.agents/plugins/marketplace.json` です。ChatGPT desktop app と同じ環境の Codex CLI から、GitHub 上のこのリポジトリを追加できます。

```bash
codex plugin marketplace add takumi-sano22/mcp-tableau-free
codex plugin marketplace list
```

作業ブランチを試す場合は `--ref <branch-name>` を付けます。追加後、ChatGPT desktop app を再起動し、Plugins Directory の `mcp-tableau-free` から Plugin をインストールします。ChatGPT の web 版でも使うには、workspace 管理者が Personal の Plugin を workspace へ公開します。

Tunnel で作成した developer-mode app の技術 ID は workspace ごとに異なるため、Plugin へ固定していません。MCP 接続と Skill Plugin を同じ会話で有効にして使います。認証情報、`tunnel_id`、個人環境の絶対パスは Plugin に含めません。

---

## リポジトリの外から使う

ここまでの導入が済んでいれば、**ほかのプロジェクトからも同じサーバとスキルを呼べます**。運ぶものは2つだけです。

| 運ぶもの | A. 全プロジェクトで使う（user スコープ） | B. 特定のプロジェクトだけで使う（project スコープ） |
| --- | --- | --- |
| MCP の接続設定 | `~/.claude.json` に追記する | 対象リポジトリ直下の `.mcp.json` |
| スキル2つ | `~/.claude/skills/` へコピー | `<対象リポジトリ>/.claude/skills/` へコピー |

同名なら **project が user より優先**されます。両方に入れても壊れません。

> **MCP の設定は `.claude/` の中ではありません。** 紛らわしいのですが、user スコープは `~/.claude/` ではなく `~/.claude.json`（ファイル）、project スコープはリポジトリ直下の `.mcp.json` です。`.claude/` に入るのはスキルだけです。

以下、`<clone先>` はこのリポジトリを clone した場所の**絶対パス**に読み替えてください。

| 環境 | `<clone先>` の例 |
| --- | --- |
| WSL / Linux / macOS | `/home/<ユーザー名>/project/mcp-tableau-free` |
| Windows | `C:/Users/<ユーザー名>/project/mcp-tableau-free`（JSON の中は `/` 区切りが安全です） |

**リポジトリの外から使うときは、必ず絶対パスにします。** 起動時の作業ディレクトリが毎回変わるため、`.venv/bin/python` のような相対パスは解決できません。

### A. 全プロジェクトで使う（user スコープ）

#### A-1. MCP を登録する

**WSL / Linux / macOS** — コマンド一発で登録できます。

```bash
claude mcp add-json tableau-local '{
  "type": "stdio",
  "command": "<clone先>/.venv/bin/python",
  "args": ["-m", "experiments.tableau_local.server"],
  "env": { "TABLEAU_DATA_DIR": "<clone先>/data" }
}' -s user
```

**Windows（PowerShell）** — `C:\Users\<ユーザー名>\.claude.json` を開き、`mcpServers` の中へ次を貼ります。

```json
    "tableau-local": {
      "type": "stdio",
      "command": "<clone先>/.venv/Scripts/python.exe",
      "args": ["-m", "experiments.tableau_local.server"],
      "env": { "TABLEAU_DATA_DIR": "<clone先>/data" }
    }
```

PowerShell 5.1 はネイティブコマンドへ渡す引数から引用符を落とすため、`claude mcp add-json` に JSON をそのまま渡すと壊れます（実測）。Windows ではファイルを直接編集してください。
`~/.claude.json` は Claude Code が作るファイルで、通常はすでに `mcpServers` があります。ほかのサーバが並んでいる場合は、区切りのカンマを忘れないでください。`mcpServers` 自体が無ければ `{ "mcpServers": { ... } }` の形で作ります。

#### A-2. スキルを置く

**始めに `.claude/` へ cd した状態**から続けます。

**WSL / Linux / macOS**

```bash
mkdir -p ~/.claude/skills
cd ~/.claude
cp -r <clone先>/.claude/skills/{tableau-analysis,mcp-local-server} skills/
```

**Windows（PowerShell）**

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
cd "$env:USERPROFILE\.claude"
Copy-Item -Recurse -Force "<clone先>\.claude\skills\tableau-analysis" skills\
Copy-Item -Recurse -Force "<clone先>\.claude\skills\mcp-local-server" skills\
```

> **更新するときは、コピー先の同名ディレクトリを先に消します。** `cp -r` はコピー先に同名ディレクトリがあると、その中へ入れ子にコピーします（`skills/tableau-analysis/tableau-analysis/` ができます）。`rm -rf skills/tableau-analysis skills/mcp-local-server` してからコピーしてください。PowerShell の `Copy-Item -Force` は同じ場所へ上書きしますが、コピー元から消えたファイルは残ります。

#### A-3. 確認する

**このリポジトリの外**で確認します。中で実行すると project スコープが優先され、user 側が隠れて判定を誤ります。

```bash
cd ~   # 別のプロジェクトでもかまいません
claude mcp get tableau-local
```

`Scope: User config (available in all your projects)` と `✔ Connected` が出れば完了です。

### B. 特定のプロジェクトだけで使う（project スコープ）

設定をチームや別のマシンと共有したい場合、そのプロジェクトの `data/` を読ませたい場合はこちらです。

#### B-1. `.mcp.json` を置く

対象リポジトリの**直下**（`.claude/` の中ではありません）に `.mcp.json` を作ります。`.claude/` にいるなら1つ上です。

```json
{
  "mcpServers": {
    "tableau-local": {
      "command": "<clone先>/.venv/bin/python",
      "args": ["-m", "experiments.tableau_local.server"],
      "env": {
        "TABLEAU_DATA_DIR": "${TABLEAU_DATA_DIR:-data}"
      }
    }
  }
}
```

Windows 側の Claude Code から使う場合は、`command` を `<clone先>/.venv/Scripts/python.exe` にします。

`TABLEAU_DATA_DIR` を相対パス（`data`）のままにすると、**そのプロジェクトの `data/` を読みます**（リポジトリ直下で `claude` を起動する前提）。別の場所を読ませたいときは絶対パスを書きます。
`${VAR:-既定値}` の展開は Claude Code 固有です。ほかの MCP クライアントに渡す設定は、値を直接書いた `examples/mcp-config.json` を使ってください。

#### B-2. スキルを置く

コピー先が変わるだけで、あとは A-2 と同じです。

**WSL / Linux / macOS**

```bash
mkdir -p <対象リポジトリ>/.claude/skills
cd <対象リポジトリ>/.claude
cp -r <clone先>/.claude/skills/{tableau-analysis,mcp-local-server} skills/
```

**Windows（PowerShell）**

```powershell
New-Item -ItemType Directory -Force "<対象リポジトリ>\.claude\skills" | Out-Null
cd "<対象リポジトリ>\.claude"
Copy-Item -Recurse -Force "<clone先>\.claude\skills\tableau-analysis" skills\
Copy-Item -Recurse -Force "<clone先>\.claude\skills\mcp-local-server" skills\
```

リポジトリで共有するなら、`.mcp.json` と `.claude/skills/` をコミットします。

#### B-3. 承認する

`.mcp.json` は置いただけでは有効になりません。対象リポジトリ直下で `claude` を起動し、プロジェクトの MCP サーバを使うか聞かれたら承認します。承認するまで `⏸ Pending approval` のままで tool を呼べません。

### 外から使うときの注意

- **`pip install -e` が済んでいることが前提です。** `-m experiments.tableau_local.server` がどの作業ディレクトリからでも起動できるのは、editable install で `sys.path` に登録されているためです。clone しただけでは起動しません（先に[導入](#1-clone-してセットアップ)を済ませてください）。
- **venv を作り直すと、登録した全プロジェクトで壊れます。** 絶対パスで venv の Python を指しているためです。作り直したら登録し直してください。
- **user スコープに入れると、どのプロジェクトの Claude Code からも `TABLEAU_DATA_DIR` の中身が読めます。** 機微なデータを置くディレクトリを指定しないでください。
- **WSL と Windows の設定は別物です。** WSL の Claude Code は `/home/...` を、Windows の Claude Code は `C:/...` を見ます。両方で使うなら両方に登録します。
- **user と project の両方に登録すると、`/mcp` に `Conflicting scopes` の警告が出ます。** 同じサーバでもパスの綴りが違えば警告されます。動作には影響しません。消すには片方を削除します（`claude mcp remove tableau-local -s user`）。
- **設定を変えたら Claude Code を再起動します。** 起動中のセッションには反映されません。

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
| `assets/ref-dashboard-2026.2.twb` | Tableau 2026.2 が実際に書き出した `.twb`（構造の参照用。識別子・パス・値は伏せてあります） |

**このスキルの一番大事な主張**は「ワークブックの XML を推測で書かない」ことです。
Tableau のワークブック形式は公開仕様（公式 XSD）と実装が食い違い、**XSD を通ったファイルが Tableau で開けない**ことを実測しています。
そのため、まず実機で雛形を1つ作ってもらい、その骨格を流用して生成します。

プロジェクト固有の事情は `references/projects/<名前>/` に置きます。書き方は同ディレクトリの `README.md` にあります。

### `mcp-local-server` — Claude Code でのローカル MCP 登録と確認

stdio 形式の MCP サーバを Claude Code に登録し、**実際に tool を呼べるところまで**確認する手順です。
スコープ（user / project / local）の選び方、承認と再起動の要否、繋がらないときの切り分け、`claude -p` を使った tool の実呼び出し検証を扱います。

このリポジトリの `.mcp.json` は、このスキルが説明している project スコープの実例そのものです。

### `tableau-local-mcp` — ChatGPT Work での接続と実測確認

`plugins/mcp-tableau-free/` にだけ含む ChatGPT / Codex 用 Skill です。Secure MCP Tunnel の権限・workspace 関連付け・WSL 側の起動を切り分け、接続後は3つの tool を順番に呼びます。東京 1200・大阪 900・福岡 600 を実際の戻り値で確認できない限り、完了扱いにしません。

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
- Extensions API（ダッシュボードに外部 Web アプリを載せる）/ Embedding API（viz を外部サイトに載せる）— どちらも埋め込み向け
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

OpenAI の [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) を使います。`tunnel-client` が WSL から外向き HTTPS で接続し、ローカルの stdio MCP へ転送するため、**サーバの HTTP 化も受信ポートの開放も不要**です。既存の `.mcp.json` と stdio 起動は変更しません。

### 1. 権限と接続範囲

事前に次を用意します。

- Platform tunnel settings で作成した `tunnel_id` と runtime API key
- 実行者の Tunnels Read + Use 権限。Tunnel の作成・編集には Read + Manage も必要
- ChatGPT workspace の Developer mode 利用権限
- Tunnel と対象 ChatGPT workspace の関連付け
- WSL から `api.openai.com:443` への外向き HTTPS

runtime API key、`tunnel_id`、Tunnel profile はリポジトリへコミットしません。ローカル MCP は外部へ公開しません。

### 2. WSL でサンプルと Tunnel を起動

リポジトリ直下でサンプルを生成したあと、Platform tunnel settings から取得した最新の `tunnel-client` を使います。値は実環境のものへ置き換えてください。

```bash
./.venv/bin/python examples/create_sample_hyper.py

chmod +x /path/to/tunnel-client
export PATH="/path/to/tunnel-client-directory:$PATH"
export CONTROL_PLANE_API_KEY="<runtime API key>"

TABLEAU_MCP_ROOT="$(pwd)"
export TABLEAU_DATA_DIR="$TABLEAU_MCP_ROOT/data"

tunnel-client help quickstart
tunnel-client init \
  --sample sample_mcp_stdio_local \
  --profile tableau-local \
  --tunnel-id "tunnel_..." \
  --mcp-command "$TABLEAU_MCP_ROOT/.venv/bin/python -m experiments.tableau_local.server"

tunnel-client doctor --profile tableau-local --explain
tunnel-client run --profile tableau-local
```

`run` は ChatGPT からの確認中も起動したままにします。

### 3. ChatGPT Work で接続

1. Settings → Security and login で Developer mode を有効にする
2. ChatGPT Plugins の追加ボタンから developer-mode app を作る
3. Connection で Tunnel を選び、対象 Tunnel または `tunnel_id` を指定する
4. 検出された `list_hyper_files`、`list_hyper_tables`、`preview_hyper_table` を確認する
5. 新しい会話で MCP 接続と `mcp-tableau-free` Plugin を有効にする
6. 「`sample.hyper` の中身を確認して」と依頼する

Tunnel が表示されない場合は、対象 ChatGPT workspace との関連付けと Tunnels Read + Use 権限を確認します。

### 4. 完了判定

| 呼び出し | 実測する結果 |
| --- | --- |
| `list_hyper_files()` | `sample.hyper` |
| `list_hyper_tables(filename="sample.hyper")` | `Extract` / `Sales` |
| `preview_hyper_table(filename="sample.hyper", schema="Extract", table="Sales", limit=10)` | 東京 1200・大阪 900・福岡 600 |

行の並び順は保証されません。3つの呼び出しと値を実測できたときだけ Issue #4 の完了条件を満たします。

ChatGPT Work の管理された実行環境からローカル WSL の Tunnel を起動することはできないため、現時点でこの E2E は未確認です。確認済みなのは、同じ stdio MCP に独立した MCP クライアントから接続して3つの tool を検出し、`list_hyper_files` を呼べる境界までです。ローカル Hyper の読み取りと Tunnel 経由の呼び出しを推測で完了扱いにはしません。

Plugin の接続・Skillテストについては [OpenAI の手順](https://developers.openai.com/plugins/deploy/connect-chatgpt) も参照してください。

---

## ディレクトリ構成

```text
.claude/skills/
  tableau-analysis/      Claude Code 用 Tableau 分析スキル
  mcp-local-server/      Claude Code 用ローカル MCP 運用スキル
.agents/plugins/
  marketplace.json       ChatGPT / Codex 用 repo marketplace
plugins/
  mcp-tableau-free/
    plugin.json          portable Agent Plugin manifest
    .codex-plugin/       Codex 互換 manifest
    skills/
      tableau-analysis/  provider-neutral な Tableau 分析スキル
      tableau-local-mcp/ ChatGPT Work の接続・確認スキル
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

[リポジトリの外から使う](#リポジトリの外から使う)の手順は、WSL2 側で user スコープ登録（`claude mcp add-json` → リポジトリ外で `✔ Connected`）とスキルのコピーまで確認しました。
PowerShell 側は `Copy-Item` の上書き挙動と、ネイティブコマンドへ渡す JSON から引用符が落ちること（PowerShell 5.1）だけ実測しています。
**Windows 版 Claude Code からの user スコープ接続は未確認です。**

ChatGPT Work の管理された実行環境では、独立した MCP クライアントから stdio 接続し、3 tool の検出と空のデータディレクトリに対する `list_hyper_files` 呼び出しまで確認しました。同環境では Hyper プロセスのローカルソケット作成が `Operation not permitted` で拒否されたため、ローカル WSL の Tunnel と `sample.hyper` を使う E2E は未確認です。

`tableau-analysis` スキルのワークブック生成まわりの記述は、Tableau Desktop 2026.2（Windows）での実測にもとづきます。
**版が変われば構造も変わります。** 雛形は必ず対象環境で取り直してください。

---

## 参考

- [Hyper API](https://tableau.github.io/hyper-db/docs/) / [Hyper ファイルの読み取り](https://tableau.github.io/hyper-db/docs/guides/hyper_file/read/) / [接続とファイルロック](https://tableau.github.io/hyper-db/docs/hyper-api/connection/)
- [Tableau Document Schemas](https://github.com/tableau/tableau-document-schemas)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)

今後の予定は [ROADMAP.md](ROADMAP.md) にあります。
