import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing

from L1Trigger.Phase2L1GT.l1tGTScales import scale_parameter



process = cms.Process("DecisionValidation")

options = VarParsing.VarParsing()
options.register("inputFile", 
                 "/eos/cms/store/group/dpg_trigger/comm_trigger/L1Trigger/roward/phase2/menu/ntuples/Spring24/170X1004/v45/GluGluToHHTo4B_node_SM_TuneCP5_14TeV-amcatnlo-pythia8/GluGluToHHTo4B_Spring24_200PU_V45_reL1wTT_170X1004/261006_232436/0000/output_Phase2_L1T_11.root",
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string, "L1Nano ntuple")
options.register("outputFile", "decisions.txt",
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string, "score dump")
options.register("scoresFile", "scores.root",
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.string, "EDM output with the score product")
options.register("maxEvents", 10,
                 VarParsing.VarParsing.multiplicity.singleton,
                 VarParsing.VarParsing.varType.int, "events to validate")
options.parseArguments()

process.source = cms.Source("EmptySource")
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.options = cms.untracked.PSet(
    numberOfThreads=cms.untracked.uint32(1),
    numberOfStreams=cms.untracked.uint32(1),
)

process.MessageLogger = cms.Service(
    "MessageLogger",
    threshold=cms.untracked.string("WARNING"),
    categories=cms.untracked.vstring("L1GTDecision"),
    L1GTDecision=cms.untracked.PSet(limit=cms.untracked.int32(5)),
)

process.l1tGTProducer = cms.EDProducer(
    "L1GTNtupleSource",
    scales=scale_parameter,
    filename=cms.string(options.inputFile),
)

from L1Trigger.Phase2L1GT.l1GTScoreProducer_cfi import l1tGTScoreProducer

process.l1tGTScoreProducer = l1tGTScoreProducer.clone()

# score product is unlabeled (one model per module instance)
process.decisionDump = cms.EDAnalyzer(
    "L1GTDecisionDump",
    names=cms.vstring("hh4b_minbias"),
    scores=cms.VInputTag("l1tGTScoreProducer"),
    filename=cms.string(options.outputFile),
)

process.scores = cms.OutputModule(
    "PoolOutputModule",
    fileName=cms.untracked.string(options.scoresFile),
    outputCommands=cms.untracked.vstring("keep *_l1tGTScoreProducer_*_*"),
)

process.p = cms.Path(
    process.l1tGTProducer + process.l1tGTScoreProducer + process.decisionDump
)
process.o = cms.EndPath(process.scores)
