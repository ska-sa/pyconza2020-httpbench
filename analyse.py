#!/usr/bin/env python3
import glob

import matplotlib.figure
import pandas as pd


COMMON = dict(
    capsize=5,
    y='mean',
    yerr='std',
    ylabel='MB/s',
    ylim=(0, 3500),
    rot=False
)


def load():
    dfs = [pd.read_csv(fname, index_col=('Python', 'Method', 'Size')) for fname in glob.glob('results/*-1gb.csv')]
    df = pd.concat(dfs)
    return df.xs(1000000128, level='Size') / 1e6


def fig_blank():
    fig = matplotlib.figure.Figure()
    ax = fig.subplots()
    ax.set_xlim(-0.5, 2.5)
    ax.set_ylim(0, 3500)
    ax.set_xlabel('Method')
    ax.set_ylabel('MB/s')
    ax.set_xticks([])
    fig.savefig('images/blank.pdf')


def fig_generic(df, pythons, methods, filename):
    fig = matplotlib.figure.Figure()
    ax = fig.subplots()
    df.loc[pythons].unstack('Python').loc[methods].plot.bar(
        ax=ax,
        **COMMON
    )
    ax.set_xlim(-0.5, 2.5)
    fig.savefig(filename)


def main():
    df = load()

    fig_blank()
    fig_generic(df, ['3.6.12'], ['requests'], 'images/requests-cpy.pdf')
    fig_generic(df, ['3.6.12', 'PyPy 7.3.1'], ['requests'], 'images/requests-pypy.pdf')


if __name__ == '__main__':
    main()
