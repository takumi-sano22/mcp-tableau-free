"""ローカルHyperファイルの一覧・プレビューを公開する最小MCPサーバ。"""

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from tableauhyperapi import Connection, HyperProcess, TableName, Telemetry


# 起動元による参照先の変化を避けるため、許可するデータ領域を起動時に確定する。
DATA_DIR = Path(os.environ.get("TABLEAU_DATA_DIR", "data")).resolve()
mcp = FastMCP("tableau-local-sandbox")


def resolve_hyper_path(filename: str) -> Path:
    """許可ディレクトリ内の既存Hyperファイルだけを受け付ける。"""
    path = (DATA_DIR / filename).resolve()
    if not path.is_relative_to(DATA_DIR) or path.suffix.lower() != ".hyper":
        raise ValueError("TABLEAU_DATA_DIR内の.hyperファイルを指定してください。")
    if not path.is_file():
        raise ValueError("指定された.hyperファイルが見つかりません。")
    return path


@mcp.tool()
def list_hyper_files() -> list[str]:
    """データディレクトリ直下にある.hyperファイル名を返す。"""
    if not DATA_DIR.is_dir():
        return []
    return sorted(
        path.name for path in DATA_DIR.iterdir()
        if path.is_file() and path.suffix.lower() == ".hyper"
        and path.resolve().is_relative_to(DATA_DIR)
    )


@mcp.tool()
def list_hyper_tables(filename: str) -> list[dict[str, str]]:
    """Hyperファイルのスキーマ名とテーブル名を返す。"""
    path = resolve_hyper_path(filename)
    # 各呼び出しで確実にファイルを解放し、Tableauとのロック競合を短くする。
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, path) as connection:
            return [
                {"schema": schema.name.unescaped, "table": table.name.unescaped}
                for schema in connection.catalog.get_schema_names()
                for table in connection.catalog.get_table_names(schema)
            ]


@mcp.tool()
def preview_hyper_table(
    filename: str, schema: str, table: str, limit: int = 20
) -> dict:
    """指定テーブルの列名と先頭行を取得する。行数は1〜100。値は文字列かnull。"""
    if not 1 <= limit <= 100:
        raise ValueError("limitは1〜100で指定してください。")
    path = resolve_hyper_path(filename)
    # 任意SQLを公開せず、識別子の引用をAPIに任せて入力がSQL構文になるのを防ぐ。
    table_name = TableName(schema, table)
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, path) as connection:
            definition = connection.catalog.get_table_definition(table_name)
            rows = connection.execute_list_query(f"SELECT * FROM {table_name} LIMIT {limit}")
    # Decimalや日付などもMCPで返せるよう、サンプルでは文字列に統一する。
    return {
        "columns": [column.name.unescaped for column in definition.columns],
        "rows": [[None if value is None else str(value) for value in row] for row in rows],
    }


def main() -> None:
    """ローカルのMCPクライアントから標準入出力で起動する。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
