import numpy as np, json
R = 40000.0  # kHz, TopoFlow CROSSING_RATE_KHZ convention (rate = R * bkg eff)
targets = {"Loose": 50.0, "Medium": 20.0, "Tight": 10.0}
L = lambda f: np.fromfile(f, np.float32)
y = np.fromfile("bbtt_test_y.i8", np.int8)
models = {
  "hh4b":     dict(mb=L("mb_hh4b.f32"),     sig={"HH4b (50k CMSSW nano)": L("hh4b_hh4b.f32"),     "HH->bbtautau (test set)": L("bbtt_test_hh4b.f32")[y == 1]}),
  "hh2b2tau": dict(mb=L("mb_hh2b2tau.f32"), sig={"HH4b (50k CMSSW nano)": L("hh4b_hh2b2tau.f32"), "HH->bbtautau (test set)": L("bbtt_test_hh2b2tau.f32")[y == 1]}),
}
n = len(models["hh4b"]["mb"]); res = {}
print(f"MinBias events: {n}  (1 event = {R/n:.3f} kHz)\n")
for m, d in models.items():
    mb = np.sort(d["mb"]); res[m] = {}
    cur = (d["mb"] > 0.95).mean() * R
    print(f"== {m}   current 0.95 cut: {cur:.1f} kHz")
    for wp, t in targets.items():
        kmax = int(np.floor(t / R * n))                     # max allowed passing MinBias events
        thr = mb[n - kmax - 1] if kmax < n else mb[0] - 1   # pass = score > thr  -> exactly <= kmax pass (ties go up)
        thr = np.ceil(thr * 1024) / 1024                    # on the 1/1024 output grid
        rate = (d["mb"] > thr).mean() * R; err = np.sqrt((d["mb"] > thr).sum()) / n * R
        effs = {k: float((s > thr).mean()) for k, s in d["sig"].items()}
        res[m][wp] = dict(threshold=float(thr), rate_khz=float(rate), rate_err_khz=float(err), **{"eff " + k: v for k, v in effs.items()})
        print(f"  {wp:6s} thr > {thr:8.4f}   rate {rate:5.1f} ± {err:3.1f} kHz   " + "   ".join(f"eff[{k}] {v:.3f}" for k, v in effs.items()))
json.dump(res, open("working_points.json", "w"), indent=2)
