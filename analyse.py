#!/usr/bin/env python3
import glob

import matplotlib.figure
import pandas as pd


FIGSIZE = (5.5, 3)
COMMON = dict(
    capsize=2,
    y='mean',
    yerr='std',
    xlabel='',
    ylabel='MB/s',
    ylim=(0, 3500),
    rot=0
)


def load():
    dfs = [pd.read_csv(fname, index_col=('Python', 'Method', 'Size')) for fname in glob.glob('results/*-1gb.csv')]
    df = pd.concat(dfs)
    return df.xs(1000000128, level='Size') / 1e6


def fig_blank():
    fig = matplotlib.figure.Figure(figsize=FIGSIZE)
    ax = fig.subplots()
    ax.set_xlim(-0.5, 3.5)
    ax.set_ylim(0, 3500)
    ax.set_ylabel('MB/s')
    ax.set_xticks([])
    ax.grid(axis='y')
    ax.set_axisbelow(True)
    fig.savefig('images/blank.pdf')


def fig_generic(df, pythons, methods, filename):
    fig = matplotlib.figure.Figure(figsize=FIGSIZE)
    ax = fig.subplots()
    df.loc[pythons].unstack('Python').loc[methods].plot.bar(
        ax=ax,
        **COMMON
    )
    ax.set_xlim(-0.5, 3.5)
    ax.grid(axis='y')
    ax.set_axisbelow(True)
    for p in ax.patches:
        ax.annotate('{:.0f}'.format(p.get_height()),
                    (p.get_x() + 0.5 * p.get_width(), p.get_height() + 50),
                    fontsize='x-small',
                    horizontalalignment='center',
                    verticalalignment='bottom')
    fig.savefig(filename)


def main():
    df = load()

    fig_blank()
    fig_generic(df, ['3.6.12'], ['requests'], 'images/requests-cpy.pdf')
    fig_generic(df, ['3.6.12', 'PyPy 7.3.1'], ['requests'], 'images/requests-pypy.pdf')
    fig_generic(df, ['3.6.12'], ['requests', 'urllib3', 'httpclient', 'socket-read'], 'images/requests-stack.pdf')


if __name__ == '__main__':
    main()
