---
name: mcp-local-server
description: "ローカルのMCPサーバ（stdio）をClaude Codeへ登録し、接続と動作を確認して運用するスキル。MCP登録、MCPサーバ追加、mcp add、.mcp.json、MCPスコープ、MCP接続確認、MCPが繋がらない、Pending approval、Connectedにならない、MCPをほかのプロジェクトでも使いたい、MCPの動作確認、mcp list、mcp get といったキーワードで必ず使用すること。「MCPサーバを登録して」「このMCPを他のプロジェクトでも使えるようにして」「MCPが繋がらない」「MCPのtoolを呼べるか確認して」「MCP設定をリポジトリで共有したい」といったリクエストでもトリガーする。リモートMCP（HTTP/SSE）ではなく、ローカルで動くstdioサーバを対象とする。"
---

# ローカルMCPサーバの登録と確認

ローカルで動く stdio 形式の MCP サーバを Claude Code に登録し、**実際に tool が呼べるところまで確認する**ための手順。

登録しただけでは動く保証がない。`Connected` 表示と tool の実呼び出しまで到達してから「使える」と報告すること。

---

## 1. スコープを選ぶ

Claude Code の MCP 設定には3つのスコープがあり、**同名なら local > project > user の順で優先**される。どこで使いたいかで決める。

| スコープ | 保存先 | 有効範囲 | 選ぶ基準 |
|---|---|---|---|
| `user` | `~/.claude.json` | 全プロジェクト | どのリポジトリからでも使いたい。**絶対パス必須** |
| `project` | リポジトリ直下の `.mcp.json` | そのリポジトリのみ | 設定をチームやほかのマシンと共有したい。**コミット対象** |
| `local` | `~/.claude.json` のプロジェクト別領域 | そのリポジトリのみ | 自分だけで使い、コミットしたくない |

判断に迷ったら、**共有したいなら project、自分がどこでも使いたいなら user**。両方に登録して併存させてもよい（そのリポジトリ内では project が優先される）。

---

## 2. 登録する

### user スコープ

```bash
claude mcp add --scope user <server-name> \
  -e <ENV_KEY>=<絶対パス等の値> \
  -- /abs/path/to/python -m <module.path>
```

`--` 以降が実際に起動するコマンド。**user スコープでは相対パスを使わない**。起動時の作業ディレクトリが毎回変わるため、相対パスは解決できない。

### project スコープ

リポジトリ直下に `.mcp.json` を作る。

```json
{
  "mcpServers": {
    "<server-name>": {
      "command": "${MY_PYTHON:-.venv/bin/python}",
      "args": ["-m", "<module.path>"],
      "env": {
        "MY_DATA_DIR": "${MY_DATA_DIR:-data}"
      }
    }
  }
}
```

**`${VAR:-既定値}` の展開は Claude Code が行う。** この記法を使うと、個人環境の絶対パスをコミットせずに済み、必要な人だけ環境変数で上書きできる。

ただし展開はあくまで Claude Code の機能であり、MCP の仕様ではない。ほかのクライアント向けの設定例を同梱する場合は、値を直接書いた別ファイルを用意すること。

ChatGPT Work からローカルの stdio サーバを使う場合は、OpenAI の [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) を経由する。`tunnel-client` が外向き HTTPS で接続してローカル MCP へ転送するため、**サーバを HTTP 化する必要も、受信ポートを開ける必要もない**。stdio のまま共用できる。

相対パスを既定値にした場合、**リポジトリ直下で `claude` を起動する前提**になる。README等にその前提を明記する。

#### このリポジトリでの実例

`mcp-tableau-free` の `.mcp.json` が、この形の実物。ローカルの `.hyper` を読む `tableau-local` サーバを project スコープで登録している。

```json
{
  "mcpServers": {
    "tableau-local": {
      "command": "${TABLEAU_MCP_PYTHON:-.venv/bin/python}",
      "args": ["-m", "experiments.tableau_local.server"],
      "env": {
        "TABLEAU_DATA_DIR": "${TABLEAU_DATA_DIR:-data}"
      }
    }
  }
}
```

既定値が相対パスなので、リポジトリ直下で `claude` を起動する。別の場所から使うなら、両方を絶対パスで上書きする。

---

## 3. 承認する（project スコープのみ）

`.mcp.json` は作成しただけでは有効にならない。安全のため初回に承認が要る。

1. リポジトリ直下で `claude` を起動する
2. プロジェクトの MCP サーバを使うか尋ねられたら承認する

承認するまで `claude mcp list` に `⏸ Pending approval` と表示され、tool を呼べない。

**すでに起動中の Claude Code には反映されない。** `.mcp.json` を追加・変更したらセッションの再起動が必要になる。ユーザーに案内するときは、この再起動の必要性を必ず伝える。

---

## 4. 接続を確認する

```bash
claude mcp get <server-name>   # スコープと状態を見る
claude mcp list                # 一覧で Connected を確認
```

