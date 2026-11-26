// evalbin <model path without .so> <in.f32> <out.f32>: rows of 62 float32 -> one float32 score per row
#include "hls4ml/emulator.h"
#include <any>
#include <cstdio>
#include <vector>
int main(int argc, char** argv) {
  hls4mlEmulator::ModelLoader loader(argv[1]);
  auto model = loader.load_model();
  FILE* in = fopen(argv[2], "rb"); FILE* out = fopen(argv[3], "wb");
  std::vector<float> x(62); float y; long n = 0;
  while (fread(x.data(), sizeof(float), 62, in) == 62) {
    model->prepare_input(std::any(x.data())); model->predict(); model->read_result(std::any(&y));
    fwrite(&y, sizeof(float), 1, out); ++n;
  }
  fclose(in); fclose(out); fprintf(stderr, "%ld events\n", n);
}
