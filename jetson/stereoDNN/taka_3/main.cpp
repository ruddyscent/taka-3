// Copyright (c) 2017, NVIDIA CORPORATION. All rights reserved.
// Full license terms provided in LICENSE.md file.

#include "NvCaffeParser.h"
#include "NvInfer.h"
#include <cassert>
#include <chrono>
#include <cuda_runtime_api.h>
#include <cudnn.h>
#include <fstream>
#include <iostream>
#include <opencv2/opencv.hpp>
#include <unordered_map>

#include "networks.h"
#include "redtail_tensorrt_plugins.h"

#define UNUSED(x) ((void)(x))

#define CHECK(status)                                                          \
  do {                                                                         \
    int res = (int)(status);                                                   \
    assert(res == 0);                                                          \
    UNUSED(res);                                                               \
  } while (false)

using namespace nvinfer1;
using namespace redtail::tensorrt;

class Logger : public nvinfer1::ILogger {
public:
  void log(nvinfer1::ILogger::Severity severity, const char *msg) override {
    // Skip info (verbose) messages.
    // if (severity == Severity::kINFO)
    //     return;

    switch (severity) {
    case Severity::kINTERNAL_ERROR:
      std::cerr << "TRT INTERNAL_ERROR: ";
      break;
    case Severity::kERROR:
      std::cerr << "TRT ERROR: ";
      break;
    case Severity::kWARNING:
      std::cerr << "TRT WARNING: ";
      break;
    case Severity::kINFO:
      std::cerr << "TRT INFO: ";
      break;
    default:
      std::cerr << "TRT UNKNOWN: ";
      break;
    }
    std::cerr << msg << std::endl;
  }
};

static Logger gLogger;

class Profiler : public nvinfer1::IProfiler {
public:
  void printLayerTimes() {
    float total_time = 0;
    for (size_t i = 0; i < profile_.size(); i++) {
      printf("%-60.60s %4.3fms\n", profile_[i].first.c_str(),
             profile_[i].second);
      total_time += profile_[i].second;
    }
    printf("All layers  : %4.3f\n", total_time);
  }

protected:
  void reportLayerTime(const char *layerName, float ms) override {
    auto record =
        std::find_if(profile_.begin(), profile_.end(),
                     [&](const Record &r) { return r.first == layerName; });
    if (record == profile_.end())
      profile_.push_back(std::make_pair(layerName, ms));
    else
      record->second = ms;
  }

private:
  using Record = std::pair<std::string, float>;
  std::vector<Record> profile_;
};

static Profiler s_profiler;

std::vector<std::vector<float>> readVideoStream(cv::VideoCapture &cap,
                                                int video_w, int video_h,
                                                int model_w, int model_h) {
  cv::Mat img;
  cap >> img; // get a new frame from video stream

  // 0. Conver to float.
  img.convertTo(img, CV_32F);

  // 1. Separate left and right images.
  const auto roi_left = cv::Rect(0, 0, video_w / 2, video_h);
  auto img_left = img(roi_left);

  const auto roi_right = cv::Rect(video_w / 2, 0, video_w, video_h);
  auto img_right = img(roi_right);

  // 2. Resize.
  cv::resize(img_left, img_left, cv::Size(model_w, model_h), 0, 0,
             cv::INTER_LANCZOS4);
  cv::resize(img_right, img_right, cv::Size(model_w, model_h), 0, 0,
             cv::INTER_LANCZOS4);

  // 3. Convert BGR -> RGB.
  cv::cvtColor(img_left, img_left, CV_BGR2RGB);
  cv::cvtColor(img_left, img_right, CV_BGR2RGB);

  // 4. Convert HWC -> CHW.
  cv::Mat res_left = img_left.reshape(1, model_w * model_h).t();
  cv::Mat res_right = img_right.reshape(1, model_w * model_h).t();

  // 5. Scale.
  res_left /= 255.0;
  res_right /= 255.0;

  auto left = std::vector<float>(
      res_left.ptr<float>(0), res_left.ptr<float>(0) + model_w * model_h * 3);
  auto right = std::vector<float>(
      res_right.ptr<float>(0), res_right.ptr<float>(0) + model_w * model_h * 3);

  auto stereo = std::vector<std::vector<float>>();
  stereo.push_back(left);
  stereo.push_back(right);
  return stereo;
}

