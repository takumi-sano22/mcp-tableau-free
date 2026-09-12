---
name: tableau-analysis
description: "Tableauを使った分析を進めるスキル。データを.hyperへ渡す、ワークブック（.twb/.twbx）をコードから生成する、公式の操作手順を調べて案内する作業で使う。Tableau、Hyper、.twb、.twbx、ダッシュボード、ワークシート、データソース、Tableauで可視化、といった話題で必ずトリガーすること。"
---

# Tableau分析スキル

Tableauを使った分析を、実測結果を優先しながら進める。データの受け渡し、ワークブックの生成、操作手順の案内を扱う。

ユーザーの明示的な指示を最優先し、このスキルから作業範囲を勝手に広げない。

## 最初に確認する

1. **Tableauの版と動作環境**。WSLから使う場合、Tableau本体はWindows側にある。版によってワークブックの受け入れ構造が変わるため、版を確かめずに生成を始めない。実行環境からユーザーのPCを確認できなければ質問する。
2. **データの置き場所**。Tableauが開くファイルはWindowsから見えるパスに要る。Tableauは`.hyper`を排他するため、MCPなどから同時に読むなら実体を2箇所に分ける。
3. **何を見たいのか**。シートの構成は分析の問いから決まる。`references/analysis-recipes.md`の型に当てはめてから設計する。

ChatGPT Workの実行環境とユーザーのローカルWSLは別環境である。ローカルファイルやコマンドを確認したと、tool結果なしに主張しない。`tableau-local`のtoolが使える場合だけ、Tunnel経由でローカルHyperを確認する。

## 鉄則: 実機の出力を正とする

Tableauのワークブック形式は公開仕様と実装が食い違う。公式XSDを通したワークブックがTableauで開けないことを実測している。構文検証は最低限の足切りとしてだけ使い、正しい構造は必ず実機が書き出したファイルから取る。

推測でXMLを書かない。対象環境で雛形を1つ作り、その骨格を流用する。

## 何をするとき、どれを読むか

| やること | 読むreference |
| --- | --- |
| データをTableauへ渡す（Hyper生成・型・排他・MCPでの確認） | `references/data-handoff.md` |
| ワークブック（.twb/.twbx）をコードから生成する | `references/workbook-generation.md` |
| 分析の問いからシート構成を決める | `references/analysis-recipes.md` |
| Tableauの操作手順・仕様を調べて案内する | `references/official-sources.md` |
| プロジェクト固有の対象データ・手順 | `references/projects/<project>/README.md`（無ければ作る。書き方は`references/projects/README.md`） |

## 同梱物

| ファイル | 用途 |
| --- | --- |
| `scripts/build_hyper.py` | CSV群を型を明示して`.hyper`へ格納する |
| `scripts/validate_twb.py` | 公式XSDで`.twb`を構文検証する。通っても開ける保証はない |
| `scripts/build_workbook_from_template.py` | 実機の雛形を土台に`.twb` / `.twbx`を組み立てる実装例。先頭の設定ブロックを対象に合わせて書き換える |
| `assets/ref-dashboard-2026.2.twb` | Tableau 2026.2が書き出した構造参照用の実物。生成用の雛形は対象環境で取り直す |

## 進め方の既定

1. 分析の問いを決め、`analysis-recipes.md`でシート構成を先に決める。
2. long形式のテーブルを設計し、CSVから`.hyper`にする（`data-handoff.md`）。
3. `tableau-local`が使えるなら、`list_hyper_files`、`list_hyper_tables`、`preview_hyper_table`の順で内容を確認する。
4. ワークブックを作るなら、まず実機の雛形を取る（`workbook-generation.md`）。
5. 雛形の骨格を流用して生成し、構造を雛形と比較して検証する。
6. ユーザーに実機で開いてもらい、結果を確認する。

## プロジェクト固有の内容

このスキルの正本は[mcp-tableau-free](https://github.com/takumi-sano22/mcp-tableau-free)にある。プロジェクト固有の内容は`references/projects/<name>/`にだけ置き、汎用の作法を固有の事情で上書きしない。
