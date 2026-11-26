import FWCore.ParameterSet.Config as cms

############################################################
# L1 Global Trigger Emulation: ML-score seeds
############################################################

from L1Trigger.Phase2L1GT.l1tGTAlgoBlockProducer_cff import algorithms

from L1Trigger.Phase2L1GT.l1GTScoreProducer_cfi import l1tGTScoreProducer
from L1Trigger.Phase2L1GT.l1tGTScoreCond_cfi import l1tGTScoreCond

####### Event tagger (TopoFlow/event_tagger, deepsets, HH4b vs MinBias) ###########
# The model output is the linear logit (0.0 == sigmoid 0.5). The threshold is the
# deployment decision of L1Trigger/Phase2L1GT/data/triggermodel/metadata.json.

EventTagger0p95 = l1tGTScoreCond.clone(
    src = cms.InputTag("l1tGTScoreProducer"),
    minScore = cms.double(0.95),
)
pEventTagger0p95 = cms.Path(EventTagger0p95, cms.Task(l1tGTScoreProducer))
algorithms.append(cms.PSet(expression = cms.string("pEventTagger0p95")))
