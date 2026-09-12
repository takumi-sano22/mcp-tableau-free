# MCP / Tool Use Sandbox

さまざまなMCP・tool useを小さく試す、個人用の汎用サンドボックスです。
最初の実験として、Windows上のTableau Desktop Free Editionと併用するローカルHyperファイル用MCPサーバを用意します。

## 現在できること

- `.hyper`ファイルの一覧取得
- Hyper APIによるスキーマ・テーブル一覧取得
- テーブルの先頭行の取得（最大100行）
- 架空の売上データを使ったサンプルHyperファイル生成

このサーバはローカルのファイルを扱います。Tableau Desktopの画面操作、ワークブックの編集、Cloud / Serverへの接続は実装していません。

## ディレクトリ構成

```text
experiments/
  tableau_local/          # 最初の実験：ローカルHyper用MCP
    server.py
examples/
  create_sample_hyper.py  # 架空データの生成
  mcp-config.json         # stdio接続設定例
data/                    # ローカルデータ。Git管理対象外
README.md
ROADMAP.md
pyproject.toml
```

## Windowsでの実行

64ビット版Python 3.11〜3.14を使います。以下はPowerShellで、リポジトリ直下から実行してください。

```powershell
git clone https://github.com/takumi-sano22/mcp-tool-use-sandbox.git
cd mcp-tool-use-sandbox
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[tableau]"
.\.venv\Scripts\python.exe examples/create_sample_hyper.py
$env:TABLEAU_DATA_DIR = (Resolve-Path data).Path
.\.venv\Scripts\python.exe -m experiments.tableau_local.server
```

privateリポジトリのcloneにはGitHub認証が必要です。仮想環境の有効化は不要です。
サーバはstdio形式なので、単体起動時はMCPクライアントからの入力を待ちます。終了はCtrl+Cです。

### MCPクライアントに接続

`examples/mcp-config.json`の`C:/path/to/...`を実際の絶対パスに置き換え、利用クライアントのMCP設定に登録します。
これは`mcpServers`形式の設定例です。クライアントによって登録形式が異なる場合は、同じcommand・args・環境変数を指定してください。

接続後、次の順でtoolを呼び出します。

1. `list_hyper_files()` → `sample.hyper`が表示される
2. `list_hyper_tables(filename="sample.hyper")` → `Extract` / `Sales`が表示される
3. `preview_hyper_table(filename="sample.hyper", schema="Extract", table="Sales", limit=10)` → 東京1200、大阪900、福岡600の3行が返る

行の並び順は保証しません。値は型の違いによる転送エラーを避けるため、文字列またはnullで返します。

### Tableauとの併用

`data/sample.hyper`をTableauから開いて可視化できます。同じファイルをTableauとHyper APIで同時に開くとロック競合するため、MCPから読むときはTableau側で閉じるか、コピーを利用してください。

`TABLEAU_DATA_DIR`で対象ディレクトリを指定します。未指定時は起動時の作業ディレクトリの`data`です。
toolは対象領域外のパスを拒否し、任意SQLは受け付けません。ローカルの信頼できるクライアントでの実験を想定しています。
実データや認証情報をコミットせず、MCPの戻り値が接続先AIに渡ることを踏まえて利用してください。

## 実験を追加する

1. `experiments/<実験名>/`に独立したモジュールを追加する
2. 目的・起動方法・必要な権限をそのディレクトリのREADMEに記載する
3. 専用の依存ライブラリは`pyproject.toml`のoptional-dependenciesに追加する
4. `ROADMAP.md`に結果と次に試すことを記録する

共通化は複数の実験で必要になった段階で行います。自動テストコードは初期構成に含めず、上記のサンプルで動作確認します。

## 動作確認済み環境

2026-09-12にWindows / Python 3.14.3 / MCP SDK 1.30.0 / tableauhyperapi 0.0.26558で、サンプル生成、stdio接続、3つのtool、不正パスと行数上限の拒否を確認しました。
Tableau Desktop本体と利用者のAIクライアントへの接続は、ロードマップの次の段階です。

## 参考

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Hyper API](https://tableau.github.io/hyper-db/docs/)
- [Hyperファイルの読み取り](https://tableau.github.io/hyper-db/docs/guides/hyper_file/read/)
- [Hyper接続とファイルロック](https://tableau.github.io/hyper-db/docs/hyper-api/connection/)

今後の予定は[ROADMAP.md](ROADMAP.md)を参照してください。
