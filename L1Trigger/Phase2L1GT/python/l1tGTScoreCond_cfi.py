import FWCore.ParameterSet.Config as cms

# GT condition on an L1GTScoreProducer output: set minScore and/or maxScore.
l1tGTScoreCond = cms.EDFilter(
    "L1GTScoreCond",
    src=cms.InputTag("l1tGTScoreProducer"),
    index=cms.uint32(0),
)
