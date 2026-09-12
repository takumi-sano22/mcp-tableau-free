#!/usr/bin/env python3
"""実機の雛形を土台に Tableau ワークブック（.twb / .twbx）を組み立てる実装例。

**そのままでは動かない。** 下の「設定」を対象のデータ・雛形に合わせて書き換えて使う。
汎用ツールではなく、references/workbook-generation.md の手順をコードに落とした参照実装。

公式 XSD を通しても Tableau は開かない（読み込み時の content model が別）ことを実測したため、
骨格（document-format-change-manifest / preferences / datasources）は実機が書いた雛形から取り、
worksheets 以降だけを生成する。使う XML 構文も雛形に出現したものに限る。

雛形の取り方は references/workbook-generation.md「雛形の取り方」を参照。
雛形は**対象環境の Tableau で取り直す**こと（版が違えば構造が違う）。
"""

import csv
import re
import sys
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

# ---------------------------------------------------------------------------
# 設定：ここから下を対象に合わせて書き換える
# ---------------------------------------------------------------------------

OUT_DIR = Path(__file__).resolve().parent / "out"

# 実機で作った雛形（.twb）。これが構造の正本になる。
REF = Path("/mnt/c/Users/<user>/Documents/<workdir>/ref-dash.twb")

# 生成対象のテーブル。雛形で接続したテーブルと同じ名前にする。
TABLE = "axis_scores"

# シート内に出るデータソースの表示名。雛形の綴りに合わせる（Tableau の言語設定で変わる）。
DS_CAPTION = "{} 抽出".format(TABLE)

# 列定義の approx-count を数えるための CSV（.hyper の元データ）。
CSV_PATH = Path("/tmp/<workdir>/axis_scores.csv")

# .twbx へ同梱する .hyper の実体。
HYPER = Path("/home/<user>/<workdir>/sample_quality.hyper")

# .twbx 内でのデータソースのパス（この綴りで固定）。
HYPER_IN_ZIP = "Data/Datasources/sample_quality.hyper"

# 単体 .twb で使う場合の、Tableau から見た .hyper の絶対パス（Windows・スラッシュ区切り）。
HYPER_WIN_ABS = "C:/Users/<user>/Documents/<workdir>/sample_quality.hyper"

# 列の並びは .hyper の定義と一致させる（ordinal がずれると metadata が食い違う）。
# (列名, Tableau 上の表示名, 型) の型は string / integer / real。
COLUMNS = [
    ("run_key", "Run Key", "string"), ("track", "Track", "string"),
    ("phase_label", "Phase Label", "string"), ("phase_seq", "Phase Seq", "integer"),
    ("judge_version", "Judge Version", "string"), ("compare_group", "Compare Group", "string"),
    ("condition", "Condition", "string"), ("axis", "Axis", "string"),
    ("axis_group", "Axis Group", "string"), ("score", "Score", "real"), ("n", "N", "integer"),
]

DASH_NAME = "ダッシュボード"

# シート定義。枚数は自由（ダッシュボードは 2 列で折り返す）。
# filters は (列名, 値) の単一値フィルタだけを使う。複数値フィルタの XML は雛形に出ないことが
# 多いため、絞り込みは列を足してデータ側で解決する
# （references/workbook-generation.md「未検証の構文を避ける設計」）。
SHEETS = [
    dict(name="① 主要指標の推移", mark="Line",
         cols="phase_label", rows="score", color="axis",
         filters=[("condition", "baseline"), ("axis_group", "主要3軸")]),
    dict(name="② 施策の前後比較", mark="Bar",
         cols="phase_label", rows="score", color="axis",
         filters=[("condition", "overall"), ("axis_group", "主要3軸")]),
    dict(name="③ ガード指標の維持", mark="Line",
         cols="phase_label", rows="score", color="axis",
         filters=[("condition", "baseline"), ("axis_group", "安全ガード")]),
    dict(name="④ フラグ件数の推移", mark="Bar",
         cols="phase_label", rows="score", color="axis",
         filters=[("condition", "baseline"), ("axis_group", "フラグ")]),
]

# ---------------------------------------------------------------------------
# ここから下は書き換え不要
# ---------------------------------------------------------------------------

# 雛形の metadata-record から読み取った型の対応。
TYPE_MAP = {"string": ("129", "string", "Count", True),
            "integer": ("20", "integer", "Sum", False),
            "real": ("5", "real", "Sum", False)}
ROLE_MAP = {"string": ("dimension", "nominal"), "integer": ("measure", "quantitative"),
            "real": ("measure", "quantitative")}

