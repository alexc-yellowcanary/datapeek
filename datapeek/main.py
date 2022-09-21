from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Iterable

import click
import pandas as pd
from rich import box
from rich._loop import loop_first_last
from rich.console import Console
from rich.console import RenderableType
from rich.style import Style
from rich.table import Column
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import ScrollView
from textual.widgets import Static

from datapeek.df import pd_mixed_table

PRIMARY_COLOUR = "sandy_brown"
ACCENT_COLOUR = "grey23"

index_style = Style(italic=True, color=PRIMARY_COLOUR)
title_style = Style(bold=True, color=PRIMARY_COLOUR)
footer_style = Style(color=PRIMARY_COLOUR, bgcolor=ACCENT_COLOUR)


class DFFooter(Footer):
    def make_key_text(self) -> Text:
        """Create text containing all the keys."""
        text = Text(
            style=footer_style,
            no_wrap=True,
            overflow="ellipsis",
            justify="left",
            end="",
        )
        for binding in self.app.bindings.shown_keys:
            key_display = (
                binding.key.upper()
                if binding.key_display is None
                else binding.key_display
            )
            hovered = self.highlight_key == binding.key
            key_text = Text.assemble(
                (f" {key_display} ", "reverse" if hovered else "default on default"),
                f" {binding.description} ",
                meta={
                    "@click": f"app.press('{binding.key}')",
                    "key": binding.key,
                },
            )
            text.append_text(key_text)
        return text


def render_df_as_table(df: pd.DataFrame) -> Table:
    def _make_col(col_name: Any) -> Column:
        return Column(str(col_name), no_wrap=True, max_width=30)

    cols = map(_make_col, df.columns.values)
    table = Table(
        *cols,
        header_style=title_style,
        row_styles=["dim", ""],
        # show_lines=True,
        highlight=True,
        box=box.ROUNDED,
    )
    add_df_rows(table, df)

    return table


def render_index_as_table(df: pd.DataFrame, row_heights: list[int]) -> Table:

    idx = df.index

    if idx.name:
        idx_colname = idx.name
    else:
        idx_colname = " "

    index_col = Column(header=idx_colname, justify="left", no_wrap=True)

    show_lines = True

    table = Table(
        index_col,
        box=box.ROUNDED,
        # show_lines=True,
        row_styles=["dim", ""],
    )

    for i, row_height in zip(idx, row_heights[1:]):
        idx_label = str(i) + "\n" * (row_height - show_lines)
        table.add_row(*(idx_label,))

    return table


def get_row_heights(table: Table, console: Console) -> list[int]:
    """Returns list of heights (in lines) for all rows in the table (including
    header and footer if they are displayed.
    """
    table_style = console.get_style(table.style or "")
    border_style = table_style + console.get_style(table.border_style or "")

    _all_column_cells = (
        table._get_cells(console, column_index, column)
        for column_index, column in enumerate(table.columns)
    )

    all_row_cells = list(zip(*_all_column_cells))

    get_style = console.get_style
    get_row_style = table.get_row_style
    options = console.options
    columns = table.columns

    show_header = table.show_header
    show_footer = table.show_footer

    widths = table._calculate_column_widths(console, options)

    row_heights = []
    for row_idx, (is_first_col, is_last_col, row_cells) in enumerate(
        loop_first_last(all_row_cells),
    ):
        header_row = is_first_col and show_header
        footer_row = is_last_col and show_footer
        row = (
            table.rows[row_idx - show_header]
            if (not header_row and not footer_row)
            else None
        )
        max_height = 1
        if header_row or footer_row:
            row_style = Style.null()
        else:
            row_style = get_style(
                get_row_style(console, row_idx - 1 if show_header else row_idx),
            )
        for width, cell, column in zip(widths, row_cells, columns):
            render_options = options.update(
                width=width,
                justify=column.justify,
                no_wrap=column.no_wrap,
                overflow=column.overflow,
                height=None,
            )
            lines = console.render_lines(
                cell.renderable,
                render_options,
                style=get_style(cell.style) + row_style,
            )
            max_height = max(max_height, len(lines))

        row_heights.append(max_height)

    return row_heights


