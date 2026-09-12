#!/usr/bin/env python3
"""公式 XSD で .twb を構文検証する。

注意: XSD が保証するのは構文だけで、Tableau が開けるかは別。公開仕様と実装は食い違う
（XSD を通ったワークブックが開けない例を実測している）。足切りとしてのみ使うこと。
正しい構造は実機の出力から取る（references/workbook-generation.md）。

使い方:
    python validate_twb.py <twb_2026.2.0.xsd> <target.twb>

XSD は外部名前空間の参照を含み、そのままでは読み込めないため、この場で除去してから使う。
"""

import sys
from pathlib import Path

from lxml import etree

# user / xml 名前空間の属性参照は単体の XSD では解決できない。構造の検証には影響しない。
DROP = ("user:UserAttributes-AG", 'ref="xml:base"')


def main():
    xsd_path, twb_path = Path(sys.argv[1]), Path(sys.argv[2])
    lines = xsd_path.read_text(encoding="utf-8").splitlines(keepends=True)
    cleaned = "".join(l for l in lines if not any(d in l for d in DROP))
    schema = etree.XMLSchema(etree.fromstring(cleaned.encode("utf-8")).getroottree())

    doc = etree.parse(str(twb_path))
    if schema.validate(doc):
        print("OK: XSD 検証を通過（ただし Tableau で開ける保証にはならない）")
        return 0
    for e in schema.error_log:
        print("NG line {}: {}".format(e.line, e.message))
    return 1


if __name__ == "__main__":
    sys.exit(main())