# ダッシュボードの座標系。雛形と同じく全体を 100000 とする相対値で、外周に余白を取る。
GRID_COLS = 2
AREA_X, AREA_Y, AREA_W, AREA_H = 483, 851, 99034, 98298


def q(t):
    """設定値を XML の属性・テキストへ入れる前に必ず通す。"""
    return escape(str(t), {'"': "&quot;", "'": "&apos;"})


def quuid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def sub1(pattern, replacement, text, **kw):
    """置換が1件も起きなかったら落とす。

    雛形の綴りが想定と違うと、re.sub は黙って無変換のまま通してしまい、
    古い列定義を含んだファイルが出力される。ここで気づけるようにする。
    """
    new, n = re.subn(pattern, lambda _m: replacement, text, count=1, **kw)
    if n != 1:
        sys.exit("雛形の構造が想定と違います（置換できませんでした）: {}".format(pattern))
    return new


if not REF.is_file():
    sys.exit("雛形が見つかりません: {}\n"
             "references/workbook-generation.md「雛形の取り方」の手順で、"
             "対象環境の Tableau から .twb を書き出してください。".format(REF))

ref = REF.read_text(encoding="utf-8")
DS = re.search(r"name='(federated\.[a-z0-9]+)'", ref).group(1)
OBJ_ID = re.search(r"<object-id>(.*?)</object-id>", ref).group(1)
# windows タグの属性（DPI・高さ）は実機依存なので、雛形のものをそのまま使う。
WINDOWS_ATTRS = re.search(r"<windows([^>]*)>", ref).group(1).strip()

# zone の id は重複しなければよい。雛形と同じく 3 から順に振る。
GRID_ROWS = [SHEETS[i:i + GRID_COLS] for i in range(0, len(SHEETS), GRID_COLS)]
_ids = iter(range(3, 3 + (len(SHEETS) + len(GRID_ROWS) + 4) * 3, 3))
SHEET_IDS = [next(_ids) for _ in SHEETS]
ROW_IDS = [next(_ids) for _ in GRID_ROWS]
OUTER_ID, VERT_ID, PHONE_OUTER_ID, PHONE_VERT_ID = (next(_ids) for _ in range(4))

# 列ごとのユニーク件数。metadata の approx-count に入れる（Tableau が接続時に更新する統計値）。
with open(CSV_PATH, encoding="utf-8") as fh:
    rows_csv = list(csv.DictReader(fh))
APPROX = {c: len({r[c] for r in rows_csv if r[c] != ""}) for c, _, _ in COLUMNS}


def metadata_records():
    out = []
    for i, (name, _, kind) in enumerate(COLUMNS):
        rt, lt, agg, has_collation = TYPE_MAP[kind]
        collation = "            <collation flag='0' name='binary' />\n" if has_collation else ""
        out.append("""          <metadata-record class='column'>
            <remote-name>{n}</remote-name>
            <remote-type>{rt}</remote-type>
            <local-name>[{n}]</local-name>
            <parent-name>[{tbl}]</parent-name>
            <remote-alias>{n}</remote-alias>
            <ordinal>{o}</ordinal>
            <local-type>{lt}</local-type>
            <aggregation>{agg}</aggregation>
            <approx-count>{ac}</approx-count>
            <contains-null>true</contains-null>
{col}            <object-id>{oid}</object-id>
          </metadata-record>""".format(n=q(name), rt=rt, o=i, lt=lt, agg=agg, tbl=q(TABLE),
                                       ac=APPROX[name], col=collation, oid=OBJ_ID))
    return "        <metadata-records>\n" + "\n".join(out) + "\n        </metadata-records>"


def column_defs():
    out = []
    # Tableau は datasource 直下の column を caption のアルファベット順に並べる。
    for name, caption, kind in sorted(COLUMNS, key=lambda c: c[1]):
        role, typ = ROLE_MAP[kind]
        out.append("      <column caption='{cap}' datatype='{dt}' name='[{n}]' role='{r}' type='{t}' />".format(
            cap=q(caption), dt=kind, n=q(name), r=role, t=typ))
    return "\n".join(out)


def inst(field, deriv="None"):
    """雛形に出てくる内部フィールド名の綴り。離散は nk、集計は qk。"""
    pre = {"None": "none", "Sum": "sum"}[deriv]
    kind = "qk" if deriv == "Sum" else "nk"
    return "[{}:{}:{}]".format(pre, q(field), kind)


