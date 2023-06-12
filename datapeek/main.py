from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd
from rich.segment import Segment
from rich.style import Style

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, DataTable
from textual.reactive import reactive

ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]


from typing import Callable

ERROR_RETURN_VALUE = 1

READERS: dict[str, Callable] = {
    # excel extensions
    ".xlsx": pd.read_excel,
    ".xls":pd.read_excel, 
    ".xlsm":pd.read_excel, 
    ".xlsb":pd.read_excel, 
    # csv extensions
    ".csv": pd.read_csv,
    ".tsv": pd.read_csv,
    ".txt": pd.read_csv,
    # parquet extensions
    ".parquet": pd.read_parquet,
    ".pqt": pd.read_parquet,
    # pickle extensions
    ".pickle": pd.read_pickle,
    ".pkl": pd.read_pickle,
}

def get_reader_from_path(filepath: Path) -> Callable:
    return READERS[filepath.suffix.lower()]




class PeekedData(DataTable):
    def render_df(self, df: pd.DataFrame):
        self.clear(columns=True)

        self.add_columns('index', *df.columns.to_list())
        for row_data in df.itertuples(name=None):
            index = row_data[0]
            values = row_data[1:]
            self.add_row(index, *values)

    def on_mount(self) -> None:
        self.styles.height = "100%"
        self.styles.width = "100%"


class DataViewport(Container):
    rows_in_view: int

    def __init__(self, initial_rows: int, *args, **kwargs):
        self.rows_in_view = initial_rows
        super().__init__(*args, **kwargs)


    def compose(self) -> ComposeResult:
        yield PeekedData(header_height=1, zebra_stripes=True)

    def on_mount(self) -> None:
        self.styles.height = "1fr"
        self.styles.width = "1fr"

    def on_size(self) -> None:
        self.rows_in_view = self.size[1]


class Peek(App):
    data: pd.DataFrame
    filepath: str

    top_row = reactive(0)

    BINDINGS = [
        ("ctrl+d", "page_down", "Page Down"),
        ("ctrl+u", "page_up", "Page Up"),
    ]

    def __init__(self, data: pd.DataFrame, filepath: Path | str, **kwargs):
        self.data = data
        self.filepath = str(filepath)
        self.TITLE = str(self.filepath)
        super().__init__(**kwargs)

    @property
    def table(self) -> PeekedData:
        return self.query_one(PeekedData)

    @property
    def data_viewport(self) -> DataViewport:
        return self.query_one(DataViewport)

    @property
    def viewable(self) -> pd.DataFrame:
        """The viewable rows in the dataframe"""
        print(f"{self.data_viewport.size[1]=}")
        return self.data.iloc[self.top_row : self.data_viewport.rows_in_view + self.top_row]

    def watch_top_row(self, _: int) -> None:
        self.table.render_df(self.viewable)
 
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield DataViewport(initial_rows=self.size[1]-4)
 
    def on_mount(self) -> None:
        self.table.render_df(df=self.viewable)


    def action_page_down(self) -> None:
        self.top_row = min(self.top_row + self.data_viewport.rows_in_view, len(self.data))

    def action_page_up(self) -> None:
        self.top_row = max(self.top_row - self.data_viewport.rows_in_view, 0)

def main() -> int:
    try:
        filepath = Path(sys.argv[1])
    except IndexError:
        print("requires a file")
        return ERROR_RETURN_VALUE


    if not filepath.exists():
        print(f"{filepath} doesn't exist")
        return ERROR_RETURN_VALUE

    try:
        reader = get_reader_from_path(filepath)
    except KeyError:
        print(f"filetype not supported")
        return ERROR_RETURN_VALUE
 
    print("loading data...")
    data = reader(filepath)

    app = Peek(data=data, filepath=filepath)
    app.run()

    return 0


if __name__ == "__main__":
    exit(main())

