/**
 * L1GTScoreCond: GT condition on an ML model score.
 *
 * Reads the score vector produced by L1GTScoreProducer and passes the event if
 * the selected output lies in (minScore, maxScore]. Either bound may be omitted.
 * Used as the filter of a GT seed path, like the L1GT*ObjectCond filters; it
 * contributes no trigger objects to the algo block, only the decision.
 */

#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/global/EDFilter.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDMException.h"

#include <optional>
#include <vector>

class L1GTScoreCond : public edm::global::EDFilter<> {
public:
  explicit L1GTScoreCond(const edm::ParameterSet&);
  ~L1GTScoreCond() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  bool filter(edm::StreamID, edm::Event&, const edm::EventSetup&) const override;

  const edm::EDGetTokenT<std::vector<float>> token_;
  const unsigned int index_;
  const std::optional<double> minScore_;
  const std::optional<double> maxScore_;
};

namespace {
  std::optional<double> optionalDouble(const edm::ParameterSet& config, const std::string& name) {
    if (config.existsAs<double>(name))
      return config.getParameter<double>(name);
    return std::nullopt;
  }
}  // namespace

L1GTScoreCond::L1GTScoreCond(const edm::ParameterSet& config)
    : token_(consumes<std::vector<float>>(config.getParameter<edm::InputTag>("src"))),
      index_(config.getParameter<unsigned int>("index")),
      minScore_(optionalDouble(config, "minScore")),
      maxScore_(optionalDouble(config, "maxScore")) {
  if (!minScore_ && !maxScore_)
    throw edm::Exception(edm::errors::Configuration) << "L1GTScoreCond: set minScore and/or maxScore";
}

bool L1GTScoreCond::filter(edm::StreamID, edm::Event& event, const edm::EventSetup&) const {
  const std::vector<float>& scores = event.get(token_);
  if (index_ >= scores.size())
    throw edm::Exception(edm::errors::LogicError)
        << "L1GTScoreCond: score index " << index_ << " out of range (model has " << scores.size() << " outputs)";

  const double score = scores[index_];
  if (minScore_ && !(score > *minScore_))
    return false;
  if (maxScore_ && !(score <= *maxScore_))
    return false;
  return true;
}

void L1GTScoreCond::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("src", edm::InputTag("l1tGTScoreProducer"))
      ->setComment("std::vector<float> of model outputs from L1GTScoreProducer");
  desc.add<unsigned int>("index", 0)->setComment("model output to cut on");
  desc.addOptional<double>("minScore")->setComment("pass if score > minScore");
  desc.addOptional<double>("maxScore")->setComment("pass if score <= maxScore");
  descriptions.add("l1tGTScoreCond", desc);
}

DEFINE_FWK_MODULE(L1GTScoreCond);
