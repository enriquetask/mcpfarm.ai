"""
Data Science MCP server — NumPy, Pandas, and statistics utilities.
"""

from io import StringIO
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

from fastmcp import FastMCP

mcp = FastMCP(name="Data Science Server")


#
# ------------------------- NumPy Array Tools -------------------------
#

@mcp.tool()
def numpy_array(arr: List[float]) -> List[float]:
    """
    Return the same array (identity). Useful to turn list -> numpy internally
    and facilitate other array ops.
    """
    return np.array(arr).tolist()

@mcp.tool()
def array_sum(arr: List[float]) -> float:
    """Sum of numbers in a list (via NumPy)."""
    return float(np.sum(arr))

@mcp.tool()
def array_mean(arr: List[float]) -> float:
    """Mean of numbers in a list (via NumPy)."""
    return float(np.mean(arr))


#
# ------------------------ Pandas Data Tools --------------------------
#

@mcp.tool()
def df_from_dict(records: List[Dict]) -> str:
    """
    Build a DataFrame from a list of dicts and return simple info.
    Useful for converting JSON into tabular.
    """
    df = pd.DataFrame(records)
    return df.to_json()

@mcp.tool()
def df_head(json_df: str, n: int = 5) -> str:
    """
    Return the first n rows of a DataFrame encoded as JSON.
    """
    df = pd.read_json(StringIO(json_df))
    return df.head(n).to_json()

@mcp.tool()
def df_describe(json_df: str) -> Dict:
    """
    Return descriptive statistics for a DataFrame.
    Includes count, mean, std, min, quartiles, and max for numeric cols.
    """
    df = pd.read_json(StringIO(json_df))
    return df.describe().to_dict()

@mcp.tool()
def df_filter(
    json_df: str, column: str, op: str, value: float
) -> str:
    """
    Filter a DataFrame where column op value.
    Supported ops: '==', '!=', '<', '<=', '>', '>='
    """
    df = pd.read_json(StringIO(json_df))
    if op not in ("==", "!=", "<", "<=", ">", ">="):
        raise ValueError(f"Unsupported op: {op}")
    return df.query(f"{column} {op} @value").to_json()


#
# ---------------------- Statistics / Sampling ------------------------
#

@mcp.tool()
def mean(values: List[float]) -> float:
    """Arithmetic mean."""
    return float(np.mean(values))

@mcp.tool()
def median(values: List[float]) -> float:
    """Median."""
    return float(np.median(values))

@mcp.tool()
def std(values: List[float]) -> float:
    """Standard deviation (population)."""
    return float(np.std(values))

@mcp.tool()
def sample(values: List[float], k: int = 1, seed: Optional[int] = None) -> List[float]:
    """Random sample k items from values."""
    rng = np.random.default_rng(seed)
    return rng.choice(values, size=min(k, len(values)), replace=False).tolist()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.http_app(stateless_http=True),
        host="0.0.0.0",
        port=9001,
    )
