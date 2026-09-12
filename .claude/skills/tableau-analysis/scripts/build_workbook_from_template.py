#!/usr/bin/env python3
"""実機の雛形を土台に Tableau ワークブック（.twb / .twbx）を組み立てる実装例。

**そのままでは動かない。** 下の「設定」を対象のデータ・雛形に合わせて書き換えて使う。
汎用ツールではなく、references/workbook-generation.md の手順をコードに落とした参照実装。

公式 XSD を通しても Tableau が開かない（読み込み時の content model が別）ことを実測したため、
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

# 列定義の approx-count を数えるための CSV（.hyper の元データ）。
CSV_PATH = Path("/tmp/<workdir>/axis_scores.csv")

# .twbx へ同梱する .hyper の実体。
HYPER = Path("/home/ai/project/mcp-tableau-free/data/sample_quality.hyper")

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

# シート定義。filters は (列名, 値) の単一値フィルタだけを使う。
# 複数値フィルタの XML は雛形に出ないことが多いため、絞り込みは列を足してデータ側で解決する
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


def q(t):
    return escape(str(t), {'"': "&quot;", "'": "&apos;"})


def quuid():
    return "{" + str(uuid.uuid4()).upper() + "}"


if not REF.is_file():
    sys.exit("雛形が見つかりません: {}\n"
             "references/workbook-generation.md「雛形の取り方」の手順で、"
             "対象環境の Tableau から .twb を書き出してください。".format(REF))

ref = REF.read_text(encoding="utf-8")
DS = re.search(r"name='(federated\.[a-z0-9]+)'", ref).group(1)
OBJ_ID = re.search(r"<object-id>(.*?)</object-id>", ref).group(1)

# 列ごとのユニーク件数。metadata の approx-count に入れる（Tableau が後で更新する統計値）。
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
          </metadata-record>""".format(n=name, rt=rt, o=i, lt=lt, agg=agg, tbl=TABLE,
                                       ac=APPROX[name], col=collation, oid=OBJ_ID))
    return "        <metadata-records>\n" + "\n".join(out) + "\n        </metadata-records>"


def column_defs():
    out = []
    # Tableau は datasource 直下の column を caption のアルファベット順に並べる。
    for name, caption, kind in sorted(COLUMNS, key=lambda c: c[1]):
        role, typ = ROLE_MAP[kind]
        out.append("      <column caption='{cap}' datatype='{dt}' name='[{n}]' role='{r}' type='{t}' />".format(
            cap=caption, dt=kind, n=name, r=role, t=typ))
    return "\n".join(out)


def inst(field, deriv="None"):
    """雛形に出てくる内部フィールド名の綴り。離散は nk、集計は qk。"""
    pre = {"None": "none", "Sum": "sum"}[deriv]
    kind = "qk" if deriv == "Sum" else "nk"
    return "[{}:{}:{}]".format(pre, field, kind)


def deps_and_filters(fields, filters):
    """使うフィールドの宣言・フィルタ・slices をまとめて作る。"""
    caption = {n: c for n, c, _ in COLUMNS}
    kinds = {n: k for n, _, k in COLUMNS}
    decls = []
    for f, deriv in sorted(fields.items()):
        role, typ = ROLE_MAP[kinds[f]]
        decls.append("            <column caption='{c}' datatype='{d}' name='[{f}]' role='{r}' type='{t}' />".format(
            c=caption[f], d=kinds[f], f=f, r=role, t=typ))
        it = "quantitative" if deriv == "Sum" else "nominal"
        decls.append("            <column-instance column='[{f}]' derivation='{d}' name='{i}' pivot='key' type='{t}' />".format(
            f=f, d=deriv, i=inst(f, deriv), t=it))
    filt, slices = [], []
    for f, value in filters:
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
            <datasource caption='{tbl} 抽出' name='{ds}' />
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
                           mark=s["mark"], tbl=TABLE, color=inst(s["color"]),
                           rows=inst(s["rows"], "Sum"), cols=inst(s["cols"]), uid=quuid())


ZONE_STYLE = """                <zone-style>
                  <format attr='border-color' value='#000000' />
                  <format attr='border-style' value='none' />
                  <format attr='border-width' value='0' />
                  <format attr='margin' value='4' />
                </zone-style>"""