std::unordered_map<std::string, Weights>
readWeights(const std::string &filename, DataType data_type) {
  assert(data_type == DataType::kFLOAT || data_type == DataType::kHALF);

  std::unordered_map<std::string, Weights> weights;
  std::ifstream weights_file(filename, std::ios::binary);
  assert(weights_file.is_open());
  while (weights_file.peek() != std::ifstream::traits_type::eof()) {
    std::string name;
    uint32_t count;
    Weights w{data_type, nullptr, 0};
    std::getline(weights_file, name, '\0');
    weights_file.read(reinterpret_cast<char *>(&count), sizeof(uint32_t));
    w.count = count;
    size_t el_size_bytes = data_type == DataType::kFLOAT ? 4 : 2;
    auto p = new uint8_t[count * el_size_bytes];
    weights_file.read(reinterpret_cast<char *>(p), count * el_size_bytes);
    w.values = p;
    assert(weights.find(name) == weights.cend());
    weights[name] = w;
  }
  return weights;
}

void displayImg(std::vector<float> &img, const std::string &window_title, int w,
                int h) {
  auto img_f = cv::Mat(h, 2 * 2 * w, CV_32F, img.data());
  // Same as in KITTI, reduce quantization effects by storing as 16-bit PNG.
  img_f *= 256;
  // resnet18_2D model normalizes disparity using sigmoid, so bring it back to
  // pixels.
  img_f *= w;
  cv::Mat img_u16;
  img_f.convertTo(img_u16, CV_16U);

  cv::imshow(window_title, img_u16);
}

