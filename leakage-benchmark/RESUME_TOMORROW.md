# Resume — one model left

**Stopped 2026-08-19 23:20 for a laptop software update. Nothing is running.**

## State

Roster **15 of 16 complete**. PREREG section 8's floor is 12 — cleared, so the
run is valid whatever happens next.

Outstanding: **`gemini-3.7-flash`, 27/40, 13 cells.** Seven AI Studio keys in
`gemini.env` gave 9 cells in an hour and then nothing across five passes — a
daily quota wall. Waiting for the reset was the decision, not a workaround.

## To resume

```
nohup /tmp/synth_gem_overnight.sh > /tmp/gem_overnight.log 2>&1 &
```

It polls every 30 minutes for up to 24 hours, stops the moment the model reads
40/40, and runs `verify_synth.py` itself. If `/tmp` was cleared by the reboot,
the script is trivial to rewrite: `runner.py --provider gemini --models
gemini-3.7-flash --datasets <the 20 synth tables> --conditions 1,6 --repeats 1
--max-tokens 16000 --http-timeout 900`, in a loop, sourcing `gemini.env`.
Cached cells are skipped and failures are never cached, so re-running is free.

Check progress with:

```
python3 verify_synth.py
```

which refuses to certify until the roster reads 16 of 16.

## If the quota does not come back

Decided already, do not re-litigate: report `gemini-3.7-flash` ABSENT under
PREREG section 3, with its complete Vertex twin
`gemini-3.7-flash::vertex-think16000-t0.0` (40/40, plus 72 main-corpus cells)
reported beside the roster as a host replication — never as a substitute.
`verify_synth.py`'s gate then needs changing from a literal 16 to "16 minus
documented absences"; it currently refuses forever.

## The real remaining work is writing, not compute

1. **Section X does not exist.** `PAPER.md` mentions Stratum E nowhere. The
   whole experiment — D1/D2, the nemotron ladder, the clause diagnostic, the
   opaque control — lives only in `synth/STATUS.md`, `OPAQUE_CONTROL.md` and
   `CLAIM2_DRAFT.md`. This is the biggest lever on the paper.
2. **Claim (2) rewrite** — drafted in `CLAIM2_DRAFT.md`, gated on a complete
   roster and on the figures reaching `NUMBERS_E.txt`.
3. **Section 7.3** — still blocked on a matched C6-vs-C9 on Stratum B, which
   `verify_paper.py` does not yet emit.
4. **`PAPER_SHORT.md` has no checker** — it appears in five scripts, every one
   only in a comment.
5. **Environment pins drift**: `requirements.txt` says numpy 2.4.6 / pandas
   3.0.3; the machine has 2.5.2 / 3.0.5. Reconcile deliberately — `NUMBERS.txt`
   may predate the drift.
6. **Amendments 1 and 2 are in `PREREG.md` but not disclosed in `PAPER.md`.**
7. **Keys still need rotating** — the NVIDIA key (also sitting in plaintext in
   `/tmp/synth_nv.sh`) and every Gemini key pasted into a chat window.

## Do not push the response cache until the roster is done

The cached Stratum E cells name every column and every verdict; publishing them
early destroys the novelty guarantee PREREG section 3 rests on. Local commits
are fine — the branch is `vertex-provider-and-appendix-fixes`, HEAD `c6548a9`.