def deps_and_filters(fields, filters):
    """使うフィールドの宣言・フィルタ・slices をまとめて作る。"""
    caption = {n: c for n, c, _ in COLUMNS}
    kinds = {n: k for n, _, k in COLUMNS}
    decls = []
    for f, deriv in sorted(fields.items()):
        role, typ = ROLE_MAP[kinds[f]]
        decls.append("            <column caption='{c}' datatype='{d}' name='[{f}]' role='{r}' type='{t}' />".format(
            c=q(caption[f]), d=kinds[f], f=q(f), r=role, t=typ))
        it = "quantitative" if deriv == "Sum" else "nominal"
        decls.append("            <column-instance column='[{f}]' derivation='{d}' name='{i}' pivot='key' type='{t}' />".format(
            f=q(f), d=deriv, i=inst(f, deriv), t=it))
    filt, slices = [], []
    for f, value in filters:
        # member は値を " で囲んだうえで、XML 属性としてもエスケープする（二重の引用）。
        filt.append("""          <filter class='categorical' column='[{ds}].{i}'>
            <groupfilter function='member' level='{i}' member='&quot;{v}&quot;' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />
          </filter>""".format(ds=DS, i=inst(f), v=q(value)))
        slices.append("            <column>[{ds}].{i}</column>".format(ds=DS, i=inst(f)))
    slice_xml = ""
    if slices:
        slice_xml = "\n          <slices>\n" + "\n".join(slices) + "\n          </slices>"
    return "\n".join(decls), "\n".join(filt), slice_xml


def worksheet(s):
    # 行は集計（Sum）、列と色は離散。フィルタで1行に絞られるなら Sum でも値はそのまま出る。
    fields = {s["cols"]: "None", s["color"]: "None", s["rows"]: "Sum"}
    for f, _ in s["filters"]:
        fields.setdefault(f, "None")
    decls, filt, slices = deps_and_filters(fields, s["filters"])
    return """    <worksheet name='{name}'>
      <table>
        <view>
          <datasources>
            <datasource caption='{cap}' name='{ds}' />
          </datasources>
          <datasource-dependencies datasource='{ds}'>
{decls}
          </datasource-dependencies>
{filt}{slices}
          <aggregation value='true' />
        </view>
        <style />
        <panes>
          <pane selection-relaxation-option='selection-relaxation-allow'>
            <view>
              <breakdown value='auto' />
            </view>
            <mark class='{mark}' />
            <encodings>
              <color column='[{ds}].{color}' />
            </encodings>
          </pane>
        </panes>
        <rows>[{ds}].{rows}</rows>
        <cols>[{ds}].{cols}</cols>
      </table>
      <simple-id uuid='{uid}' />
    </worksheet>""".format(name=q(s["name"]), ds=DS, decls=decls, filt=filt, slices=slices,
                           mark=s["mark"], cap=q(DS_CAPTION), color=inst(s["color"]),
                           rows=inst(s["rows"], "Sum"), cols=inst(s["cols"]), uid=quuid())


def zone_style(margin):
    return """<zone-style>
                  <format attr='border-color' value='#000000' />
                  <format attr='border-style' value='none' />
                  <format attr='border-width' value='0' />
                  <format attr='margin' value='{}' />
                </zone-style>""".format(margin)


def dashboard():
    # 外側 basic → 縦 flow → 横 flow（1行ぶん）、という雛形と同じ入れ子にする。
    # シート枚数は自由。2 列で折り返し、最後の行が1枚なら横幅いっぱいに広げる。
    row_h = AREA_H // len(GRID_ROWS)
    rows_xml = []
    for r, row in enumerate(GRID_ROWS):
        cell_w = AREA_W // len(row)
        y = AREA_Y + r * row_h
        cells = []
        for c, s in enumerate(row):
            cells.append("""              <zone h='{h}' id='{id}' name='{name}' w='{w}' x='{x}' y='{y}'>
                {style}
              </zone>""".format(h=row_h, id=SHEET_IDS[r * GRID_COLS + c], name=q(s["name"]),
                                w=cell_w, x=AREA_X + c * cell_w, y=y, style=zone_style(4)))
        rows_xml.append("""            <zone h='{h}' id='{id}' param='horz' type-v2='layout-flow' w='{w}' x='{x}' y='{y}'>
{cells}
            </zone>""".format(h=row_h, id=ROW_IDS[r], w=AREA_W, x=AREA_X, y=y,
                              cells="\n".join(cells)))
    # Phone レイアウトは縦一列。高さは枚数で等分する。
    phone_h = AREA_H // len(SHEETS)
    phone = []
    for i, s in enumerate(SHEETS):
        phone.append("""                <zone fixed-size='280' h='{h}' id='{id}' is-fixed='true' name='{name}' w='{w}' x='{x}' y='{y}'>
                {style}
                </zone>""".format(h=phone_h, id=SHEET_IDS[i], name=q(s["name"]), w=AREA_W,
                                  x=AREA_X, y=AREA_Y + i * phone_h, style=zone_style(4)))
    return """    <dashboard enable-sort-zone-taborder='true' name='{dash}'>
      <style />
      <size sizing-mode='automatic' />
      <zones>
        <zone h='100000' id='{outer}' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='{ah}' id='{vert}' param='vert' type-v2='layout-flow' w='{aw}' x='{ax}' y='{ay}'>
{rows}
          </zone>
          {style}
        </zone>
      </zones>
      <devicelayouts>
        <devicelayout auto-generated='true' name='Phone'>
          <size maxheight='700' minheight='700' sizing-mode='vscroll' />
          <zones>
            <zone h='100000' id='{pouter}' type-v2='layout-basic' w='100000' x='0' y='0'>
              <zone h='{ah}' id='{pvert}' param='vert' type-v2='layout-flow' w='{aw}' x='{ax}' y='{ay}'>
{phone}
              </zone>
              {style}
            </zone>
          </zones>
        </devicelayout>
      </devicelayouts>
      <simple-id uuid='{uid}' />
    </dashboard>""".format(dash=q(DASH_NAME), rows="\n".join(rows_xml), phone="\n".join(phone),
                           outer=OUTER_ID, vert=VERT_ID, pouter=PHONE_OUTER_ID,
                           pvert=PHONE_VERT_ID, ah=AREA_H, aw=AREA_W, ax=AREA_X, ay=AREA_Y,
                           style=zone_style(8), uid=quuid())