def add_df_rows(table: Table, df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        table.add_row(*map(str, row.values))


class DFScrollView(ScrollView):
    """Custom scroll view, with snappier horizontal scrolling"""

    _speed = 500

    def page_left(self) -> None:
        self.target_x -= int(self.size.width * 0.8)
        self.animate("x", self.target_x, speed=self._speed, easing="out_cubic")

    def page_right(self) -> None:
        self.target_x += int(self.size.width * 0.8)
        self.animate("x", self.target_x, speed=self._speed, easing="out_cubic")

    async def update(
        self,
        renderable: RenderableType,
        scroll_position: int = 0,
    ) -> None:
        await super().update(renderable)
        self.x = scroll_position


class DataFrameViewer(App):
    """An example of a very simple Textual App"""

    df: pd.DataFrame
    top_row: int

    def __init__(
        self,
        *args: Iterable[Any],
        dataframe: pd.DataFrame,
        **kwargs: dict[str, Any],
    ) -> None:
        super().__init__(*args, **kwargs)
        self.df = dataframe

    async def on_load(self, event: events.Load) -> None:
        await self.bind("q", "quit", "Quit")
        await self.bind("j", "down", "Page Down")
        await self.bind("k", "up", "Page Up")
        await self.bind("h", "left", "Left")
        await self.bind("l", "right", "Right")

    async def on_mount(self, event: events.Mount) -> None:
        """Create and dock the widgets + set initial static content."""

        self.top_row = 0

        self.body = body = DFScrollView(auto_width=True, fluid=False)

        main_table = render_df_as_table(self.viewable)
        row_heights = get_row_heights(main_table, self.body.console)
        idx_view = render_index_as_table(self.viewable, row_heights)
        self.index_view = index_view = Static(idx_view)

        # header / footer / dock
        await self.view.dock(Header(style=title_style), edge="top")
        await self.view.dock(DFFooter(), edge="bottom")

        await self.view.dock(index_view, edge="left", size=8)
        await self.view.dock(body, edge="right")

        async def add_content() -> None:
            await self.render_table()

        await self.call_later(add_content)

    @property
    def lines_in_view(self) -> int:
        return self.body.console.height - 8

    @property
    def viewable(self) -> pd.DataFrame:
        """The viewable rows in the dataframe"""

        # first get dataframe, assuming we can show one row per-line
        max_viewable_df = self.df.iloc[self.top_row : self.lines_in_view + self.top_row]

        # now render it, to find out the actual row heights
        rendered = render_df_as_table(max_viewable_df)
        row_heights = get_row_heights(rendered, self.body.console)

        if sum(row_heights) <= self.lines_in_view:
            # return df if we can fit it in viewport
            return max_viewable_df

        # pick what rendered rows we can fit - ignore column header width
        rendered_lines = 0
        max_row_idx = 0
        for row_idx, row_height in enumerate(row_heights[1:]):
            if rendered_lines + row_height < self.lines_in_view:
                max_row_idx = row_idx
                rendered_lines += row_height
            else:
                break
        return self.df.iloc[self.top_row : max_row_idx + self.top_row]

    async def render_table(self, cols_to_shift: int = 0) -> None:
        # get current horizontal scroll position
        x = self.body.x

        self.move_table_frame(cols_to_shift)

        main_table = render_df_as_table(self.viewable)
        row_heights = get_row_heights(main_table, self.body.console)
        idx_view = render_index_as_table(self.viewable, row_heights)

        await self.body.update(main_table, scroll_position=x)
        await self.index_view.update(idx_view)

    def move_table_frame(self, row_delta: int) -> None:
        max_row = len(self.df) - self.lines_in_view

        self.top_row = max(min(max_row, self.top_row + row_delta), 0)

    async def action_down(self) -> None:
        await self.render_table(cols_to_shift=len(self.viewable))

    async def action_up(self) -> None:
        await self.render_table(cols_to_shift=-len(self.viewable))

    async def action_left(self) -> None:
        self.body.page_left()

    async def action_right(self) -> None:
        self.body.page_right()


@click.command()
@click.argument("file")
def main(file: str) -> None:

    # TODO: hacky file handling/reading for now - fix later, etc
    filepath = Path(file)

    df = pd.read_csv(filepath).round(3)

    DataFrameViewer.run(title="DataFrame Viewer", log="textual.log", dataframe=df)