def dashboard():
    # 2行×2列。外側 basic → 縦 flow → 横 flow 2本、という雛形と同じ入れ子にする。
    ids = [3, 9, 12, 15]
    rows_xml = []
    for r in (0, 1):
        cells = []
        for c in (0, 1):
            i = r * 2 + c
            cells.append("""              <zone h='49149' id='{id}' name='{name}' w='49517' x='{x}' y='{y}'>
{style}
              </zone>""".format(id=ids[i], name=q(SHEETS[i]["name"]),
                                x=483 + c * 49517, y=851 + r * 49149, style=ZONE_STYLE))
        rows_xml.append("""            <zone h='49149' id='{id}' param='horz' type-v2='layout-flow' w='99034' x='483' y='{y}'>
{cells}
            </zone>""".format(id=20 + r, y=851 + r * 49149, cells="\n".join(cells)))
    phone = []
    for i, s in enumerate(SHEETS):
        phone.append("""                <zone fixed-size='280' h='24574' id='{id}' is-fixed='true' name='{name}' w='99034' x='483' y='{y}'>
{style}
                </zone>""".format(id=ids[i], name=q(s["name"]), y=851 + i * 24574, style=ZONE_STYLE))
    return """    <dashboard enable-sort-zone-taborder='true' name='{dash}'>
      <style />
      <size sizing-mode='automatic' />
      <zones>
        <zone h='100000' id='4' type-v2='layout-basic' w='100000' x='0' y='0'>
          <zone h='98298' id='7' param='vert' type-v2='layout-flow' w='99034' x='483' y='851'>
{rows}
          </zone>
          <zone-style>
            <format attr='border-color' value='#000000' />
            <format attr='border-style' value='none' />
            <format attr='border-width' value='0' />
            <format attr='margin' value='8' />
          </zone-style>
        </zone>
      </zones>
      <devicelayouts>
        <devicelayout auto-generated='true' name='Phone'>
          <size maxheight='700' minheight='700' sizing-mode='vscroll' />
          <zones>
            <zone h='100000' id='31' type-v2='layout-basic' w='100000' x='0' y='0'>
              <zone h='98298' id='30' param='vert' type-v2='layout-flow' w='99034' x='483' y='851'>
{phone}
              </zone>
              <zone-style>
                <format attr='border-color' value='#000000' />
                <format attr='border-style' value='none' />
                <format attr='border-width' value='0' />
                <format attr='margin' value='8' />
              </zone-style>
            </zone>
          </zones>
        </devicelayout>
      </devicelayouts>
      <simple-id uuid='{uid}' />
    </dashboard>""".format(dash=q(DASH_NAME), rows="\n".join(rows_xml),
                           phone="\n".join(phone), uid=quuid())


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
      <active id='3' />
      <simple-id uuid='{uid}' />
    </window>""".format(dash=q(DASH_NAME), vps=vps, uid=quuid()))
    return "\n".join(out)


def build(dbname):
    # 骨格は雛形の datasources 終わりまでを流用し、それ以降は作り直す。
    head = ref[:ref.index("  </datasources>") + len("  </datasources>")]
    head = re.sub(r"dbname='[^']*'", "dbname='{}'".format(dbname), head)
    head = re.sub(r"        <metadata-records>.*?</metadata-records>",
                  metadata_records(), head, flags=re.S)
    # 列定義（datasource 直下の column 群）も追加列を含む形に差し替える。
    head = re.sub(r"      <column caption='[^']*' datatype='[^']*' name='\[[a-z_]+\]' role='[^']*' type='[^']*' />\n"
                  r"(?:      <column caption='[^']*' datatype='[^']*' name='\[[a-z_]+\]' role='[^']*' type='[^']*' />\n)*",
                  column_defs() + "\n", head, count=1)
    return "{head}\n  <worksheets>\n{ws}\n  </worksheets>\n  <dashboards>\n{dash}\n  </dashboards>\n  <windows saved-dpi-scale-factor='1.25' source-height='37'>\n{win}\n  </windows>\n</workbook>\n".format(
        head=head, ws="\n".join(worksheet(s) for s in SHEETS),
        dash=dashboard(), win=windows())


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
