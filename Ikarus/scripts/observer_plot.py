import finplot as fplt

def qc(dashboard_data, ax):
    fplt.plot(dashboard_data['qc']['total'], width=3, ax=ax, legend='Total')
    fplt.plot(dashboard_data['qc']['free'], width=2, ax=ax, legend='Free')
    fplt.plot(dashboard_data['qc']['in_trade'], width=2, ax=ax, legend='In Trade')
    fplt.add_line((dashboard_data['qc']['total'].index[0], dashboard_data['qc']['total'].iloc[0]),
        (dashboard_data['qc']['total'].index[-1], dashboard_data['qc']['total'].iloc[0]), color='#000000', interactive=False)


def qc_leak(dashboard_data, ax):
    fplt.plot(dashboard_data['qc_leak']['binary'], width=3, ax=ax, legend='binary')

