#include "FWCore/Framework/interface/ConsumesCollector.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/Utilities/interface/EDMException.h"
#include "FWCore/Utilities/interface/FileInPath.h"

#include "DataFormats/L1TParticleFlow/interface/PFJet.h"
#include "DataFormats/L1Trigger/interface/P2GTCandidate.h"

#include "CommonTools/Utils/interface/StringObjectFunction.h"
#include "hls4ml/emulator.h"

#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>

#include <algorithm>
#include <any>
#include <cmath>
#include <memory>
#include <numeric>
#include <string>
#include <vector>

using namespace l1t;

namespace {

  // Type-erased model input block: fills nObjects x nFeatures floats into the input vector.
  class InputBlock {
  public:
    virtual ~InputBlock() = default;
    virtual void fill(const edm::Event& event, std::vector<float>& input, size_t& pos) const = 0;
    virtual size_t size() const = 0;
  };

  template <typename T>
  class TypedInputBlock : public InputBlock {
  public:
    TypedInputBlock(const edm::ParameterSet& pset, edm::ConsumesCollector cc)
        : token_(cc.consumes<std::vector<T>>(pset.getParameter<edm::InputTag>("tag"))),
          nObjects_(pset.getParameter<unsigned int>("nObjects")) {
      const std::string sortBy = pset.getParameter<std::string>("sortBy");
      if (!sortBy.empty())
        sortKey_ = std::make_unique<StringObjectFunction<T>>(sortBy);
      const std::string reduce = pset.getParameter<std::string>("reduce");
      if (reduce == "sum")
        sum_ = true;
      else if (reduce == "pairMass")
        pairMass_ = true;
      else if (!reduce.empty())
        throw edm::Exception(edm::errors::Configuration)
            << "L1GTScoreProducer: unknown reduce '" << reduce << "' (expected '', 'sum' or 'pairMass')";
      for (const std::string& feature : pset.getParameter<std::vector<std::string>>("features")) {
        if (pairMass_ && feature == "valid")
          throw edm::Exception(edm::errors::Configuration)
              << "L1GTScoreProducer: 'valid' is not allowed with reduce = 'pairMass'";
        presence_.push_back(feature == "valid");
        // "valid" needs no getter: it is 1 for a real object, 0 for a padded slot
        getters_.emplace_back(feature == "valid" ? std::string("0") : feature);
      }
      if (pairMass_ && getters_.size() != 3)
        throw edm::Exception(edm::errors::Configuration)
            << "L1GTScoreProducer: reduce = 'pairMass' needs exactly 3 features (pt, eta, phi), got "
            << getters_.size();
    }

    size_t size() const override {
      if (pairMass_)
        return nObjects_ * (nObjects_ - 1) / 2;
      return (sum_ ? 1 : nObjects_) * getters_.size();
    }

    void fill(const edm::Event& event, std::vector<float>& input, size_t& pos) const override {
      const std::vector<T>& objects = event.get(token_);

      std::vector<size_t> order(objects.size());
      std::iota(order.begin(), order.end(), size_t{0});
      if (sortKey_)
        std::stable_sort(order.begin(), order.end(), [&](size_t a, size_t b) {
          return (*sortKey_)(objects[a]) > (*sortKey_)(objects[b]);
        });

      if (pairMass_) {
        // massless dijet invariant mass for every pair (i<j) of the first nObjects objects:
        // m = sqrt(2 pt_i pt_j (cosh(deta) - cos(dphi))), in the units of the pt feature.
        // Pairs involving a missing object are 0.
        for (size_t i = 0; i < nObjects_; ++i) {
          for (size_t j = i + 1; j < nObjects_; ++j) {
            if (j >= order.size()) {
              input[pos++] = 0.f;
              continue;
            }
            const T& a = objects[order[i]];
            const T& b = objects[order[j]];
            const double m2 = 2. * getters_[0](a) * getters_[0](b) *
                              (std::cosh(getters_[1](a) - getters_[1](b)) - std::cos(getters_[2](a) - getters_[2](b)));
            input[pos++] = m2 > 0. ? std::sqrt(m2) : 0.;
          }
        }
        return;
      }

      if (sum_) {
        // one value per feature: the sum over the first nObjects objects
        const size_t n = std::min<size_t>(nObjects_, order.size());
        for (size_t f = 0; f < getters_.size(); ++f) {
          double total = 0.;
          for (size_t k = 0; k < n; ++k)
            total += presence_[f] ? 1. : getters_[f](objects[order[k]]);
          input[pos++] = total;
        }
        return;
      }

      for (size_t k = 0; k < nObjects_; ++k) {
        for (size_t f = 0; f < getters_.size(); ++f) {
          if (k >= order.size())
            input[pos++] = 0.f;  // 0-padded slot
          else if (presence_[f])
            input[pos++] = 1.f;
          else
            input[pos++] = getters_[f](objects[order[k]]);
        }
      }
    }

  private:
    edm::EDGetTokenT<std::vector<T>> token_;
    unsigned int nObjects_;
    bool sum_ = false;
    bool pairMass_ = false;
    std::unique_ptr<StringObjectFunction<T>> sortKey_;
    std::vector<StringObjectFunction<T>> getters_;
    std::vector<bool> presence_;
  };

