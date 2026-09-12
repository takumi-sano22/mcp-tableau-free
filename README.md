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
.mcp.json                # Claude Code用のプロジェクト接続設定
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

## WSLでの実行

Claude CodeをWSLで使う場合は、WSL側にPython環境を作ります。Tableau DesktopはWindows側のままで構いません。

```bash
git clone git@github.com:takumi-sano22/mcp-tool-use-sandbox.git
cd mcp-tool-use-sandbox
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[tableau]"
./.venv/bin/python examples/create_sample_hyper.py
```

`tableauhyperapi`はLinux向けのwheelも配布されるため、WSL側でもそのまま動作します。

### Claude Codeに接続

リポジトリ直下の`.mcp.json`がプロジェクト単位の接続設定です。個人環境の絶対パスを含めないよう、既定値を相対パスにし、環境変数で上書きできるようにしています。

| 環境変数 | 既定値 | 用途 |
| --- | --- | --- |
| `TABLEAU_MCP_PYTHON` | `.venv/bin/python` | 起動するPython。Windowsでは`.venv\Scripts\python.exe`を指定する |
| `TABLEAU_DATA_DIR` | `data` | 対象のデータディレクトリ |

既定値は相対パスなので、リポジトリ直下で`claude`を起動してください。別の場所から起動する場合は、両方を絶対パスで指定します。
`${VAR:-既定値}`という書き方の展開はClaude Codeが行います。ほかのクライアントに登録する場合は、`examples/mcp-config.json`のように値を直接指定してください。

初回はプロジェクトのMCP設定を承認する操作が必要です。

1. リポジトリ直下で`claude`を起動する
2. プロジェクトのMCPサーバを使うか尋ねられたら承認する
3. `claude mcp list`で`tableau-local`が`Connected`になることを確認する

承認するまでは`claude mcp list`に`Pending approval`と表示され、toolを呼べません。
`.mcp.json`を追加・変更したときは、起動中のClaude Codeを再起動してください。

### ChatGPT Workに接続

ChatGPT Workからローカルサーバを使う場合は、OpenAIの[Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)を使います。ChatGPT Workに`.mcp.json`を読み込ませるのではなく、Windows上の`tunnel-client`が外向きHTTPSでOpenAIへ接続し、ローカルのstdio MCPへ要求を転送します。受信ポートの開放や、認証なしの公開URLは不要です。

公式の`tunnel-client`はローカルMCPへのstdio接続をサポートするため、このサーバをHTTP化する必要はありません。既存のClaude Code向けstdio起動をそのまま共用します。

事前に次を用意します。

- PlatformのTunnel設定で作成した`tunnel_id`
- `tunnel-client`用のruntime API key
- 対象Platform organizationのTunnel権限（作成・変更はRead + Manage、利用はRead + Use）
- ChatGPT側のdeveloper mode利用権限
- Tunnelに、利用するPlatform organizationとChatGPT workspaceが関連付けられていること

Windowsのリポジトリ直下で、PlatformのTunnel設定から取得した最新の`tunnel-client`を使います。以下の値は例なので、実際の値へ置き換えてください。

```powershell
$env:CONTROL_PLANE_API_KEY = "<runtime API key>"
$env:TABLEAU_DATA_DIR = (Resolve-Path data).Path

tunnel-client help quickstart
tunnel-client init --sample sample_mcp_stdio_local --profile tableau-local --tunnel-id <tunnel_id> --mcp-command ".\.venv\Scripts\python.exe -m experiments.tableau_local.server"

tunnel-client doctor --profile tableau-local --explain
tunnel-client run --profile tableau-local
```

`CONTROL_PLANE_API_KEY`は環境変数だけで渡し、リポジトリ、設定例、ログへ書き込まないでください。Tunnelのprofileもリポジトリ外で管理します。

`tunnel-client run`を起動したまま、ChatGPTのPlugins画面でdeveloper-mode appを作成し、ConnectionにTunnelを選びます。対象Tunnelを選択するか`tunnel_id`を指定し、次の「toolの呼び出し」の順で確認します。Tunnelが表示されない場合は、ChatGPT workspaceとの関連付けとRead + Use権限を確認してください。

### ほかのMCPクライアントに接続

`examples/mcp-config.json`の`C:/path/to/...`を実際の絶対パスに置き換え、利用クライアントのMCP設定に登録します。
これは`mcpServers`形式の設定例です。クライアントによって登録形式が異なる場合は、同じcommand・args・環境変数を指定してください。

### toolの呼び出し

接続後、次の順でtoolを呼び出します。