def windows():
    out = []
    for s in SHEETS:
        out.append("""    <window class='worksheet' name='{name}'>
      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
          <strip size='2147483647'>
            <card type='title' />
          </strip>
        </edge>
        <edge name='right'>
          <strip size='160'>
            <card pane-specification-id='0' param='[{ds}].{color}' type='color' />
          </strip>
        </edge>
      </cards>
      <simple-id uuid='{uid}' />
    </window>""".format(name=q(s["name"]), ds=DS, color=inst(s["color"]), uid=quuid()))
    vps = "\n".join("""        <viewpoint name='{name}'>
          <zoom type='entire-view' />
        </viewpoint>""".format(name=q(s["name"])) for s in SHEETS)
    out.append("""    <window class='dashboard' maximized='true' name='{dash}'>
      <viewpoints>
{vps}
      </viewpoints>
      <active id='{active}' />
      <simple-id uuid='{uid}' />
    </window>""".format(dash=q(DASH_NAME), vps=vps, active=SHEET_IDS[0], uid=quuid()))
    return "\n".join(out)


def build(dbname):
    # 骨格は雛形の datasources 終わりまでを流用し、それ以降は作り直す。
    head = ref[:ref.index("  </datasources>") + len("  </datasources>")]
    head = sub1(r"dbname='[^']*'", "dbname='{}'".format(q(dbname)), head)
    head = sub1(r"        <metadata-records>.*?</metadata-records>",
                metadata_records(), head, flags=re.S)
    # 列定義（datasource 直下の column 群）も追加列を含む形に差し替える。
    head = sub1(r"      <column caption='[^']*' datatype='[^']*' name='\[[^\]]+\]' role='[^']*' type='[^']*' />\n"
                r"(?:      <column caption='[^']*' datatype='[^']*' name='\[[^\]]+\]' role='[^']*' type='[^']*' />\n)*",
                column_defs() + "\n", head)
    return "{head}\n  <worksheets>\n{ws}\n  </worksheets>\n  <dashboards>\n{dash}\n  </dashboards>\n  <windows {wattrs}>\n{win}\n  </windows>\n</workbook>\n".format(
        head=head, ws="\n".join(worksheet(s) for s in SHEETS),
        dash=dashboard(), win=windows(), wattrs=WINDOWS_ATTRS)


OUT_DIR.mkdir(parents=True, exist_ok=True)
twb_in_zip = OUT_DIR / "workbook.twb"          # .twbx に入れる用（相対パス参照）
twb_direct = OUT_DIR / "workbook-direct.twb"   # 単体で開く用（絶対パス参照）
for path, db in ((twb_in_zip, HYPER_IN_ZIP), (twb_direct, HYPER_WIN_ABS)):
    path.write_text(build(db), encoding="utf-8")
    print("生成:", path, path.stat().st_size, "bytes")

# .twbx はワークブックと .hyper を固めた zip。Tableau が開いている間の排他と無関係になる。
out_twbx = OUT_DIR / "workbook.twbx"
with zipfile.ZipFile(out_twbx, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(twb_in_zip, twb_in_zip.name)
    z.write(HYPER, HYPER_IN_ZIP)
print("生成:", out_twbx)
