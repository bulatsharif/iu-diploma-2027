#!/usr/bin/env python3
"""Rebuild baseline figures from data/baseline.csv. Requires matplotlib."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, MaxNLocator
ROOT=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((ROOT/'data/baseline.csv').open()))
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':10,'axes.labelsize':10,
                     'axes.titlesize':11,'legend.fontsize':10,'pdf.fonttype':42,
                     'axes.spines.top':False,'axes.spines.right':False})
colors={'RU':'#245d8c','EN':'#b94c26'}
markers={'RU':'o','EN':'s'}

def get(lang,target):
    return sorted([r for r in rows if r['language']==lang and int(r['target'])==target and r['mode']=='rps'],key=lambda r:int(r['load']))
def style(ax):
    ax.set_xscale('log',base=2);ax.set_xticks([1,2,4,8,16]);ax.xaxis.set_major_formatter(ScalarFormatter())
    ax.set_xlabel('Offered requests/s');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig,axes=plt.subplots(1,3,figsize=(6.4,3.1),layout='constrained')
for ax,target in zip(axes,(100,500,1000)):
    for lang in ('RU','EN'):
        rs=get(lang,target); ax.plot([int(r['load']) for r in rs],[float(r['throughput'])/1000 for r in rs],label=lang,color=colors[lang],marker=markers[lang],lw=1.7,ms=4)
    ax.set_title(f'~{target} tokens');style(ax);ax.set_ylim(bottom=0)
axes[0].set_ylabel('Output throughput (1000 tokens/s)');axes[0].legend(frameon=False)
ROOT.joinpath('figs').mkdir(exist_ok=True)
for ext in ('pdf','png'):fig.savefig(ROOT/f'figs/baseline_throughput.{ext}',dpi=200)
plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(6.4,3.1),layout='constrained')
for lang in ('RU','EN'):
    rs=get(lang,1000); xs=[int(r['load']) for r in rs]
    axes[0].plot(xs,[float(r['ttft_p99']) for r in rs],label=lang,color=colors[lang],marker=markers[lang],lw=1.8)
    axes[1].plot(xs,[float(r['completion_pct']) for r in rs],label=lang,color=colors[lang],marker=markers[lang],lw=1.8)
for ax in axes:style(ax)
axes[0].set_yscale('log');axes[0].set_ylabel('p99 time to first token (ms)');axes[0].legend(frameon=False)
axes[1].set_ylim(80,101);axes[1].set_yticks([80,85,90,95,100]);axes[1].set_ylabel('Completed / submitted requests (%)')
axes[1].annotate('EN: 82.45%',xy=(16,82.45),xytext=(-7,12),textcoords='offset points',ha='right',fontsize=10,color=colors['EN'])
for ext in ('pdf','png'):fig.savefig(ROOT/f'figs/baseline_tail.{ext}',dpi=200)
plt.close(fig)
print('Wrote two figures as PDF and PNG.')