1. `list_hyper_files()` → `sample.hyper`が表示される
2. `list_hyper_tables(filename="sample.hyper")` → `Extract` / `Sales`が表示される
3. `preview_hyper_table(filename="sample.hyper", schema="Extract", table="Sales", limit=10)` → 東京1200、大阪900、福岡600の3行が返る

行の並び順は保証しません。値は型の違いによる転送エラーを避けるため、文字列またはnullで返します。

### Tableauとの併用

Hyperファイルは読み取りだけでもプロセス間で排他されます。接続中のファイルへ別プロセスから接続すると、`The database file is locked by another process`で失敗することを確認しました。
Tableau Desktopでファイルを開いている間はMCPから読めず、逆も同様です。この場合、toolは日本語でロック競合を知らせます。

ファイルを開かない`list_hyper_files`は、占有中でも動作します。

同じサンプルをTableauで確認するときは、コピーを開くと競合しません。WSLのファイルをWindowsのTableauで開く場合は、次のようにコピーします。

```bash
# WSL側で、リポジトリ直下から実行する。<Windowsユーザー名>は自分の環境に合わせる
cp data/sample.hyper /mnt/c/Users/<Windowsユーザー名>/Desktop/sample_tableau.hyper
```

1. エクスプローラーでコピーした`sample_tableau.hyper`をダブルクリックする（またはTableau Desktopへドラッグ＆ドロップする）
2. `Extract`スキーマの`Sales`テーブルを開く
3. `region`と`sales`の3行（東京1200、大阪900、福岡600）を確認する
4. `preview_hyper_table`の戻り値と突き合わせる

`\\wsl.localhost\<ディストリ名>\home\...`でWSL上のファイルを直接開くこともできますが、ネットワークパス経由でのロック挙動は未確認です。コピーの利用を勧めます。

### そのほかの注意点

`TABLEAU_DATA_DIR`で対象ディレクトリを指定します。未指定時は起動時の作業ディレクトリの`data`です。
toolは対象領域外のパスを拒否し、任意SQLは受け付けません。ローカルの信頼できるクライアントでの実験を想定しています。
実データや認証情報をコミットせず、MCPの戻り値が接続先AIに渡ることを踏まえて利用してください。

Hyper APIは起動時の作業ディレクトリに`hyperd.log`を作ります。`.gitignore`で除外済みです。

## 実験を追加する

1. `experiments/<実験名>/`に独立したモジュールを追加する
2. 目的・起動方法・必要な権限をそのディレクトリのREADMEに記載する
3. 専用の依存ライブラリは`pyproject.toml`のoptional-dependenciesに追加する
4. `ROADMAP.md`に結果と次に試すことを記録する

共通化は複数の実験で必要になった段階で行います。自動テストコードは初期構成に含めず、上記のサンプルで動作確認します。

## 動作確認済み環境

いずれも2026-09-12に、MCP SDK 1.30.0 / tableauhyperapi 0.0.26558で確認しました。

- Windows / Python 3.14.3
  サンプル生成、stdio接続、3つのtool、対象外パスと行数上限の拒否。
- WSL2 Ubuntu 24.04 / Python 3.12.3
  上記に加えて、Claude Codeからの3つのtool呼び出し、ロック競合時のエラー、Windows側へコピーしたHyperファイルの読み取り。

Windows側へコピーしたサンプルをTableau Desktop 2026.2で開き、3行の値がMCPの戻り値と一致することを確認しました。承認後の`claude mcp list`が`tableau-local`を`Connected`と表示することも確認しています。

2026-09-12にChatGPT Work向けの公式接続方式も確認しました。Secure MCP TunnelはローカルMCPへのstdio接続に対応するため、サーバのHTTP化は不要と判断しました。ChatGPT Workの管理された作業環境内では、独立したMCPクライアントからstdio接続し、3つのtoolの検出と`list_hyper_files`の呼び出しまで確認しました。ただし、この環境ではHyperプロセスのローカルソケット作成が`Operation not permitted`で拒否されたため、サンプル生成とChatGPT WorkからのTunnel経由の3 tool呼び出しは未確認です。完了確認は、上記手順をローカルWindowsで実行して行います。

## 参考

- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Hyper API](https://tableau.github.io/hyper-db/docs/)
- [Hyperファイルの読み取り](https://tableau.github.io/hyper-db/docs/guides/hyper_file/read/)
- [Hyper接続とファイルロック](https://tableau.github.io/hyper-db/docs/hyper-api/connection/)

今後の予定は[ROADMAP.md](ROADMAP.md)を参照してください。
