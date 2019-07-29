import abc
from typing import Optional, Sequence, Tuple, Union

import numpy as np

from pandas.tseries.offsets import DateOffset

BeginEnd = Tuple[np.ndarray, np.ndarray]


class BaseIndexer(abc.ABC):
    """Base class for window bounds calculations"""

    def __init__(
        self,
        index=None,
        offset: Optional[Union[str, DateOffset]] = None,
        keys: Optional[Sequence[np.ndarray]] = None,
    ):
        """
        Parameters
        ----------
        index : , default None
            pandas index to reference in the window bound calculation

        offset: str or DateOffset, default None
            Offset used to calcuate the window boundary

        keys: np.ndarray, default None
            Additional columns needed to calculate the window bounds

        """
        self.index = index
        self.offset = offset
        self.keys = keys

    @classmethod
    @abc.abstractmethod
    def get_window_bounds(
        cls,
        values: Optional[np.ndarray] = None,
        window_size: int = 0,
        min_periods: Optional[int] = None,
        center: Optional[bool] = None,
        closed: Optional[str] = None,
        win_type: Optional[str] = None,
    ) -> BeginEnd:
        """
        Computes the bounds of a window.

        Parameters
        ----------
        # TODO: should users have access to _all_ the values or just the length (len(values))?
        values : np.ndarray, default None
            values that will have the rolling operation applied

        window_size : int, default 0
            min_periods passed from the top level rolling API

        min_periods : int, default None
            min_periods passed from the top level rolling API

        center : bool, default None
            center passed from the top level rolling API

        closed : str, default None
            closed passed from the top level rolling API

        win_type : str, default None
            win_type passed from the top level rolling API

        Returns
        -------
        BeginEnd
            A tuple of ndarray[int64]s, indicating the boundaries of each
            window

        """


class FixedWindowIndexer(BaseIndexer):
    def get_window_bounds(
        self,
        values: Optional[np.ndarray] = None,
        window_size: int = 0,
        min_periods: Optional[int] = None,
        center: Optional[bool] = None,
        closed: Optional[str] = None,
        win_type: Optional[str] = None,
    ):
        num_values = len(values) if values is not None else 0
        start_s = np.zeros(window_size, dtype=np.int64)
        start_e = np.arange(window_size, num_values, dtype=np.int64) - window_size + 1
        start = np.concatenate([start_s, start_e])

        end_s = np.arange(window_size, dtype=np.int64) + 1
        end_e = start_e + window_size
        end = np.concatenate([end_s, end_e])
        return start, end


class VariableWindowIndexer(BaseIndexer):
    def _calculate_closed_bounds(self, closed: Optional[str]) -> Tuple[bool, bool]:
        left_closed = False
        right_closed = False

        # if windows is variable, default is 'right', otherwise default is 'both'
        if closed is None:
            closed = "right" if self.index is not None else "both"

        if closed == "both":
            left_closed = True
            right_closed = True

        elif closed == "right":
            right_closed = True

        elif closed == "left":
            left_closed = True

        return left_closed, right_closed

    def get_window_bounds(
        self,
        values: Optional[np.ndarray] = None,
        window_size: int = 0,
        min_periods: Optional[int] = None,
        center: Optional[bool] = None,
        closed: Optional[str] = None,
        win_type: Optional[str] = None,
    ):

        left_closed, right_closed = self._calculate_closed_bounds(closed)

        num_values = len(values) if values is not None else 0

        start = np.empty(num_values, dtype=np.int64)
        start.fill(-1)

        end = np.empty(num_values, dtype=np.int64)
        end.fill(-1)

        start[0] = 0

        # right endpoint is closed
        if right_closed:
            end[0] = 1
        # right endpoint is open
        else:
            end[0] = 0

        # start is start of slice interval (including)
        # end is end of slice interval (not including)
        for i in range(1, num_values):
            end_bound = self.index[i]
            start_bound = self.index[i] - window_size

            # left endpoint is closed
            if left_closed:
                start_bound -= 1

            # advance the start bound until we are
            # within the constraint
            start[i] = i
            for j in range(start[i - 1], i):
                if self.index[j] > start_bound:
                    start[i] = j
                    break

            # end bound is previous end
            # or current index
            if self.index[end[i - 1]] <= end_bound:
                end[i] = i + 1
            else:
                end[i] = end[i - 1]

            # right endpoint is open
            if not right_closed:
                end[i] -= 1

        return start, end
