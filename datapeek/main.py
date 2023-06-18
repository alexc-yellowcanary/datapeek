from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from typing import Literal
from typing import Protocol

import pandas as pd
from rich.segment import Segment
from rich.style import Style
from textual.app import App
from textual.app import ComposeResult
from textual.containers import Container
from textual.coordinate import Coordinate
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import DataTable
from textual.widgets import Footer
from textual.widgets import Header

ERROR_RETURN_VALUE = 1


class DataPathReader(Protocol):
    def __call__(self, path: Path) -> pd.DataFrame:
        ...


def ExcelReader(path: Path) -> pd.DataFrame:
    return pd.read_excel(path)


def CSVReader(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def ParquetReader(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


READERS: dict[str, DataPathReader] = {
    # excel extensions
    ".xlsx": ExcelReader,
    ".xls": ExcelReader,
    ".xlsm": ExcelReader,
    ".xlsb": ExcelReader,
    # csv extensions
    ".csv": CSVReader,
    ".tsv": CSVReader,
    ".txt": CSVReader,
    # parquet extensions
    ".parquet": ParquetReader,
    ".pqt": ParquetReader,
}


def get_reader_from_path(filepath: Path) -> DataPathReader:
    return READERS[filepath.suffix.lower()]


class PeekedData(DataTable):
    BINDINGS = [
        ("h", "cursor_left", "Cursor Left"),
        ("l", "cursor_right", "Cursor Right"),
        ("k", "cursor_up", "Cursor Up"),
        ("j", "cursor_down", "Cursor Down"),
    ]

    def render_df(self, df: pd.DataFrame) -> None:
        self.clear(columns=True)

        self.add_columns("index", *df.columns.to_list())
        for row_data in df.itertuples(name=None):
            index = row_data[0]
            values = row_data[1:]
            self.add_row(index, *values)

    def on_mount(self) -> None:
        self.styles.height = "100%"
        self.styles.width = "100%"

    @contextmanager
    def preserve_cursor_scroll_coords(self) -> Generator[None, None, None]:
        # save current coords
        cursor_coords = self.cursor_coordinate
        scroll_coords = self.scroll_offset

        # enter context
        yield

        # recreate saved coords
        self.move_cursor(
            row=cursor_coords.row,
            column=cursor_coords.column,
            animate=False,
        )

        self.scroll_to(x=scroll_coords.x, y=scroll_coords.y, animate=False)

    class ScrollRequest(Message):
        """Request the content to be scrolled"""

        def __init__(self, direction: Literal["up", "down"]) -> None:
            self.direction = direction
            super().__init__()

    def action_cursor_up(self) -> None:
        cursor_coords = self.cursor_coordinate

        if cursor_coords.row == 0:
            self.post_message(self.ScrollRequest("up"))

        else:
            super().action_cursor_up()

    def action_cursor_down(self) -> None:
        cursor_coords = self.cursor_coordinate

        if cursor_coords.row == self.row_count - 1:
            self.post_message(self.ScrollRequest("down"))

        else:
            super().action_cursor_down()


class DataViewport(Container):
    rows_in_view: int

    def __init__(self, initial_rows: int):
        self.rows_in_view = initial_rows
        super().__init__()

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

    def __init__(self, data: pd.DataFrame, filepath: Path | str):
        self.data = data
        self.filepath = str(filepath)
        self.TITLE = str(self.filepath)
        super().__init__()

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
        return self.data.iloc[
            self.top_row : self.data_viewport.rows_in_view + self.top_row
        ]

    def watch_top_row(self, _: int) -> None:
        self.table.render_df(self.viewable)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield DataViewport(initial_rows=self.size[1] - 4)

    def on_mount(self) -> None:
        self.table.render_df(df=self.viewable)

    def action_page_down(self) -> None:

        with self.table.preserve_cursor_scroll_coords():
            self.top_row = min(
                self.top_row + self.data_viewport.rows_in_view,
                len(self.data) - 1,
            )

    def action_page_up(self) -> None:
        with self.table.preserve_cursor_scroll_coords():
            self.top_row = max(self.top_row - self.data_viewport.rows_in_view, 0)

    def on_peeked_data_scroll_request(self, scroll_request: PeekedData.ScrollRequest) -> None:
        """Page the data in the direction, and move the cursor to the opposite
        row to represent the cursor moving to the first row of the next page in
        that direction"""
        row_count = self.table.row_count

        if scroll_request.direction == "up":
            self.action_page_up()
            self.table.move_cursor(row=row_count - 1, animate=False)

        elif scroll_request.direction == "down":
            self.action_page_down()
            self.table.move_cursor(row=0, animate=False)


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
