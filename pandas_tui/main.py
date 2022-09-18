from __future__ import annotations

from typing import Any

import pandas as pd
from rich import box
from rich.console import RenderableType
from rich.pretty import Pretty
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

from pandas_tui.df import pd_mixed_table

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
        return Column(str(col_name))

    cols = map(_make_col, df.columns.values)
    table = Table(
        *cols,
        header_style=title_style,
        row_styles=["dim", ""],
        highlight=True,
        box=box.ROUNDED,
    )
    add_df_rows(table, df)

    return table


def render_index_as_table(df: pd.DataFrame) -> Table:

    idx = df.index

    if idx.name:
        idx_colname = Pretty(idx.name)
    else:
        idx_colname = " "

    col = Column(header=idx_colname, justify="left", no_wrap=True)

    table = Table(
        col,
        box=box.SIMPLE,
        row_styles=["dim", ""],
    )

    for i in idx:
        new_row = (str(i),)
        table.add_row(*new_row)

    return table


def add_df_rows(table: Table, df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        table.add_row(*map(str, row.values))


class DFScrollView(ScrollView):
    _speed = 500

    def page_left(self) -> None:
        self.target_x -= self.size.width - 2
        self.animate("x", self.target_x, speed=self._speed, easing="out_cubic")

    def page_right(self) -> None:
        self.target_x += self.size.width - 2
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

    async def on_load(self, event: events.Load) -> None:
        await self.bind("q", "quit", "Quit")
        await self.bind("j", "down", "Page Down")
        await self.bind("k", "up", "Page Up")
        await self.bind("h", "left", "Left")
        await self.bind("l", "right", "Right")

    async def on_mount(self, event: events.Mount) -> None:
        """Create and dock the widgets."""

        self.df = self.load_dataframe()
        self.top_row = 0
        self.body = body = DFScrollView(auto_width=True, fluid=False)
        self.index_view = index_view = Static(
            render_index_as_table(self.viewable),
        )

        # header / footer / dock
        await self.view.dock(Header(style=title_style), edge="top")
        await self.view.dock(DFFooter(), edge="bottom")

        await self.view.dock(index_view, edge="left", size=8)
        await self.view.dock(body, edge="right")

        async def add_content() -> None:
            await self.render_table()

        await self.call_later(add_content)

    @property
    def rows_in_view(self) -> int:
        return self.body.console.height - 9

    @property
    def viewable(self) -> pd.DataFrame:
        """The viewable rows in the dataframe"""
        return self.df.iloc[self.top_row : self.rows_in_view + self.top_row]

    async def render_table(self, cols_to_shift: int = 0) -> None:
        # get current horizontal scroll position
        x = self.body.x

        self.move_table_frame(cols_to_shift)

        await self.body.update(render_df_as_table(self.viewable), scroll_position=x)
        await self.index_view.update(render_index_as_table(self.viewable))

    def move_table_frame(self, row_delta: int) -> None:
        max_row = len(self.df) - self.rows_in_view

        self.top_row = max(min(max_row, self.top_row + row_delta), 0)

    async def action_down(self) -> None:
        await self.render_table(cols_to_shift=self.rows_in_view)

    async def action_up(self) -> None:
        await self.render_table(cols_to_shift=-self.rows_in_view)

    async def action_left(self) -> None:
        self.body.page_left()

    async def action_right(self) -> None:
        self.body.page_right()

    def load_dataframe(self) -> pd.DataFrame:
        df = pd_mixed_table(300, 10).round(5)
        return df


def main() -> None:
    DataFrameViewer.run(title="DataFrame Viewer", log="textual.log")
