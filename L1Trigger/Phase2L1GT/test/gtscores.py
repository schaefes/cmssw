
import FWCore.ParameterSet.Config as cms

from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9
from Configuration.AlCa.GlobalTag import GlobalTag

process = cms.Process("L1P2GT", Phase2C17I13M9)

process.load("Configuration.StandardSequences.Services_cff")
process.load("SimGeneral.HepPDTESSource.pythiapdt_cfi")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.load("Configuration.EventContent.EventContent_cff")
process.load("SimGeneral.MixingModule.mixNoPU_cfi")
process.load("Configuration.Geometry.GeometryExtendedRun4D121Reco_cff")
process.load("Geometry.HcalTowerAlgo.HcalTrigTowerGeometryESProducer_cfi")
process.load("Configuration.StandardSequences.MagneticField_cff")
process.load("Configuration.StandardSequences.L1TrackTrigger_cff")
process.load("Configuration.StandardSequences.SimL1Emulator_cff")
process.load("Configuration.StandardSequences.SimPhase2L1GlobalTriggerEmulator_cff")
process.load("L1Trigger.Configuration.Phase2GTMenus.SeedDefinitions.v0p0_2026.l1tGTMenu_cff")
process.load("Configuration.StandardSequences.EndOfProcess_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("CalibCalorimetry.CaloTPG.CaloTPGTranscoder_cfi")

process.GlobalTag = GlobalTag(
    process.GlobalTag,
    "auto:phase2_realistic_T35",
    ""
)

# The input is a MINIAOD: the PixelDigiSimLink collection produced by the
# mixing module (mix:Tracker) is not stored, but the DIGI-step copy is.
process.TTClusterAssociatorFromPixelDigis.digiSimLinks = cms.InputTag(
    "simSiPixelDigis", "Tracker"
)

process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(
        "file:/eos/cms/store/mc/Phase2Spring24DIGIRECOMiniAOD/TTTo2L2Nu_TuneCP5_14TeV-powheg-pythia8/GEN-SIM-DIGI-RAW-MINIAOD/PU200_Trk1GeV_140X_mcRun4_realistic_v4-v1/2810000/3b081cbc-6a4e-429a-a2d5-be0241900a26.root"
        # "file:/eos/cms/store/group/dpg_trigger/comm_trigger/L1Trigger/roward/phase2/menu/ntuples/Spring24/170X1004/v45/GluGluToHHTo4B_node_SM_TuneCP5_14TeV-amcatnlo-pythia8/GluGluToHHTo4B_Spring24_200PU_V45_reL1wTT_170X1004/261006_232436/0000/output_Phase2_L1T_10.root"
    ),
    inputCommands=cms.untracked.vstring(
        "keep *",
        "drop l1tPFJets_*_*_*",
        "drop l1tTrackerMuons_l1tTkMuonsGmt*_*_HLT"
    )
)

process.maxEvents = cms.untracked.PSet(
    input=cms.untracked.int32(1000)
)

process.options = cms.untracked.PSet(
    wantSummary=cms.untracked.bool(True),
    numberOfThreads=cms.untracked.uint32(8),
    numberOfStreams=cms.untracked.uint32(0)
)

process.MessageLogger.cerr.FwkReport.reportEvery = 100

# Phase-2 L1 emulation paths
process.L1TrackTrigger_step = cms.Path(
    process.L1TrackTrigger
)

process.L1simulation_step = cms.Path(
    process.SimL1Emulator
)

process.Phase2L1GTProducer = cms.Path(
    process.l1tGTProducerSequence
)

# Model score producer: TopoFlow/event_tagger deepsets model
# (62 raw inputs + 6 dijet masses = 68; needs a model trained with n_inputs = 68)
process.l1tGTScoreProducer = cms.EDProducer(
    "L1GTScoreProducer",
    modelPath=cms.string(
        "L1Trigger/Phase2L1GT/data/triggermodel/metadata.json"
    ),
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
        cms.PSet(  # 6 pairwise dijet masses of the 4 leading L1puppiJetSC4NG:
            # m(j0j1), m(j0j2), m(j0j3), m(j1j2), m(j1j3), m(j2j3), massless jets,
            # in hwPt units (LSB 0.25 GeV); 0 if a jet is missing
            type=cms.string("PFJet"),
            tag=cms.InputTag("l1tSC4NGJetProducer", "l1tSC4NGJets"),
            nObjects=cms.uint32(4),
            sortBy=cms.string("hwPt"),
            reduce=cms.string("pairMass"),
            # pt, eta, phi: eta/phi hw -> rad (ETAPHI_LSB = pi/720)
            features=cms.vstring(
                "hwPt",
                "hwEta*3.141592653589793/720",
                "hwPhi*3.141592653589793/720",
            ),
        ),
    )
)

process.pScore = cms.Path(
    process.l1tGTScoreProducer
)

# ROOT output containing the score product
process.scoreOutput = cms.OutputModule(
    "PoolOutputModule",
    fileName=cms.untracked.string("scores.root"),
    outputCommands=cms.untracked.vstring(
        "drop *",
        "keep *_l1tGTScoreProducer_*_*",
        # model inputs
        "keep *_l1tSC4NGJetProducer_l1tSC4NGJets_*",
        "keep *_l1tSC4PFL1PuppiExtendedCorrectedEmulator_*_*",
        "keep *_l1tGTProducer_CL2EtSum_*",
    ),
    dataset=cms.untracked.PSet(
        dataTier=cms.untracked.string("NANOAOD"),
        filterName=cms.untracked.string("")
    )
)

process.scoreOutput_step = cms.EndPath(
    process.scoreOutput
)

# Retain the standard end-of-process path
process.endjob_step = cms.EndPath(
    process.endOfProcess
)


# GT menu seed paths (incl. pEventTagger0p95 from l1tGTMenu_MLSeeds_cff)
from L1Trigger.Phase2L1GT.l1tGTAlgoBlockProducer_cff import collectAlgorithmPaths

process.schedule = cms.Schedule(
    process.L1TrackTrigger_step,
    process.L1simulation_step,
    process.Phase2L1GTProducer,
    process.pScore,
    *collectAlgorithmPaths(process),
    process.endjob_step,
    process.scoreOutput_step
)
