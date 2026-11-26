"""NanoAOD tables of the L1GTScoreProducer outputs (ML-seed models of the GT menu).

Per event:
  L1GTScore_score            HH4b event-tagger logit         (l1tGTScoreProducer)
  L1GTScoreHH2b2tau_score    HH->bbtautau event-tagger logit (l1tGTScoreProducerHH2b2tau)
  L1GTScoreInputs_<feature>  the 62 raw GT model inputs (shared by both models)

The L1_pEventTagger<Model>_<WP>_final decisions come from the standard
P2GTTriggerResultsConverter of the Phase-2 L1 nano. Use with cmsDriver as

  --customise L1Trigger/Phase2L1GT/l1tGTScoreNano_cff.addL1GTScoreTables
"""

import FWCore.ParameterSet.Config as cms

# input column names = training RAW_FEATURE_NAMES (same order as the producer)
_jetFeatures = ["pT", "eta", "phi", "bTagScore", "cTagScore", "udsTagScore",
                "tau_pTagScore", "tau_nTagScore", "eTagScore", "muTagScore"]
_inputColumns = [f"j{i}_{f}" for i in range(6) for f in _jetFeatures] + ["ht_scalarSumPT", "met_pT"]

# (producer label, table name, doc) of every score to store
_scoreTables = [
    ("l1tGTScoreProducer", "L1GTScore", "HH4b event tagger output (linear logit)"),
    ("l1tGTScoreProducerHH2b2tau", "L1GTScoreHH2b2tau", "HH->bbtautau event tagger output (linear logit)"),
]


def addL1GTScoreTables(process):
    """Add the score (+ input) tables of the ML-seed producers present in the process."""
    tables = []
    for producer, name, doc in _scoreTables:
        if not hasattr(process, producer):  # model not in the loaded GT menu
            continue
        label = f"{name[0].lower()}{name[1:]}Table"  # e.g. l1GTScoreTable: kept by nanoaodFlatTable_*Table_*_*
        setattr(process, label, cms.EDProducer(
            "L1GTScoreTableProducer",
            src=cms.InputTag(producer),
            name=cms.string(name),
            doc=cms.string(doc),
            columns=cms.vstring("score"),
        ))
        tables.append(getattr(process, label))

    if hasattr(process, "l1tGTScoreProducer"):
        process.l1GTScoreInputsTable = cms.EDProducer(
            "L1GTScoreTableProducer",
            src=cms.InputTag("l1tGTScoreProducer", "inputs"),
            name=cms.string("L1GTScoreInputs"),
            doc=cms.string("event tagger raw GT inputs"),
            columns=cms.vstring(*_inputColumns),
        )
        tables.append(process.l1GTScoreInputsTable)

    if not tables:
        return process
    process.l1GTScoreTablesTask = cms.Task(*tables)
    if process.schedule is not None:
        process.schedule.associate(process.l1GTScoreTablesTask)
    else:  # no explicit schedule: run them via an EndPath
        process.l1GTScoreTables_step = cms.EndPath(process.l1GTScoreTablesTask)
    return process
