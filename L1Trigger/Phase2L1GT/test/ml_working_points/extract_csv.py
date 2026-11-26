import sys, numpy as np
d = "/afs/cern.ch/user/s/stella/TopoFlow/event_tagger/data/03_preprocessed/"
X = np.loadtxt(d + "event_tagger_X_test_hw.csv", delimiter=",", skiprows=1, dtype=np.float32)
y = np.loadtxt(d + "processed_event_tagger_y_test.csv", delimiter=",", skiprows=1, dtype=np.int8)
X.tofile(sys.argv[1] + "_X.f32"); y.tofile(sys.argv[1] + "_y.i8"); print(X.shape, y.sum())
