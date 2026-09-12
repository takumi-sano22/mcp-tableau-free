"""架空の売上データを作り、実データなしで接続を確認できるようにする。"""

from pathlib import Path

from tableauhyperapi import (
    Connection, CreateMode, HyperProcess, Inserter, SqlType,
    TableDefinition, TableName, Telemetry,
)


def main() -> None:
    """既存ファイルを上書きせず、リポジトリのdataにサンプルを作る。"""
    path = Path(__file__).resolve().parents[1] / "data" / "sample.hyper"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise SystemExit("sample.hyperは既に存在します。別名に移動してから再実行してください。")
    definition = TableDefinition(
        TableName("Extract", "Sales"),
        [
            TableDefinition.Column("region", SqlType.text()),
            TableDefinition.Column("sales", SqlType.int()),
        ],
    )
    # 架空の少量データに限定し、そのままプレビュー結果と比較できるようにする。
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(hyper.endpoint, path, CreateMode.CREATE) as connection:
            connection.catalog.create_schema("Extract")
            connection.catalog.create_table(definition)
            with Inserter(connection, definition) as inserter:
                inserter.add_rows([["東京", 1200], ["大阪", 900], ["福岡", 600]])
                inserter.execute()
    print(f"サンプルを作成しました: {path}")


if __name__ == "__main__":
    main()
