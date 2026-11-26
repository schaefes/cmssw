import sys, glob, numpy as np, uproot
indir, out = sys.argv[1], sys.argv[2]
jf = ["pT","eta","phi","bTagScore","cTagScore","udsTagScore","tau_pTagScore","tau_nTagScore","eTagScore","muTagScore"]
cols = [f"L1GTScoreInputs_j{i}_{f}" for i in range(6) for f in jf] + ["L1GTScoreInputs_ht_scalarSumPT", "L1GTScoreInputs_met_pT"]
X, S = [], []
for a in uproot.iterate([f + ":Events" for f in sorted(glob.glob(indir + "/*.root"))], cols + ["L1GTScore_score"], library="np", step_size="200 MB"):
    X.append(np.stack([a[c] for c in cols], axis=1).astype(np.float32)); S.append(a["L1GTScore_score"].astype(np.float32))
X, S = np.concatenate(X), np.concatenate(S)
X.tofile(out + "_X.f32"); S.tofile(out + "_cmssw_hh4b.f32"); print(out, X.shape)
