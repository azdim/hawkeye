import pandas as pd


def generate_trade_data():
    """Generate sample OMS and PB trade datasets with controlled breaks."""
    base_trades = [
        {
            "TradeDate": "2026-04-30",
            "Ticker": "UST 10Y",
            "Side": "Buy",
            "Quantity": 2000000,
            "Price": 99.8750,
            "Commission": 150.00,
            "Broker": "JPM",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "UST 2Y",
            "Side": "Sell",
            "Quantity": 1500000,
            "Price": 100.1250,
            "Commission": 120.00,
            "Broker": "GS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "AAPL",
            "Side": "Buy",
            "Quantity": 2000,
            "Price": 192.3400,
            "Commission": 18.50,
            "Broker": "MS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "MSFT",
            "Side": "Sell",
            "Quantity": 1800,
            "Price": 410.1200,
            "Commission": 16.20,
            "Broker": "CITI",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "NVDA",
            "Side": "Buy",
            "Quantity": 900,
            "Price": 875.5500,
            "Commission": 14.40,
            "Broker": "UBS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "EURUSD",
            "Side": "Buy",
            "Quantity": 3000000,
            "Price": 1.0862,
            "Commission": 210.00,
            "Broker": "BARC",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "USDJPY",
            "Side": "Sell",
            "Quantity": 2500000,
            "Price": 155.4200,
            "Commission": 175.00,
            "Broker": "DB",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "GBPUSD",
            "Side": "Buy",
            "Quantity": 2000000,
            "Price": 1.2678,
            "Commission": 165.00,
            "Broker": "HSBC",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "TSLA",
            "Side": "Sell",
            "Quantity": 1300,
            "Price": 176.9300,
            "Commission": 12.75,
            "Broker": "JPM",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "AMZN",
            "Side": "Buy",
            "Quantity": 2400,
            "Price": 182.4700,
            "Commission": 19.20,
            "Broker": "GS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "META",
            "Side": "Buy",
            "Quantity": 1700,
            "Price": 498.6600,
            "Commission": 15.10,
            "Broker": "MS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "UST 30Y",
            "Side": "Sell",
            "Quantity": 1200000,
            "Price": 98.4375,
            "Commission": 110.00,
            "Broker": "CITI",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "USDCAD",
            "Side": "Buy",
            "Quantity": 2200000,
            "Price": 1.3724,
            "Commission": 160.00,
            "Broker": "UBS",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "IBM",
            "Side": "Sell",
            "Quantity": 1600,
            "Price": 188.3300,
            "Commission": 13.60,
            "Broker": "BARC",
        },
        {
            "TradeDate": "2026-04-30",
            "Ticker": "UST 5Y",
            "Side": "Buy",
            "Quantity": 1800000,
            "Price": 99.5625,
            "Commission": 130.00,
            "Broker": "DB",
        },
    ]

    oms_trades = pd.DataFrame(base_trades)
    pb_trades = pd.DataFrame(base_trades)

    # Break 1: Commission difference
    pb_trades.loc[pb_trades["Ticker"] == "AAPL", "Commission"] = 19.25

    # Break 2: Slight price rounding error
    pb_trades.loc[pb_trades["Ticker"] == "EURUSD", "Price"] = 1.0863

    # Break 3: Missing trade in OMS (exists in PB only)
    oms_trades = oms_trades[oms_trades["Ticker"] != "IBM"].reset_index(drop=True)

    # Break 4: Reversed side
    pb_trades.loc[pb_trades["Ticker"] == "TSLA", "Side"] = "Buy"

    # Break 5: Quantity mismatch
    pb_trades.loc[pb_trades["Ticker"] == "UST 5Y", "Quantity"] = 1750000

    column_order = [
        "TradeDate",
        "Ticker",
        "Side",
        "Quantity",
        "Price",
        "Commission",
        "Broker",
    ]
    oms_trades = oms_trades[column_order]
    pb_trades = pb_trades[column_order]

    return oms_trades, pb_trades


def export_sample_csv(output_path="sample_pb_statement.csv"):
    """Export generated PB sample statement to a local CSV file."""
    _, pb_trades = generate_trade_data()
    pb_trades.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    export_sample_csv()
