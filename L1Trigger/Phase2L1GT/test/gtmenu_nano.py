"""Phase-2 L1 emulation + P2GT menu (incl. the ML seed) -> one flat NanoAOD file.

Per event the output holds:
  L1GTScore_score             HH4b event-tagger logit (L1GTScoreProducer)
  L1GTScoreHH2b2tau_score     HH->bbtautau event-tagger logit (L1GTScoreProducerHH2b2tau)
  L1GTScoreInputs_<feature>   the 62 raw model inputs, named as in the training
                              (TopoFlow/event_tagger RAW_FEATURE_NAMES)
  L1_<seed>_final             P2GT algo-block decision of every menu seed,
                              e.g. L1_pEventTaggerHH4b_<Loose,Medium,Tight>_final, L1_pEventTaggerHH2b2tau_<WP>_final
  run, luminosityBlock, event

    cmsRun L1Trigger/Phase2L1GT/test/gtmenu_nano.py [inputFiles=a.root,b.root]
        [inputFiles_load=files.txt] [outputFile=out.root] [maxEvents=N] [threads=N] [menu=v0p0_2026]
"""

import FWCore.ParameterSet.Config as cms

from Configuration.Eras.Era_Phase2C17I13M9_cff import Phase2C17I13M9
from Configuration.AlCa.GlobalTag import GlobalTag

from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing("analysis")
options.register("menu", "v0p0_2026", VarParsing.multiplicity.singleton, VarParsing.varType.string,
                 'GT menu: "v0p0_2026" or "step1_2024" (both contain the ML-seed working points)')
options.register("threads", 8, VarParsing.multiplicity.singleton, VarParsing.varType.int, "number of threads")
options.setDefault("maxEvents", 1000)
options.setDefault("outputFile", "l1t_menu_scores_nano.root")
options.parseArguments()

MENU = options.menu
MAX_EVENTS = options.maxEvents
OUTPUT = options.outputFile
DEFAULT_INPUT = [
    "file:/eos/cms/store/mc/Phase2Spring24DIGIRECOMiniAOD/TTTo2L2Nu_TuneCP5_14TeV-powheg-pythia8/GEN-SIM-DIGI-RAW-MINIAOD/PU200_Trk1GeV_140X_mcRun4_realistic_v4-v1/2810000/3b081cbc-6a4e-429a-a2d5-be0241900a26.root"
]

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
process.load(f"L1Trigger.Configuration.Phase2GTMenus.SeedDefinitions.{MENU}.l1tGTMenu_cff")
process.load("Configuration.StandardSequences.EndOfProcess_cff")
process.load("Configuration.StandardSequences.FrontierConditions_GlobalTag_cff")
process.load("CalibCalorimetry.CaloTPG.CaloTPGTranscoder_cfi")

process.GlobalTag = GlobalTag(process.GlobalTag, "auto:phase2_realistic_T35", "")

# The input is a MINIAOD: the PixelDigiSimLink collection produced by the
# mixing module (mix:Tracker) is not stored, but the DIGI-step copy is.
process.TTClusterAssociatorFromPixelDigis.digiSimLinks = cms.InputTag("simSiPixelDigis", "Tracker")

process.source = cms.Source(
    "PoolSource",
    fileNames=cms.untracked.vstring(*(options.inputFiles or DEFAULT_INPUT)),
    inputCommands=cms.untracked.vstring(
        "keep *",
        "drop l1tPFJets_*_*_*",
        "drop l1tTrackerMuons_l1tTkMuonsGmt*_*_HLT",
        # HLT-path products are not used by the L1 emulation, and their branch
        # content varies between files of a dataset (-> MismatchedInputFiles)
        "drop *_hlt*_*_*",
    )
)

process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(MAX_EVENTS))

process.options = cms.untracked.PSet(
    wantSummary=cms.untracked.bool(True),
    numberOfThreads=cms.untracked.uint32(options.threads),
    numberOfStreams=cms.untracked.uint32(0)
)

process.MessageLogger.cerr.FwkReport.reportEvery = 100

# Phase-2 L1 emulation
process.L1TrackTrigger_step = cms.Path(process.L1TrackTrigger)
process.L1simulation_step = cms.Path(process.SimL1Emulator)
process.Phase2L1GTProducer = cms.Path(process.l1tGTProducerSequence)

# GT menu seeds (the ML seed path runs l1tGTScoreProducer from the menu) and the algo block
from L1Trigger.Phase2L1GT.l1tGTAlgoBlockProducer_cff import collectAlgorithmPaths

process.Phase2L1GTAlgoBlock = cms.Path(process.l1tGTAlgoBlockProducerSequence)

# ---- NanoAOD output: scores, model inputs, L1 decisions ----
process.l1tP2GTTrigConvert = cms.EDProducer(
    "P2GTTriggerResultsConverter",
    src=cms.InputTag("l1tGTAlgoBlockProducer"),
    prefix=cms.string("L1_"),
    decision=cms.string("final"),
)

process.l1tGTScoreTable = cms.EDProducer(
    "L1GTScoreTableProducer",
    src=cms.InputTag("l1tGTScoreProducer"),
    name=cms.string("L1GTScore"),
    doc=cms.string("event tagger output (linear logit)"),
    columns=cms.vstring("score"),
)

# input column names = training RAW_FEATURE_NAMES (same order as the producer)
_jetFeatures = ["pT", "eta", "phi", "bTagScore", "cTagScore", "udsTagScore",
                "tau_pTagScore", "tau_nTagScore", "eTagScore", "muTagScore"]
process.l1tGTScoreInputsTable = cms.EDProducer(
    "L1GTScoreTableProducer",
    src=cms.InputTag("l1tGTScoreProducer", "inputs"),
    name=cms.string("L1GTScoreInputs"),
    doc=cms.string("event tagger raw GT inputs"),
    columns=cms.vstring(
        *[f"j{i}_{f}" for i in range(6) for f in _jetFeatures],
        "ht_scalarSumPT", "met_pT",
    ),
)

# second model (HH->bbtautau tagger): same inputs, so only its score is stored
process.l1tGTScoreHH2b2tauTable = process.l1tGTScoreTable.clone(
    src=cms.InputTag("l1tGTScoreProducerHH2b2tau"),
    name=cms.string("L1GTScoreHH2b2tau"),
    doc=cms.string("HH->bbtautau event tagger output (linear logit)"),
)

process.nanoTables = cms.Task(
    process.l1tP2GTTrigConvert, process.l1tGTScoreTable, process.l1tGTScoreInputsTable,
    process.l1tGTScoreHH2b2tauTable,
)

process.nanoOutput = cms.OutputModule(
    "NanoAODOutputModule",
    fileName=cms.untracked.string(OUTPUT),
    compressionAlgorithm=cms.untracked.string("LZMA"),
    compressionLevel=cms.untracked.int32(9),
    outputCommands=cms.untracked.vstring(
        "drop *",
        "keep nanoaodFlatTable_l1tGTScore*Table_*_*",
        "keep edmTriggerResults_l1tP2GTTrigConvert_*_*",
    ),
)
process.nanoOutput_step = cms.EndPath(process.nanoOutput, process.nanoTables)

process.endjob_step = cms.EndPath(process.endOfProcess)

process.schedule = cms.Schedule(
    process.L1TrackTrigger_step,
    process.L1simulation_step,
    process.Phase2L1GTProducer,
    *collectAlgorithmPaths(process),
    process.Phase2L1GTAlgoBlock,
    process.endjob_step,
    process.nanoOutput_step,
)
