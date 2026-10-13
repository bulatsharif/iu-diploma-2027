#!/usr/bin/env python3
"""Rebuild manuscript measurements and tables from the pinned public archive.
Usage: python scripts/build_results.py --repo /path/to/iu-diploma-2027
Standard library only; does not run inference or alter the experiment repository.
"""
import argparse, csv, hashlib, json, statistics, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '3bd7f18d184cdad8101fff41fdf53125a0fe085f'
ARCHIVE = Path('reports/baseline_20261013_092255')
METRICS = {'ttft': 'time_to_first_token', 'tpot': 'inter_token_latency',
           'latency': 'request_latency', 'length': 'output_sequence_length'}


def table(name, caption, label, spec, header, rows, note='', size=r'\small'):
    text = '\n'.join([r'\begin{table}[htbp]', r'\centering',
        r'\caption{' + caption + '}', r'\label{' + label + '}',
        r'\begin{singlespace}', size, r'\setlength{\tabcolsep}{4pt}',
        r'\renewcommand{\arraystretch}{1.2}', r'\begin{tabular}{' + spec + '}',
        r'\toprule', header + r' \\', r'\midrule',
        '\n'.join(' & '.join(row) + r' \\' for row in rows),
        r'\bottomrule', r'\end{tabular}',
        (r'\par\smallskip\raggedright ' + note) if note else '',
        r'\end{singlespace}', r'\end{table}', ''])
    (ROOT / 'tables' / (name + '.tex')).write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    args = p.parse_args()
    repo = args.repo.resolve()
    archive = repo / ARCHIVE
    counts = {r['run']: {k:int(v) for k,v in r.items() if k!='run'}
              for r in csv.DictReader((archive/'request_counts.csv').open())}
    manifest = json.loads((archive/'deployment.json').read_text())
    for group in ('input_sha256', 'script_sha256'):
        for path, digest in manifest[group].items():
            assert hashlib.sha256((repo/path).read_bytes()).hexdigest() == digest, path
    rows=[]
    source_hashes={}
    for path in sorted((archive/'runs').glob('*.json')):
        d=json.loads(path.read_text()); run=path.stem
        lang, target, mode, load=run.split('_')
        c=counts[run]
        assert c['completed'] == int(d['request_count']['avg']), run
        assert c['sent'] == c['completed'] + c['cancelled'] + c['errors'], run
        assert d['is_complete'] and not d['was_cancelled'], run
        row={'run':run,'language':lang.upper(),'target':int(target), 'mode':mode,
             'load':int(load), **c,
             'completion_pct':100*c['completed']/c['sent'],
             'throughput':d['output_token_throughput']['avg']}
        for short,key in METRICS.items():
            for percentile in ('p50','p95','p99'):
                row[f'{short}_{percentile}']=d[key][percentile]
        row['source_json']=str(path.relative_to(repo))
        rows.append(row)
        source_hashes[row['source_json']]=hashlib.sha256(path.read_bytes()).hexdigest()
    assert len(rows)==36
    rows.sort(key=lambda r:(r['target'], 0 if r['language']=='RU' else 1,
                            0 if r['mode']=='concurrency' else r['load']))
    assert sum(r['sent'] for r in rows)==22843
    assert sum(r['completed'] for r in rows)==22459
    assert sum(r['cancelled'] for r in rows)==384
    for folder in ('data','tables'): (ROOT/folder).mkdir(exist_ok=True)
    with (ROOT/'data/baseline.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)
    checked_commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if checked_commit!=COMMIT:
        print('Note: working HEAD differs from manuscript snapshot; archive values and hashes validated.')
    source_hashes[str(ARCHIVE/'request_counts.csv')]=hashlib.sha256((archive/'request_counts.csv').read_bytes()).hexdigest()
    provenance={'repository':'https://github.com/bulatsharif/iu-diploma-2027',
       'reviewed_commit':COMMIT,'experiment_commit':manifest['git_commit'],
       'experiment_patch':str(ARCHIVE/'launch-fix.patch'),
       'archive':str(ARCHIVE),'source_sha256':source_hashes,
       'notes':'One measured run per condition. Quantiles cover completed requests. Throughput is exported, not recomputed.'}
    (ROOT/'data/provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    env=[['GPU','1 NVIDIA H100, 80 GB HBM3'],['Model and precision','Qwen3-8B, BF16; no drafter'],
      ['Runtime','vLLM 0.30.0; AIPerf 0.13.0'],['Supporting packages','PyTorch 2.13.0; Transformers 5.17.0'],
      ['Execution','CUDA graphs enabled; prefix caching disabled'],['Generation','Thinking disabled; temperature 0.6'],
      ['Sampling','Top-$p$ 0.95; top-$k$ 20; model EOS defaults']]
    table('environment','Recorded baseline environment','tab:environment','@{}lp{10cm}@{}','Item & Recorded value',env)
    meta=json.loads((repo/'data/prompts/metadata.json').read_text())
    inputs=[]
    for lang in ('ru','en'):
        for target in (100,500,1000):
            values=[r['prompt_tokens'][str(target)] for r in meta['requests'][lang]]
            inputs.append([lang.upper(),str(target),str(len(values)),str(min(values)),f'{statistics.mean(values):.2f}',str(max(values))])
    table('prompts','Prepared input lengths, including the chat template','tab:prompts','@{}lrrrrr@{}',
      'Language & Output target & Histories & Min. & Mean & Max.',inputs,
      'Lengths are tokens. The same 100 histories per language are reused for each output target.')
    c1=[r for r in rows if r['mode']=='concurrency']
    table('concurrency_one','Baseline at concurrency one','tab:c1','@{}lrrrrr@{}',
      'Profile & TPOT p50 & Latency p50 & Tokens/s & Output p50 & Done/sent',
      [[f"{r['language']} {r['target']}",f"{r['tpot_p50']:.2f}",f"{r['latency_p50']/1000:.2f}",f"{r['throughput']:.2f}",f"{r['length_p50']:.0f}",f"{r['completed']}/{r['sent']}"] for r in c1],
      'TPOT is in milliseconds; response latency is in seconds. Profile numbers denote requested output targets, not fixed lengths.')
    r16=[r for r in rows if r['mode']=='rps' and r['load']==16]
    table('load16','Baseline at 16 offered requests/s','tab:load16','@{}lrrrr@{}',
      'Profile & TTFT p99 (ms) & Latency p99 (s) & Tokens/s & Done/sent',
      [[f"{r['language']} {r['target']}",f"{r['ttft_p99']:.2f}",f"{r['latency_p99']/1000:.2f}",f"{r['throughput']:.2f}",f"{r['completed']}/{r['sent']}"] for r in r16])
    for target in (100,500,1000):
        subset=[r for r in rows if r['target']==target]
        triplet=lambda r,key: ' / '.join(f"{r[key+'_'+q]:.2f}" for q in ('p50','p95','p99'))
        table(f'full_{target}',f'Complete baseline: approximately {target} requested output tokens',f'tab:full{target}',
          '@{}llrrrrr@{}','Lang. & Load & TTFT (ms) & TPOT (ms) & Latency (ms) & Tokens/s & Output length',
          [[r['language'],'C1' if r['mode']=='concurrency' else 'RPS '+str(r['load']),triplet(r,'ttft'),triplet(r,'tpot'),triplet(r,'latency'),f"{r['throughput']:.2f}",triplet(r,'length')] for r in subset],
          'Triplets are p50 / p95 / p99. C1: concurrency one. Acceptance rate and length: not applicable (no drafter). One run per condition.',
          size=r'\fontsize{10.5}{13}\selectfont')
    countrows=[]
    for r in rows:
        countrows.append(' & '.join([r['language'],str(r['target']),'C1' if r['mode']=='concurrency' else 'RPS '+str(r['load']),str(r['sent']),str(r['completed']),str(r['cancelled']),f"{r['completion_pct']:.2f}"])+r' \\')
    counts_tex=r'''\begin{singlespace}
\small
\setlength{\tabcolsep}{6pt}
\begin{longtable}{@{}llrrrrr@{}}
\caption{Baseline request outcomes. Error counts are zero for all runs.}\label{tab:counts}\\
\toprule
Lang. & Target & Load & Sent & Done & Cancelled & Done (\%) \\
\midrule
\endfirsthead
\multicolumn{7}{c}{Table \thetable\ continued}\\
\toprule
Lang. & Target & Load & Sent & Done & Cancelled & Done (\%) \\
\midrule
\endhead
\bottomrule
\endfoot
'''+ '\n'.join(countrows)+r'''
\midrule
\multicolumn{3}{l}{Total} & 22843 & 22459 & 384 & 98.32 \\
\end{longtable}
\end{singlespace}
'''
    (ROOT/'tables/counts.tex').write_text(counts_tex)
    print('Validated 36 reports and 11 input/script hashes; wrote CSV, provenance and 8 numerical tables.')

if __name__=='__main__':main()