  struct EmulatorModel {
    std::unique_ptr<hls4mlEmulator::ModelLoader> loader;
    std::shared_ptr<hls4mlEmulator::Model> model;
    unsigned int nOutputs = 0;

    void load(const std::string& path, unsigned int nOutputs_) {
      // ModelLoader appends the ".so" suffix itself
      std::string libName = path;
      const std::string suffix = ".so";
      if (libName.size() > suffix.size() &&
          libName.compare(libName.size() - suffix.size(), suffix.size(), suffix) == 0)
        libName.resize(libName.size() - suffix.size());
      loader = std::make_unique<hls4mlEmulator::ModelLoader>(libName);
      model = loader->load_model();
      nOutputs = nOutputs_;
    }

    std::vector<float> evaluate(std::vector<float>& input) {
      std::vector<float> output(nOutputs, 0.f);
      model->prepare_input(std::any(input.data()));
      model->predict();
      model->read_result(std::any(output.data()));
      return output;
    }
  };

}  // namespace

class L1GTScoreProducer : public edm::stream::EDProducer<> {
public:
  explicit L1GTScoreProducer(const edm::ParameterSet&);
  ~L1GTScoreProducer() override = default;

  static void fillDescriptions(edm::ConfigurationDescriptions&);

private:
  void produce(edm::Event&, const edm::EventSetup&) override;

  EmulatorModel emu_;
  std::vector<std::unique_ptr<InputBlock>> inputs_;
  size_t nFeatures_ = 0;
};

L1GTScoreProducer::L1GTScoreProducer(const edm::ParameterSet& config) {
  const std::string metadataPath = edm::FileInPath(config.getParameter<std::string>("modelPath")).fullPath();
  const std::string workspace = metadataPath.substr(0, metadataPath.rfind('/'));

  boost::property_tree::ptree metadata;
  boost::property_tree::read_json(metadataPath, metadata);
  const std::string name = metadata.get<std::string>("name");

  for (const edm::ParameterSet& inputPSet : config.getParameter<std::vector<edm::ParameterSet>>("inputs")) {
    const std::string type = inputPSet.getParameter<std::string>("type");
    std::unique_ptr<InputBlock> block;
    if (type == "P2GTCandidate")
      block = std::make_unique<TypedInputBlock<P2GTCandidate>>(inputPSet, consumesCollector());
    else if (type == "PFJet")
      block = std::make_unique<TypedInputBlock<PFJet>>(inputPSet, consumesCollector());
    else
      throw edm::Exception(edm::errors::Configuration)
          << "L1GTScoreProducer: unknown input type '" << type << "' (expected P2GTCandidate or PFJet)";
    nFeatures_ += block->size();
    inputs_.push_back(std::move(block));
  }

  // The emulator reads exactly n_inputs floats from the buffer: refuse to run on a mismatch.
  const auto nModelInputs = metadata.get_optional<size_t>("n_inputs");
  if (nModelInputs && *nModelInputs != nFeatures_)
    throw edm::Exception(edm::errors::Configuration)
        << "L1GTScoreProducer: configured inputs give " << nFeatures_ << " features but model '" << name
        << "' expects n_inputs = " << *nModelInputs << " (" << metadataPath << ")";

  emu_.load(workspace + "/emulator/" + name + "/" + name, metadata.get<unsigned int>("n_outputs", 1));

  produces<std::vector<float>>();
  produces<std::vector<float>>("inputs");  // flattened model input (sorted, 0-padded)
}

void L1GTScoreProducer::produce(edm::Event& event, const edm::EventSetup&) {
  std::vector<float> input(nFeatures_, 0.f);
  size_t pos = 0;
  for (const auto& block : inputs_)
    block->fill(event, input, pos);

  auto scores = std::make_unique<std::vector<float>>(emu_.evaluate(input));
  event.put(std::make_unique<std::vector<float>>(std::move(input)), "inputs");
  event.put(std::move(scores));
}

void L1GTScoreProducer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<std::string>("modelPath")->setComment(
      "TriggerModel metadata.json (emulator/<name>/<name>.so sits next to it)");
  edm::ParameterSetDescription inputDesc;
  inputDesc.add<std::string>("type", "P2GTCandidate")->setComment("collection element type: P2GTCandidate or PFJet");
  inputDesc.add<edm::InputTag>("tag");
  inputDesc.add<unsigned int>("nObjects", 1);
  inputDesc.add<std::string>("sortBy", "")->setComment(
      "StringObjectFunction expression to sort by (descending); empty = keep collection order");
  inputDesc.add<std::string>("reduce", "")->setComment(
      "'' = one entry per object (0-padded to nObjects); 'sum' = sum each feature over the first nObjects; "
      "'pairMass' = dijet invariant mass of every pair of the first nObjects (features = pt, eta, phi)");
  inputDesc.add<std::vector<std::string>>("features")->setComment(
      "StringObjectFunction expressions on the element type, or 'valid'");
  desc.addVPSet("inputs", inputDesc, std::vector<edm::ParameterSet>());
  descriptions.add("l1tGTScoreProducer", desc);
}

DEFINE_FWK_MODULE(L1GTScoreProducer);
