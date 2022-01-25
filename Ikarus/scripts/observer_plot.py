import finplot as fplt

def quote_asset(dashboard_data, ax):
    fplt.plot(dashboard_data['quote_asset']['total'], width=3, ax=ax, legend='Total')
    fplt.plot(dashboard_data['quote_asset']['free'], width=2, ax=ax, legend='Free')
    fplt.plot(dashboard_data['quote_asset']['in_trade'], width=2, ax=ax, legend='In Trade')
    fplt.add_line((dashboard_data['quote_asset']['total'].index[0], dashboard_data['quote_asset']['total'].iloc[0]),
        (dashboard_data['quote_asset']['total'].index[-1], dashboard_data['quote_asset']['total'].iloc[0]), color='#000000', interactive=False)


def quote_asset_leak(dashboard_data, ax):
    fplt.plot(dashboard_data['quote_asset_leak']['binary'], width=3, ax=ax, legend='binary')

