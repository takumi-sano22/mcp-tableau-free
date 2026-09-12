---
name: tableau-local-mcp
description: "ChatGPT Workからmcp-tableau-freeのローカルTableau HyperをSecure MCP Tunnel経由で安全に確認するスキル。Tableau MCP、ChatGPT Work、Secure MCP Tunnel、tunnel-client、sample.hyper、MCP接続確認、toolが見つからない・呼べない、といった依頼で使う。"
---

# Tableau Local MCP

ChatGPT Workから、ユーザーのローカルWSLで動く読み取り専用MCPを安全に使い、実際のtool結果まで確認する。

## 境界

- ChatGPT Workの実行環境とユーザーのWSLは別環境。WSL上のコマンド実行やファイル確認を、結果なしに完了扱いしない。
- MCPサーバを認証なしで外部公開しない。受信ポートを開けず、Secure MCP Tunnelの外向きHTTPSを使う。
- runtime API key、`tunnel_id`、ローカルHyper、個人環境の絶対パスを会話外へ転記したり、リポジトリへ保存したりしない。
- このMCPは読み取り専用。任意SQL、Tableau GUI操作、ワークブック編集を行わない。
- ユーザーの明示的な指示を最優先し、接続設定の作成や公開範囲を勝手に広げない。

## 接続前

`list_hyper_files`、`list_hyper_tables`、`preview_hyper_table`が現在の会話で利用可能か確認する。

利用できなければ、`references/chatgpt-work-setup.md`を読み、次のどこまで確認済みかを切り分ける。

1. WSLでサンプル生成とstdio MCPの単体確認
2. Tunnelの権限・workspace関連付け
3. `tunnel-client doctor`と`run`
4. ChatGPT Pluginsでのdeveloper-mode接続
5. 会話のtoolsメニューで接続を有効化

ユーザーのWSLでしか実行できない手順は、貼り付け可能なコマンドを示して結果を依頼する。

## Hyper確認

toolが利用できる場合は、必ず次の順で呼ぶ。

1. `list_hyper_files()`を呼び、実際に返ったファイル名を記録する。
2. `sample.hyper`があれば`list_hyper_tables(filename="sample.hyper")`を呼ぶ。
3. 戻ったスキーマ名・テーブル名をそのまま使い、`preview_hyper_table(filename="sample.hyper", schema="Extract", table="Sales", limit=10)`を呼ぶ。
4. `region`と`sales`の組を順不同で比較し、東京1200・大阪900・福岡600の3行が実際の戻り値に含まれるか報告する。

期待値をtool結果として捏造しない。1つでも呼べなければ、成功した最後の境界、エラー、次に必要な操作を明記する。

## 典型的な失敗

- `sample.hyper`がない: WSLのリポジトリ直下で`./.venv/bin/python examples/create_sample_hyper.py`を実行してもらう。
- ロック競合: Tableau Desktopなどで同じHyperを閉じるか、MCP用とTableau用にコピーを分ける。
- toolが見つからない: `tunnel-client run`が継続中か、ChatGPT側で接続を有効にしたかを確認する。
- Tunnelが一覧にない: 対象ChatGPT workspaceとの関連付けとTunnels Read + Use権限を確認する。

最終報告では「確認済み」「未確認」「次の手順」を分ける。
