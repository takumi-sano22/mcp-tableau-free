# ChatGPT Work接続手順

この手順は、`mcp-tableau-free`をclone済みのWSLで実行する。ChatGPT Workの実行環境内ではなく、ローカルWSLのシェルを使う。

## 1. stdio MCPを先に確認する

リポジトリ直下で実行する。

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[tableau]"
./.venv/bin/python examples/create_sample_hyper.py
```

`data/sample.hyper`ができたことを確認する。既存のClaude Code接続がある場合は、`.mcp.json`を変更せず、そのまま動作確認に使える。

## 2. Tunnelの前提を確認する

必要なものは次のとおり。

- Platform tunnel settingsで作成した`tunnel_id`
- `tunnel-client`用のruntime API key
- Tunnelに対するTunnels Read + Use権限。Tunnelを作成・編集する人はRead + Manageも必要
- ChatGPT workspaceでのdeveloper mode利用権限
- Tunnelと対象ChatGPT workspaceの関連付け
- WSLから`api.openai.com:443`への外向きHTTPS

runtime API keyと`tunnel_id`はリポジトリへ保存しない。profileもリポジトリ外で管理する。

## 3. WSLでtunnel-clientを起動する

Platform tunnel settingsから、WSLのCPUアーキテクチャに合う最新の`tunnel-client`を取得する。リポジトリ直下で、値を実環境のものへ置き換えて実行する。

```bash
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

`run`はChatGPTからの確認中も起動したままにする。MCPはstdioのままでよく、HTTP化や受信ポートの開放は不要。

## 4. ChatGPT Workへ接続する

1. ChatGPTのSettings → Security and loginでDeveloper modeを有効にする。
2. ChatGPT Pluginsで追加ボタンを選び、developer-mode appを作る。
3. ConnectionでTunnelを選び、対象Tunnelまたは`tunnel_id`を指定する。
4. 検出された3つのtool名と引数を確認する。
5. 新しい会話で接続と、このPluginのSkillを有効にする。
6. `sample.hyperの中身を確認して`と依頼する。

Tunnelが表示されなければ、Platform organizationだけでなく対象ChatGPT workspaceにも関連付けられているか、実行者にTunnels Read + Useがあるかを確認する。

## 5. 完了判定

次をすべて実測できたときだけ完了とする。

- `list_hyper_files()`が`sample.hyper`を返す
- `list_hyper_tables(filename="sample.hyper")`が`Extract` / `Sales`を返す
- `preview_hyper_table(...)`が東京1200・大阪900・福岡600を返す

値の並び順は保証されないため、行は順不同で比較する。失敗時は`doctor`の結果、ChatGPTの接続状態、成功した最後のtoolを記録する。

## 公式情報

- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [Connect and test your plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Build skills](https://developers.openai.com/plugins/build/skills)
