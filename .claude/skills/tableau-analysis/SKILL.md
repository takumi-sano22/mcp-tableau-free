---
name: tableau-analysis
description: "Tableau を使った分析を進めるスキル。データを .hyper へ渡す、ワークブック（.twb/.twbx）をコードから生成する、公式の操作手順を調べて案内する作業で使う。Tableau、Hyper、.twb、.twbx、ダッシュボード、ワークシート、データソース、Tableau で可視化、といった話題で必ずトリガーすること。「Tableau で可視化して」「ダッシュボードを作って」「Hyper ファイルを作って」「Tableau の操作を教えて」といったリクエストでも使用する。"
---

# Tableau 分析スキル

Tableau を使った分析を、AI 側で可能な限り自動化して進めるためのスキル。
データの受け渡し・ワークブックの生成・操作手順の案内を扱う。

## 最初に確認する（毎回）

1. **Tableau の版と動作環境**。WSL から使う場合、Tableau 本体は Windows 側にある。
   `ls "/mnt/c/Program Files/Tableau/"` で版を確認する。**版によってワークブックの
   受け入れ構造が変わる**ため、版を確かめずに生成を始めない。
2. **データの置き場所**。Tableau が開くファイルは Windows から見えるパスに要る。
   WSL 上のファイルは `\\wsl.localhost\<distro>\...` でも見えるが、**Tableau が
   `.hyper` を排他する**ため、MCP などから同時に読むなら実体を2箇所に分ける。
3. **何を見たいのか**。シートの構成は分析の問いから決まる。先にテーブル設計をすると
   作り直しになる。`references/analysis-recipes.md` の型に当てはめてから設計する。

## 鉄則: 実機の出力を正とする

**Tableau のワークブック形式は公開仕様と実装が食い違う。** 公式 XSD（`tableau-document-schemas`）
を通したワークブックが Tableau で開けないことを実測している。構文検証は「最低限の足切り」として
だけ使い、**正しい構造は必ず実機が書き出したファイルから取る**。

推測で XML を書くと、ユーザーに何度も開かせて往復することになる。**雛形を1つ作ってもらう
コスト（2〜3分）のほうが、推測の試行錯誤よりはるかに安い。**

## 何をするとき、どれを読むか

| やること | 読む reference |
| --- | --- |
| データを Tableau へ渡す（Hyper 生成・型・排他・MCP での確認） | `references/data-handoff.md` |
| ワークブック（.twb/.twbx）をコードから生成する | `references/workbook-generation.md` |
| 分析の問いからシート構成を決める | `references/analysis-recipes.md` |
| Tableau の操作手順・仕様を調べて案内する | `references/official-sources.md` |
| プロジェクト固有の対象データ・手順 | `references/projects/<project>/README.md`（無ければ作る。書き方は `references/projects/README.md`）。同じディレクトリに固有のスクリプトも置く |

## 同梱スクリプト

| スクリプト | 用途 |
| --- | --- |
| `scripts/build_hyper.py` | CSV 群を型を明示して `.hyper` へ格納する |
| `scripts/validate_twb.py` | 公式 XSD で `.twb` を構文検証する（**通っても開ける保証は無い**）。`lxml` が要る |
| `scripts/build_workbook_from_template.py` | 実機の雛形を土台に `.twb` / `.twbx` を組み立てる**実装例**。先頭の設定ブロック（雛形のパス・列定義・シート定義）を対象に合わせて書き換えて使う。そのままでは動かない |

## 同梱アセット

| アセット | 用途 |
| --- | --- |
| `assets/ref-dashboard-2026.2.twb` | Tableau 2026.2 が書き出した実物（シート2枚＋ダッシュボード＋フィルタ）。作成者 ID・マシン ID・パス・フィルタ値は伏せ、サムネイル画像は除いてある（データソースの内部 ID は残る）。**構造の参照用**であり、生成に使う雛形は対象環境で取り直すこと（版が違えば構造も違う） |

## 進め方の既定

1. 分析の問いを決め、`analysis-recipes.md` でシート構成を先に決める
2. long 形式のテーブルを設計し、CSV → `.hyper` にする（`data-handoff.md`）
3. MCP（`tableau-local` 等）が使えるなら、Hyper の中身を読んで内容を確認する
4. ワークブックを作るなら、**まず実機の雛形を取る**（`workbook-generation.md`）
5. 雛形の骨格を流用して生成し、構造を雛形と比較して検証する
6. ユーザーに開いてもらい、結果を確認する

## 置き場所とプロジェクト固有の内容

このスキルの正本は [mcp-tableau-free](https://github.com/takumi-sano22/mcp-tableau-free) リポジトリにある。
利用時は `~/.claude/skills/`（全プロジェクトで使う）か、対象リポジトリの `.claude/skills/`
（そのリポジトリだけで使う）へコピーする。同名なら project 側が優先される。

**プロジェクト固有の内容は `references/projects/<name>/` にだけ置く。** 汎用の作法を
固有の事情で上書きしない。書き方は `references/projects/README.md` を参照する。

global と project の両方に同じスキルを置いた場合、**読まれるのは project 側**になる。
固有ファイルだけを参照したいときは、リポジトリのパスで直接 Read する。
