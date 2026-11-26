/**
 * L1GTScoreTableProducer: writes a std::vector<float> (e.g. the L1GTScoreProducer
 * scores or its flattened model inputs) as a singleton NanoAOD FlatTable, one
 * column per vector entry.
 */

#include "DataFormats/NanoAOD/interface/FlatTable.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDMException.h"

#include <memory>
#include <string>
#include <vector>

class L1GTScoreTableProducer : public edm::global::EDProducer<> {
public:
  explicit L1GTScoreTableProducer(const edm::ParameterSet&);
  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  void produce(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

  const edm::EDGetTokenT<std::vector<float>> token_;
  const std::string name_;
  const std::string doc_;
  const std::vector<std::string> columns_;
  const int precision_;
};

L1GTScoreTableProducer::L1GTScoreTableProducer(const edm::ParameterSet& config)
    : token_(consumes<std::vector<float>>(config.getParameter<edm::InputTag>("src"))),
      name_(config.getParameter<std::string>("name")),
      doc_(config.getParameter<std::string>("doc")),
      columns_(config.getParameter<std::vector<std::string>>("columns")),
      precision_(config.getParameter<int>("precision")) {
  if (columns_.empty())
    throw edm::Exception(edm::errors::Configuration) << "L1GTScoreTableProducer: 'columns' is empty";
  produces<nanoaod::FlatTable>();
}

void L1GTScoreTableProducer::produce(edm::StreamID, edm::Event& event, const edm::EventSetup&) const {
  const std::vector<float>& values = event.get(token_);
  if (values.size() != columns_.size())
    throw edm::Exception(edm::errors::LogicError)
        << "L1GTScoreTableProducer '" << name_ << "': product has " << values.size() << " entries but "
        << columns_.size() << " column names are configured";

  auto table = std::make_unique<nanoaod::FlatTable>(1, name_, true);
  table->setDoc(doc_);
  for (size_t i = 0; i < values.size(); ++i)
    table->addColumnValue<float>(columns_[i], values[i], doc_ + ": " + columns_[i], precision_);
  event.put(std::move(table));
}

void L1GTScoreTableProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src")->setComment("std::vector<float> to store");
  desc.add<std::string>("name")->setComment("table (branch prefix) name");
  desc.add<std::string>("doc", "");
  desc.add<std::vector<std::string>>("columns")->setComment("one column name per vector entry");
  desc.add<int>("precision", -1)->setComment("mantissa bits, -1 = full float precision");
  descriptions.addWithDefaultLabel(desc);
}

DEFINE_FWK_MODULE(L1GTScoreTableProducer);
