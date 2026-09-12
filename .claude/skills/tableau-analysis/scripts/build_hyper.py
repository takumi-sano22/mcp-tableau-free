#!/usr/bin/env python3
"""CSV 群を型を明示して .hyper へ格納する。

CSV のまま Tableau に読ませても動くが、型が推論任せになり数値が文字列に落ちることがある。
集計軸と並び順に使う列を確実に数値・日時として持たせるため、ここで型を決めて格納する。

使い方:
    python build_hyper.py <csv_dir> <out.hyper> [types.json]

types.json を渡すと型を明示できる（推論より優先）。形式:
    {"<table>": {"<column>": "text|int|double|timestamp"}}
渡さない場合は各列の値から推論する（全値が整数なら int、など）。
データ行が 0 件の CSV でもテーブルは作る。その場合、型を指定しない列は text になる。
"""

import csv
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from tableauhyperapi import (Connection, CreateMode, HyperProcess, Inserter,
                             NULLABLE, SqlType, TableDefinition, TableName, Telemetry)

T, I, D, TS = "text", "int", "double", "timestamp"
SQL = {T: SqlType.text(), I: SqlType.big_int(), D: SqlType.double(), TS: SqlType.timestamp()}


def parse_ts(v):
    """オフセット付きの日時は UTC に揃えてから naive にする。

    オフセットを捨てるだけだと、同じ瞬間を指す `...T00:00:00Z` と `...T09:00:00+09:00` が
    別の時刻として入り、時系列の並びと集計が狂う。
    """
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(tzinfo=None)


def infer(values):
    """空欄を除いた値から型を決める。判定は厳しいほうから順に試す。"""
    vals = [v for v in values if v != ""]
    if not vals:
        return T
    for kind, fn in ((I, int), (D, float), (TS, parse_ts)):
        try:
            for v in vals:
                fn(v)
            return kind
        except (ValueError, TypeError):
            continue
    return T


def convert(value, kind):
    # 空欄は NULL にする。0 と欠測が混ざると集計が狂う。
    if value is None or value == "":
        return None
    if kind == I:
        # float を経由すると 2^53 を超える整数が黙って丸まるため、まず int で受ける。
        try:
            return int(value)
        except ValueError:
            pass
        # 整数列に小数が来たら黙って切り捨てず落とす（データが静かに壊れるのを防ぐ）。
        try:
            d = Decimal(value)
        except InvalidOperation:
            raise ValueError("整数列に数値でない値が入っています: {!r}".format(value))
        if d != d.to_integral_value():
            raise ValueError("整数列に小数が入っています: {!r}".format(value))
        return int(d)
    if kind == D:
        return float(value)
    if kind == TS:
        return parse_ts(value)
    return value


def main():
    csv_dir, out = Path(sys.argv[1]), Path(sys.argv[2])
    overrides = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else {}

    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, out, CreateMode.CREATE_AND_REPLACE) as conn:
            # public は新規 Hyper にも既定で存在するため、冪等な API を使う。
            conn.catalog.create_schema_if_not_exists("public")
            for path in sorted(csv_dir.glob("*.csv")):
                name = path.stem
                with open(path, encoding="utf-8") as fh:
                    reader = csv.DictReader(fh)
                    header = reader.fieldnames or []
                    rows = list(reader)
                if not header:
                    print("skip(ヘッダ無し):", name)
                    continue
                # 0 行でもテーブルは作る。テーブルごと無いと Tableau 側で参照先が消え、
                # 「0 件だった」ことを描けなくなる（references/data-handoff.md）。
                given = overrides.get(name, {})
                # 型定義とヘッダのずれは黙って無視せず落とす（指定したつもりの型が
                # 効かないまま格納されるのが、いちばん気づきにくい壊れ方のため）。
                unknown_cols = sorted(set(given) - set(header))
                if unknown_cols:
                    raise SystemExit("{} に無い列が types.json にあります: {}".format(
                        path.name, ", ".join(unknown_cols)))
                bad_kinds = sorted({k for k in given.values() if k not in SQL})
                if bad_kinds:
                    raise SystemExit("未知の型名です（{}）: {}".format(
                        "/".join(SQL), ", ".join(bad_kinds)))
                kinds = {c: given.get(c) or infer([r[c] for r in rows]) for c in header}
                table = TableDefinition(
                    TableName("public", name),
                    [TableDefinition.Column(c, SQL[kinds[c]], NULLABLE) for c in header])
                conn.catalog.create_table(table)
                with Inserter(conn, table) as ins:
                    ins.add_rows([[convert(r[c], kinds[c]) for c in header] for r in rows])
                    ins.execute()
                print("{:20s} {:7d} 行  {}".format(
                    name, len(rows), ", ".join("{}:{}".format(c, kinds[c]) for c in header)))
    print("出力:", out)


if __name__ == "__main__":
    main()
