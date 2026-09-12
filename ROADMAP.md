# ロードマップ

ローカルの Tableau Desktop 無料版とローカルファイルの範囲で、AI から Tableau 分析を
進められる状態を目指します。期限は設けず、必要になったものを順に追加します。

## 1. ローカル Hyper 用 MCP サーバ

- [x] Python の最小 stdio MCP サーバ
- [x] Hyper ファイル一覧・テーブル一覧・行プレビュー tool
- [x] 架空データ生成と MCP 接続設定例
- [x] Claude Code（WSL / Windows）から tool を呼ぶ
- [x] ファイルロックの挙動と回避策を記録する
- [ ] Windows 側の文字コード・パスまわりの注意点を記録する
- [ ] 列の型・件数・基本集計を返す tool を必要に応じて追加する

2026-09-12 の確認でわかったことです。

- WSL 上の Python 3.12 でもサーバは動き、Claude Code からプロジェクト設定（`.mcp.json`）経由で 3 つの tool を呼べた
- Hyper ファイルは読み取りだけでもプロセス間で排他されるため、Tableau と同じファイルを同時に開けない。比較にはコピーを使う
- 行プレビューの戻り値だけでは、返った行数が全件か上限かを区別できない。件数を返す手段があると比較しやすい
- Windows 側へコピーしたサンプルを Tableau Desktop で開けば、MCP の戻り値と同じ 3 行を並べて確認できる

## 2. Tableau 分析スキル

- [x] データ受け渡し・ワークブック生成・シート設計・公式情報の調べ方を reference 化
- [x] 実機の雛形を土台にワークブックを生成する手順と実装例
- [x] ChatGPT / Codex 用 Plugin に provider-neutral な `tableau-analysis` Skill を同梱する
- [x] ChatGPT Work 向けの接続・実測手順を `tableau-local-mcp` Skill にする
- [ ] ChatGPT Work で Plugin の明示・暗黙トリガーを実機確認する
- [ ] 雛形に無い構文（複数値フィルタ・リファレンスライン）を実機から取り直して追記する
- [ ] `.twbx` 生成の確認結果を版ごとに記録する

わかっていることです。

- Tableau のワークブック形式は公開仕様（公式 XSD）と実装が食い違う。XSD を通ったファイルが開けない例を実測している
- そのため、正しい構造は必ず実機が書き出した `.twb` から取る。推測で XML を書くと往復が増える
- 版が変われば構造も変わる。雛形は対象環境で取り直す

## 3. MCP クライアントの比較

- [x] Claude Code（WSL / Windows）から3つの tool を呼ぶ
- [x] ChatGPT Work の公式接続方式が Secure MCP Tunnel であることを確認する
- [x] Tunnel がローカル stdio MCP を扱えるため、HTTP 化が不要と判断する
- [x] 認証情報・Hyper・個人環境の絶対パスを含めない接続手順と Skill Plugin を追加する
- [x] 管理された実行環境で stdio 接続、3 tool の検出、`list_hyper_files` 呼び出しを確認する
- [ ] ローカル WSL で `tunnel-client doctor` と `run` を確認する
- [ ] ChatGPT Work から3つの tool を呼ぶ
- [ ] `sample.hyper` の東京 1200・大阪 900・福岡 600 を ChatGPT Work の戻り値で確認する
- [ ] ChatGPT Work で `tableau-analysis` / `tableau-local-mcp` Skill の起動を確認する

Secure MCP Tunnel はローカルの stdio MCP へ接続できるため、このサーバを HTTP 化する必要はありません。Tunnel は WSL から OpenAI へ外向き HTTPS で接続し、認証なしの受信ポートは公開しません。

ChatGPT Work の管理された実行環境では、独立した MCP クライアントから3つの tool を検出し、空のデータディレクトリに対して `list_hyper_files` を呼べるところまで確認しました。同環境では Hyper プロセスのローカルソケット作成が拒否され、ユーザーの WSL 上で Tunnel を起動することもできないため、残りは未確認です。完了条件を推測で満たした扱いにはしません。


## 4. ローカル Tableau 資産への拡張

- [ ] `.twb` からデータソース・シート構成を読む
- [ ] `.twbx` の内容を安全に確認する
- [ ] 必要が生じた場合に、読み取り SQL の許可範囲・制限時間・出力量を設計する

画面操作やワークブックへの書き込みは別の題材として扱い、必要性を確認してから着手します。
Tableau Cloud / Server 向けの API（Tableau REST API 等）は対象外です。無料版の範囲で完結させます。
