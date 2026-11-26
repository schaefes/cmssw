import FWCore.ParameterSet.Config as cms

############################################################
# L1 Global Trigger Emulation: ML-score seeds
############################################################

from L1Trigger.Phase2L1GT.l1tGTAlgoBlockProducer_cff import algorithms

from L1Trigger.Phase2L1GT.l1GTScoreProducer_cfi import l1tGTScoreProducer
from L1Trigger.Phase2L1GT.l1tGTScoreCond_cfi import l1tGTScoreCond

# Each model is one L1GTScoreProducer instance (own modelPath, own emulator .so).
# Each working point is one L1GTScoreCond on that output (pass: score > minScore)
# and one GT path. The model output is the linear logit on the firmware's 1/1024 grid.
#
# Working points: Loose / Medium / Tight = 50 / 20 / 10 kHz seed rate, i.e. the
# lowest threshold with rate <= target on 995040 Phase-2 MinBias PU200 events
# (/eos/user/s/stella/L1GT_minbias_nano/1M), rate = 40 MHz x MinBias efficiency
# (TopoFlow CROSSING_RATE_KHZ convention). Calibrated 2026-11-26.
#
#   seed                        thr      rate[kHz]  eff HH4b  eff HH->bbtautau
#   pEventTaggerHH4b_Loose      3.9756   50.0       0.776     0.662
#   pEventTaggerHH4b_Medium     5.5186   20.0       0.647     0.502
#   pEventTaggerHH4b_Tight      6.7988   10.0       0.530     0.381
#   pEventTaggerHH2b2tau_Loose  3.8242   50.0       0.576     0.821
#   pEventTaggerHH2b2tau_Medium 4.9502   20.0       0.452     0.734
#   pEventTaggerHH2b2tau_Tight  5.6816   10.0       0.380     0.658
#
# (eff HH4b: 50k CMSSW L1 nano; eff HH->bbtautau: TopoFlow test set, 9820 events)


def _addWorkingPoints(producerLabel, producer, prefix, thresholds):
    """One condition + GT path per working point, all sharing the producer."""
    for wp, thr in thresholds.items():
        cond = l1tGTScoreCond.clone(src = cms.InputTag(producerLabel), minScore = cms.double(thr))
        globals()[f"{prefix}_{wp}Cond"] = cond
        globals()[f"p{prefix}_{wp}"] = cms.Path(cond, cms.Task(producer))
        algorithms.append(cms.PSet(expression = cms.string(f"p{prefix}_{wp}")))


####### Event tagger (TopoFlow/event_tagger, deepsets, HH4b vs MinBias) ###########

_addWorkingPoints("l1tGTScoreProducer", l1tGTScoreProducer, "EventTaggerHH4b", {
    "Loose":  3.9755859375,   # 4071/1024
    "Medium": 5.5185546875,   # 5651/1024
    "Tight":  6.798828125,    # 6962/1024
})

####### Event tagger (TopoFlow/event_tagger, deepsets, HH->bbtautau vs MinBias) ###
# Same 62 inputs as the HH4b tagger, so the input definition is inherited.

l1tGTScoreProducerHH2b2tau = l1tGTScoreProducer.clone(
    modelPath = cms.string("L1Trigger/Phase2L1GT/data/triggermodel_hh2b2tau/metadata.json"),
)

_addWorkingPoints("l1tGTScoreProducerHH2b2tau", l1tGTScoreProducerHH2b2tau, "EventTaggerHH2b2tau", {
    "Loose":  3.82421875,     # 3916/1024
    "Medium": 4.9501953125,   # 5069/1024
    "Tight":  5.681640625,    # 5818/1024
})