int main(int argc, char **argv) {
  if (argc < 4) {
    printf(
        "\n"
        "Usage  : nvstereo_taka_app[_debug] <input_path> <width> <height> "
        "<path_to_weights_file>\n"
        "where  : input_path is address of input stream\n"
        "         width and height are dimensions of the input stream (e.g. "
        "242 240)\n"
        "         weights file is the output of TensorRT model builder script\n"
        "Example: nvstereo_taka_app udp://localhost:9999 640 360 "
        "trt_weights.bin\n"
        "         ./bin/nvstereo_taka_debug "
        "\"udp://192.168.0.178:9999?overrun_nonfatal=1&fifo_size=1316\" 640 "
        "360 ./models/ResNet-18_2D/TensorRT/trt_weights_fp16.bin\n");
    return 1;
  }

  // The data type of the model: DataType::kFLOAT, DataType::kHALF
  const DataType data_type = DataType::kHALF;

  // Read weights.
  // Note: the weights object lifetime must be at least the same as engine.
  std::string weights_file(argv[4]);
  const auto weights = readWeights(weights_file, data_type);
  printf("Loaded %zu weight sets.\n", weights.size());

  // Input size off ResNet-18 2D
  const int c = 3;
  const int model_h = 513;
  const int model_w = 257;

  // TensorRT pre-built plan file.
  auto trt_plan_file = weights_file + ".plan";
  std::ifstream trt_plan(trt_plan_file, std::ios::binary);

  // Raad the input video stream.
  cv::VideoCapture cap(argv[1], cv::CAP_FFMPEG); // open the video steram
  if (!cap.isOpened())                           // check if we succeeded
    return -1;

  const int video_h = std::stoi(argv[3]);
  const int video_w = std::stoi(argv[2]);
  printf("Using [%d, %d](width, height) as dimensions of input video stream\n",
         video_w, video_h);
  printf("from %s.\n", argv[1]);

  // Note: the plugin_container object lifetime must be at least the same as the
  // engine.
  auto plugin_container = IPluginContainer::create(gLogger);
  ICudaEngine *engine = nullptr;
  // Check if we can load pre-built model from TRT plan file.
  // Currently only ResNet18_2D supports serialization.
  if (trt_plan.good()) {
    printf("Loading TensorRT plan from %s...\n", trt_plan_file.c_str());
    // StereoDnnPluginFactory object is stateless as it adds plugins to
    // corresponding container.
    StereoDnnPluginFactory factory(*plugin_container);
    IRuntime *runtime = createInferRuntime(gLogger);
    // Load the plan.
    std::stringstream model;
    model << trt_plan.rdbuf();
    model.seekg(0, model.beg);
    const auto &model_final = model.str();
    // Deserialize model.
    engine = runtime->deserializeCudaEngine(model_final.c_str(),
                                            model_final.size(), &factory);
  } else {
    // Create builder and network.
    IBuilder *builder = createInferBuilder(gLogger);

    INetworkDefinition *network = nullptr;
    network = createResNet18_2D_513x257Network(*builder, *plugin_container,
                                               DimsCHW{c, model_h, model_w},
                                               weights, data_type, gLogger);

    builder->setMaxBatchSize(1);
    size_t workspace_bytes = 1024 * 1024 * 1024;
    builder->setMaxWorkspaceSize(workspace_bytes);

    builder->setHalf2Mode(data_type == DataType::kHALF);
    // Build the network.
    engine = builder->buildCudaEngine(*network);
    network->destroy();

    printf("Saving TensorRT plan to %s...\n", trt_plan_file.c_str());
    IHostMemory *model_stream = engine->serialize();
    std::ofstream trt_plan_out(trt_plan_file, std::ios::binary);
    trt_plan_out.write((const char *)model_stream->data(),
                       model_stream->size());
  }

  assert(engine->getNbBindings() == 3);
  void *buffers[3];
  int in_idx_left = engine->getBindingIndex("left");
  assert(in_idx_left == 0);
  int in_idx_right = engine->getBindingIndex("right");
  assert(in_idx_right == 1);
  int out_idx = engine->getBindingIndex("disp");
  assert(out_idx == 2);

  IExecutionContext *context = engine->createExecutionContext();

  bool use_profiler = true;
  context->setProfiler(use_profiler ? &s_profiler : nullptr);

  std::vector<float> output(model_h * model_w);

  // Allocate GPU memory and copy data.
  CHECK(cudaMalloc(&buffers[in_idx_left], model_w * model_h * sizeof(float)));
  CHECK(cudaMalloc(&buffers[in_idx_right], model_w * model_h * sizeof(float)));
  CHECK(cudaMalloc(&buffers[out_idx], model_w * model_h * sizeof(float)));

  cv::namedWindow("Left RGB frame", cv::WINDOW_AUTOSIZE);
  cv::namedWindow("Computed depth", cv::WINDOW_AUTOSIZE);

  while (true) {
    auto img_stereo = readVideoStream(cap, video_w, video_h, model_w, model_h);
    auto img_left = img_stereo[0];
    auto img_right = img_stereo[1];

    CHECK(cudaMemcpy(buffers[in_idx_left], img_left.data(),
                     img_left.size() * sizeof(float), cudaMemcpyHostToDevice));
    CHECK(cudaMemcpy(buffers[in_idx_right], img_right.data(),
                     img_right.size() * sizeof(float), cudaMemcpyHostToDevice));

    // Do the inference.
    auto host_start = std::chrono::high_resolution_clock::now();
    auto err = context->execute(1, buffers);
    auto host_end = std::chrono::high_resolution_clock::now();
    assert(err);
    UNUSED(err);
    auto host_elapsed_ms =
        std::chrono::duration<float, std::milli>(host_end - host_start).count();
    printf("Host time: %.4fms\n", host_elapsed_ms);

    if (use_profiler)
      s_profiler.printLayerTimes();

    // Copy output back to host.
    CHECK(cudaMemcpy(output.data(), buffers[out_idx],
                     output.size() * sizeof(float), cudaMemcpyDeviceToHost));

    // Display results.
    displayImg(img_left, "Left RGB frame", video_w / 2, video_h);
    displayImg(output, "Computed depth", video_w / 2, video_h);
  }

  // Cleanup.
  context->destroy();
  engine->destroy();
  for (auto b : buffers)
    CHECK(cudaFree(b));

  printf("Done\n");
  return 0;
}
