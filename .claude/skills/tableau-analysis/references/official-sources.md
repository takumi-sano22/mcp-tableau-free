# 公式の仕様・操作手順を調べて案内する

Tableau は版によってメニュー名・ファイル形式・受け入れ構造が変わる。**記憶だけで
操作手順や仕様を断定しない。** 特にファイル形式と、版に依存する挙動は必ず裏を取る。

## 情報源の優先順位

1. **対象環境の実機**（最優先）。インストール済みの版が何を出力し、何を受け入れるかが最終的な正
2. **公式ドキュメント**（`help.tableau.com`）— 操作手順・機能の仕様
3. **公式スキーマ**（`github.com/tableau/tableau-document-schemas`）— `.twb` の XSD。版ごとに
   `schemas/<YYYY>_<R>/twb_<YYYY>.<R>.0.xsd`
4. 第三者の記事・GitHub 上の実ファイル — 補助。**版が古いことが多い**ので鵜呑みにしない

**2〜4 が 1 と食い違ったら 1 を採る。** 公式 XSD を通ったワークブックが実機で開けない、という
食い違いを実測している（`workbook-generation.md` 参照）。

## 環境を実測する

案内する前に、まず対象環境を確かめる。

```bash
ls "/mnt/c/Program Files/Tableau/"            # 入っている版
ls "/mnt/c/Program Files/Tableau/Tableau <版>/"  # 同梱物（サンプル・既定値）
ls "/mnt/c/Users/<user>/Documents/My Tableau Repository/"  # 保存先・既定のリポジトリ
```

同梱サンプルワークブックがあれば、それが最良の構造リファレンスになる（版によっては
同梱されない）。`My Tableau Repository` は Tableau を一度起動するまで作られない。

## 公式 XSD の使い方と限界

```bash
curl -sL -o twb.xsd https://raw.githubusercontent.com/tableau/tableau-document-schemas/main/schemas/2026_2/twb_2026.2.0.xsd
```

そのままでは lxml で読み込めない。外部名前空間（`user:` / `xml:`）の参照が解決できないため、
その参照行だけ落としてから使う。

```python
drop = ('user:UserAttributes-AG', 'ref="xml:base"')
kept = [l for l in lines if not any(d in l for d in drop)]
```

**XSD が保証するのは構文だけ。**「通ったから開ける」とは言えない。逆に「通らないなら
確実に開けない」ので、足切りとしては有効。

## 操作手順を案内するときの書き方

- **版を明記する**（「2026.2 の場合」）。メニュー名は版で変わる
- メニューは階層を省かず書く（「ファイル → 名前を付けて保存 → ファイルの種類」）
- 保存形式のように選択肢がある箇所は、既定値と選ぶべき値の両方を書く
- 実機で確認できない部分は**確認できないと明示する**。GUI の挙動は CLI からは検証できない

## 実物を探す

構造の実例が要るとき、GitHub のコード検索で実ファイルを探せる。

```
"<mark class=" "type=" extension:twb
```

ただし公開されている `.twb` は古い版のものが多く、**新しい版の構造は見つからない**前提で
探す。見つからなければ、実機で雛形を作ってもらうのが最短（`workbook-generation.md`）。