`✔ Connected` は、**実際にサーバプロセスを起動して初期化まで成功した**ことを意味する。コマンドのパスが誤っていれば `Connected` にはならないので、起動可否の判定として信頼できる。

user スコープの確認は、**対象リポジトリの外**で実行すること。同名の project 設定があるとそちらが優先され、user 側が隠れて判定を誤る。

```bash
cd ~/<別のプロジェクト>
claude mcp get <server-name>   # "Scope: User config" と出れば全プロジェクトで有効
```

### 表示の読み方の注意

`claude mcp list` の一覧は**設定値をそのまま**表示し、展開後のパスを見せない。`${MY_PYTHON} -m ...` のように出ていても、展開に失敗しているとは限らない。展開の成否は `Connected` か、次章の実呼び出しで判定すること。

---

## 5. toolを実際に呼んで検証する

`Connected` は起動できたことしか示さない。tool が期待どおりの値を返すかは別途確認する。

セッションを再起動せずに検証したい場合は、子プロセスの Claude Code を使う。

```bash
printf '%s' '<tool名> を1回だけ呼び、戻り値をそのまま報告してください。' \
  | claude -p --mcp-config .mcp.json --strict-mcp-config \
      --allowedTools "mcp__<server-name>__<tool名>"
```

- `--mcp-config <file>` + `--strict-mcp-config` で、**承認を経ずに**指定した設定だけを使える
- `--allowedTools` に tool 名を列挙すると、権限プロンプトなしで実行できる
- user スコープの検証では `--mcp-config` を付けない（登録済み設定が使われる）

**プロンプトは必ず stdin で渡すこと。** `--allowedTools` や `--mcp-config` は可変長オプションのため、後ろに置いたプロンプト文字列まで引数として飲み込み、`Input must be provided either through stdin or as a prompt argument` で失敗する。

### 既定値が効いているかを確かめる

環境変数の既定値に依存する設定では、変数を明示的に取り除いて検証すると確実になる。

```bash
env -u MY_PYTHON -u MY_DATA_DIR claude -p --mcp-config .mcp.json --strict-mcp-config ...
```

---

## よくある失敗と対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `Pending approval` のまま | project 設定が未承認 | リポジトリ直下で `claude` を起動して承認する |
| 設定したのに一覧に出ない | 起動中のセッションに未反映 | Claude Code を再起動する |
| 別ディレクトリだと繋がらない | 相対パスを使っている | user スコープでは絶対パスにする |
| `ENOENT` でサーバが起動しない | command のパスが誤り、または venv 未作成 | パスを実在するファイルか確認する |
| `Input must be provided...` | 可変長オプションがプロンプトを飲み込んだ | プロンプトを stdin で渡す |
| 意図と違うスコープが使われる | 同名の設定が複数スコープにある | `claude mcp get` で `Scope:` を確認する |

サーバが Python パッケージなら、`pip install -e .` しておくと `sys.path` に登録され、**起動時の作業ディレクトリに依存せず** `-m <module>` で起動できる。user スコープで使うなら、この形にしておくと安定する。

---

## 運用上の注意

- **参照範囲を意識する。** user スコープに登録すると、どのプロジェクトで起動した Claude Code からもそのサーバの対象データが読める。実データを扱うサーバをむやみに user スコープへ入れない
- **戻り値は接続先のAIに渡る。** tool が返す内容は会話コンテキストに入る。機微なデータを返すサーバでは、返す範囲を絞る設計にする
- **venv への依存を明示する。** 絶対パスで venv の Python を指定した場合、venv を作り直すと全プロジェクトで壊れる。再作成したら再登録が必要になることを伝える
- **サーバ側でファイルを排他するケースに注意する。** ローカルファイルを開くサーバでは、ほかのアプリが同じファイルを開いていると失敗することがある。エラーの原因が分かるメッセージを返す実装にしておくと、利用者が自力で復旧できる
- 設定を削除するときはスコープを指定する: `claude mcp remove <server-name> -s user`（`-s project` なら `.mcp.json` が消える）

---

## 報告のしかた

「登録した」で終えず、**どこまで確認したか**を分けて報告する。

- 確認できたこと: `Connected` 表示、実際に呼んだ tool と戻り値、検証した作業ディレクトリ
- 利用者の操作が要ること: 承認、セッション再起動
- 未確認のこと: 試していない経路（別マシン、別クライアント等）

コマンドを実行していないのに「使えます」と書かない。確認していない経路は未確認として残すこと。

---

## 置き場所

このスキルの正本は [mcp-tableau-free](https://github.com/takumi-sano22/mcp-tableau-free) リポジトリにある。
利用時は `~/.claude/skills/`（全プロジェクトで使う）か、対象リポジトリの `.claude/skills/`
（そのリポジトリだけで使う）へコピーする。同名なら project 側が優先される。
