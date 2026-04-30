import pandas as pd


def reconcile_trades(oms_df, pb_df):
    """
    Reconcile OMS and PB trade DataFrames.

    Returns:
        perfect_matches: Exact matches on Ticker, Side, Quantity, Price.
        unmatched: Trades missing in either system.
        mismatched: Trades matched on Ticker/Side but differing on
            Price, Quantity, or Commission, with Break_Reason.
    """
    key_cols = ["TradeDate", "Ticker", "Side", "Quantity", "Price"]

    # 1) Perfect matches: identical on requested key fields.
    perfect_matches = pd.merge(oms_df, pb_df, on=key_cols, how="inner")

    # 2) Unmatched: records present in only one system when using TradeDate/Ticker/Side.
    unmatched_merge = pd.merge(
        oms_df,
        pb_df,
        on=["TradeDate", "Ticker", "Side"],
        how="outer",
        suffixes=("_OMS", "_PB"),
        indicator=True,
    )
    unmatched = unmatched_merge[unmatched_merge["_merge"] != "both"].copy()
    unmatched["Missing_In"] = unmatched["_merge"].map(
        {"left_only": "PB", "right_only": "OMS"}
    )
    unmatched = unmatched.drop(columns=["_merge"])

    # 3) Mismatched: same TradeDate/Ticker/Side, but different Price/Quantity/Commission.
    compare_cols = ["TradeDate", "Ticker", "Side"]
    paired = pd.merge(
        oms_df,
        pb_df,
        on=compare_cols,
        how="inner",
        suffixes=("_OMS", "_PB"),
    )

    field_pairs = [("Price", "Price"), ("Quantity", "Quantity"), ("Commission", "Commission")]
    mismatch_mask = (
        (paired["Price_OMS"] != paired["Price_PB"])
        | (paired["Quantity_OMS"] != paired["Quantity_PB"])
        | (paired["Commission_OMS"] != paired["Commission_PB"])
    )
    mismatched = paired[mismatch_mask].copy()

    def build_break_reason(row):
        reasons = []
        for left, right in field_pairs:
            oms_col = f"{left}_OMS"
            pb_col = f"{right}_PB"
            if row[oms_col] != row[pb_col]:
                reasons.append(f"{left} mismatch (OMS={row[oms_col]}, PB={row[pb_col]})")
        return "; ".join(reasons)

    mismatched["Break_Reason"] = mismatched.apply(build_break_reason, axis=1)

    return perfect_matches, unmatched, mismatched
