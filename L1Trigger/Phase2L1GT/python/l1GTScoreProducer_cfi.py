import FWCore.ParameterSet.Config as cms

l1tGTScoreProducer = cms.EDProducer(
    "L1GTScoreProducer",
    modelPath=cms.string("L1Trigger/Phase2L1GT/data/triggermodel/metadata.json"),
    inputs=cms.VPSet(
        # Raw GT hardware integers, built exactly like the training loader
        # (TopoFlow/event_tagger: src/event_tagger/datasets/event_tagger_loader.py).
        # The hw -> GeV/rad conversion is traced into the emulator .so.
        cms.PSet(  # 6 leading L1puppiJetSC4NG: hw pT/eta/phi + 7 tag scores
            type=cms.string("PFJet"),
            tag=cms.InputTag("l1tSC4NGJetProducer", "l1tSC4NGJets"),
            nObjects=cms.uint32(6),
            sortBy=cms.string("hwPt"),
            features=cms.vstring(
                "hwPt", "hwEta", "hwPhi",
                # ap_ufixed<8,1> scores: x 2**7 gives the raw integer exactly
                'getTagScore("b")*128', 'getTagScore("c")*128', 'getTagScore("uds")*128',
                'getTagScore("tau_p")*128', 'getTagScore("tau_n")*128',
                'getTagScore("e")*128', 'getTagScore("mu")*128',
            ),
        ),
        cms.PSet(  # HT: GT CL2HtSum scalar sum (pT>30, |eta|<2.4 SC4 jets, htmht emulator)
            type=cms.string("P2GTCandidate"),
            tag=cms.InputTag("l1tGTProducer", "CL2HtSum"),
            nObjects=cms.uint32(1),
            features=cms.vstring("hwScalarSumPT_toInt"),
        ),
        cms.PSet(  # MET: L1puppiMET (l1tMETPFProducer) hw pT
            type=cms.string("P2GTCandidate"),
            tag=cms.InputTag("l1tGTProducer", "CL2EtSum"),
            nObjects=cms.uint32(1),
            features=cms.vstring("hwPT_toInt"),
        ),
    ),
)
