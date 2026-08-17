"""PROTOCOL §3a -- build the Frame A candidate list, in rank order, once.

Run this on a machine with network access, commit the output, and never
regenerate it.  The frozen file IS the sampling frame; regenerating it later
would silently change the population as download counts move, and the
prevalence figure would no longer refer to a fixed set.

    python3 frame_a.py 120 > frame_a.json

Requires: pip install openml
"""
import sys, json, datetime


def build(n):
    import openml
    # every dataset the registry knows about, with its metadata
    df = openml.datasets.list_datasets(output_format="dataframe")

    # PROTOCOL I2/I3: tabular, supervised, named columns, non-trivial
    keep = df[(df.NumberOfClasses >= 2)
              & (df.NumberOfInstances >= 500)
              & (df.NumberOfFeatures >= 5)]

    # rank by usage.  'NumberOfDownloads' is absent on some mirrors; 'runs' is
    # the stable fallback and is recorded so the choice is auditable.
    rank_col = ("NumberOfDownloads" if "NumberOfDownloads" in keep.columns
                else "runs" if "runs" in keep.columns else None)
    if rank_col is None:
        raise SystemExit("no usage column available; record an alternative "
                         "ranking in PROTOCOL §3a before proceeding")

    keep = keep.sort_values(rank_col, ascending=False)
    # one entry per dataset NAME -- OpenML carries many near-duplicate versions
    # of the same underlying data, and counting them separately would inflate
    # the frame with repeats of a handful of classics.
    keep = keep.drop_duplicates(subset="name", keep="first").head(n)

    return dict(
        registry="OpenML",
        retrieved=datetime.date.today().isoformat(),
        rank_column=rank_col,
        filters="NumberOfClasses>=2, NumberOfInstances>=500, NumberOfFeatures>=5,"
                " deduplicated by dataset name, ranked descending",
        n=int(len(keep)),
        datasets=[dict(rank=i + 1, did=int(r.did), name=str(r["name"]),
                       rows=int(r.NumberOfInstances),
                       features=int(r.NumberOfFeatures),
                       usage=int(r[rank_col]))
                  for i, (_, r) in enumerate(keep.iterrows())],
    )


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    print(json.dumps(build(n), indent=1))
