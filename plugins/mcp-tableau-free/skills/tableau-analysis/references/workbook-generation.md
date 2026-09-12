# ワークブック（.twb / .twbx）をコードから生成する

> Tableau Desktop 2026.2（Windows）で実測した内容。版が変われば構造も変わるため、
> **本書の個別の値をそのまま信じず、必ず対象環境の実機出力で確かめること。**

## 目次

- [鉄則](#鉄則)
- [手順](#手順)
- [雛形の取り方](#雛形の取り方)
- [骨格の境界](#骨格の境界)
- [ファイル構造の要点](#ファイル構造の要点)
- [未検証の構文を避ける設計](#未検証の構文を避ける設計)
- [エラーの読み方](#エラーの読み方)
- [実測した失敗の記録](#実測した失敗の記録)

## 鉄則

**ゼロから XML を書かない。実機が書き出したファイルを土台に加工する。**

理由は、Tableau のワークブック形式が公開仕様と実装で食い違うため。公式 XSD
（`github.com/tableau/tableau-document-schemas`）を通したファイルが Tableau で開けない
ことを二度実測している。XSD は「最低限の足切り」にしかならない。

副次的な効果として、**実機が書いた構文だけを使えば、未知の要素・属性を推測せずに済む**。
生成できる図の幅は狭まるが、開けないファイルを何度も渡すより速い。

## 手順

1. 対象環境の Tableau の版を確認する（`ls "/mnt/c/Program Files/Tableau/"`）
2. **実機で雛形を1つ作ってもらう**（下記テンプレート）
3. 雛形から骨格を切り出し、`worksheets` 以降だけを生成する
4. 生成物を雛形と構造比較して検証する（要素の並び・数・列定義）
5. ユーザーに開いてもらう

3〜5 の実装例が `scripts/build_workbook_from_template.py` にある。先頭の設定ブロック
（雛形のパス・テーブル名・列定義・シート定義）を対象に合わせて書き換えて使う。

## 雛形の取り方

雛形には**これから使う要素を全部含めてもらう**。1回で済ませるため、依頼内容を先に設計する。
シート1枚だけの雛形ではフィルタもダッシュボードも取れず、往復が増える。

依頼テンプレート:

```
1. Tableau で対象の .hyper に接続 → 使うテーブルを選ぶ
2. シート1（フィルタとマーク種別を取る）
   - 列・行・色にフィールドを置く
   - 絞り込みに使う列をフィルタへドラッグし、1つだけチェックする
   - マークを「線」に変更
3. シート2（複数シートと別マークを取る）
   - 同様に置き、マークは「棒」
4. ダッシュボードを新規作成し、シート2枚を並べる
5. 名前を付けて保存（.twb 形式）
```

**取れるもの**: workbook ルートの属性 / `document-format-change-manifest` /
`preferences` / データソース定義（接続文字列・`metadata-records`・`object-graph`）/
worksheet の構造 / フィルタ構文 / ダッシュボードの `zones` と `devicelayouts` / `windows`。

## 骨格の境界

雛形の**先頭から `</datasources>` まで**を、そのまま流用するのが安全。

```python
head = ref[:ref.index("  </datasources>") + len("  </datasources>")]
```

この範囲に含まれるもの:

- workbook ルート（`version` / `source-build` / 名前空間宣言 / フィンガープリント属性）
- `document-format-change-manifest` — **先頭に必須**。これが無いと Tableau は古い世代の
  content model で検証し、`simple-id` すら弾く
- `preferences`
- `datasources`（接続・`metadata-records`・列定義・`layout` / `semantic-values` / `object-graph`）

差し替えが要るのは次の3つだけ:

| 差し替える | 方法 |
| --- | --- |
| `dbname` | `.twbx` なら `Data/Datasources/<name>.hyper`、単体 `.twb` なら Windows の絶対パス（`C:/...` とスラッシュ区切り） |
| `metadata-records` | 列を増減したら再生成する（下記の型対応表） |
| `datasource` 直下の `column` 群 | 同上。caption のアルファベット順に並ぶ |

`worksheets` / `dashboards` / `windows` は丸ごと生成する。`thumbnails` は optional なので省く
（古いシート名のサムネイルが残るため、むしろ省いたほうがよい）。

## ファイル構造の要点

### workbook の version は製品バージョンではない

```xml
<workbook source-build='2026.2.2 (20262.26.0819.2015)' source-platform='win' version='18.1' ...>
```

**2026.2 の実機が書き出す `version` は `18.1`。** XSD のファイル名（`twb_2026.2.0.xsd`）に
引きずられて `26.2` と書くと、Tableau は別世代の content model を当てて失敗する
（`mark` に `type` 必須、`worksheet-number` 必須、などと言われる）。

### workbook 直下の要素順

```
document-format-change-manifest, repository-location?, preferences, style-theme?, style,
local-data?, datasources?, datasource-relationships?, mapsources?, shared-views?, actions?,
worksheets?, dashboards?, windows, thumbnails?, external?
```

`windows` は必須。`explain-data` はこの content model に**存在しない**（公式 XSD にはある）。

### metadata-records の型対応

| データ型 | `remote-type` | `local-type` | `aggregation` | `collation` |
| --- | --- | --- | --- | --- |
| 文字列 | 129 | string | Count | あり（`<collation flag='0' name='binary' />`） |
| 整数 | 20 | integer | Sum | なし |
| 実数 | 5 | real | Sum | なし |

`ordinal` はテーブルの列順（0始まり）。`object-id` はテーブル単位で同じ値を使う。
`approx-count` は統計値なので概算でよい（Tableau が接続時に更新する）。

### フィールドの内部名

- 離散ディメンション: `[none:<column>:nk]`
- 集計メジャー: `[sum:<column>:qk]` / `[avg:<column>:qk]`
- 参照は `[<datasource-name>].[none:<column>:nk]` の形

`datasource-dependencies` に、そのシートで使う `column` と `column-instance` を**両方**宣言する。

### フィルタ

```xml
<filter class='categorical' column='[DS].[none:track:nk]'>
  <groupfilter function='member' level='[none:track:nk]' member='&quot;値&quot;'
               user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />
</filter>
<slices>
  <column>[DS].[none:track:nk]</column>
</slices>
```

- `member` の値は `"` で囲み、XML 属性としてエスケープする
- **`user:ui-*` 属性が付く**（`xmlns:user` はルートで宣言済み）
- **`<slices>` でフィルタ対象の列を宣言する**
- 単一値なら `union` で包まない

### ダッシュボード

```
(((layout-options?)|(repository-location?)),style,size?,datasources,datasource-dependencies*,zones,devicelayouts)
```

`style` / `zones` / `devicelayouts` が要る。`zones` は入れ子で、外側が
`type-v2='layout-basic'`、内側が `type-v2='layout-flow'`（`param='vert'` / `'horz'`）。
シートを置く zone は `name` にワークシート名を指定する。座標は 100000 を全体とする相対値。

`devicelayouts` には `<devicelayout auto-generated='true' name='Phone'>` を1つ入れる。

### simple-id

`worksheet` / `dashboard` / `window` それぞれの**末尾**に置く。
形式は `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`（中括弧付き・大文字）。

## 未検証の構文を避ける設計

雛形に出てこなかった構文が必要になったら、**XML を推測する前に、データ側で解決できないか
考える**。生成の失敗はユーザーに開かせる往復を生むが、データの作り直しは自動で完結する。

実例: 「軸を3つ選ぶ」フィルタ（複数値）の構文が雛形に無かったとき、テーブルに
`axis_group` 列（主要3軸／安全ガード／フラグ）を足して、**単一値フィルタだけで**同じ
絞り込みを実現した。

同様に、**複数テーブルを1つのデータソースに寄せられないか**も検討する。雛形が1テーブルの
場合、別テーブル用の `metadata-records` を手で書く必要が出る。件数のような別スケールの値でも、
シートを分けるなら同じテーブルに合流させてよい（その場合は集計方法をドキュメントに明記する）。

## エラーの読み方

Tableau の読み込みエラーは**行番号・桁と content model** を返す。これは正解の構造を
直接教えてくれる、最も価値のある情報源。

```
Error(96,17): element 'simple-id' is not allowed for content model
              '(((layout-options?)|(repository-location?)),table)'
```

- 行番号が生成ファイルの行数を超えている場合、それは **Tableau 内部スキーマ側の警告**で
  自分のファイルとは無関係（例: `group 'Sort-G' must contain all, choice, or sequence compositor`）
- `?` が付かない要素は必須。順序も content model のとおり
- `missing required attribute` は、その要素に属性が足りない

## 実測した失敗の記録

同じ轍を踏まないための記録。いずれも「推測で書いた」ことが原因。

| 失敗 | 症状 | 真因 |
| --- | --- | --- |
| `version='26.2'` と宣言 | `mark` に `type` 必須・`worksheet-number` 必須と言われる | XSD のファイル名を製品バージョンと混同した。実機は `18.1` |
| `document-format-change-manifest` を省略 | `simple-id` / `explain-data` が「許可されていない」 | 古い世代の content model が当てられた |
| 公式 XSD の検証だけで判断 | XSD は通るのに Tableau が開かない | 公開仕様と実装が食い違う。XSD に無い属性（`mark` の `type`）を実装が要求する |
| ダッシュボードを推測で記述 | `datasources` と `devicelayouts` が無いと言われる | 雛形にダッシュボードを含めていなかった |
