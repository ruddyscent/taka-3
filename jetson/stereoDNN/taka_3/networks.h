// Copyright (c) 2018, NVIDIA CORPORATION. All rights reserved.
// Full license terms provided in LICENSE.md file.

#ifndef NETWORKS_H
#define NETWORKS_H

#include <NvInfer.h>
#include <string>
#include <unordered_map>

namespace redtail {
namespace tensorrt {

using namespace nvinfer1;

using weight_map = std::unordered_map<std::string, Weights>;

class IPluginContainer;

// ResNet18_2D DNN: 513x256 input, 96 max disparity.
INetworkDefinition *createResNet18_2D_513x257Network(
    IBuilder &builder, IPluginContainer &plugin_factory, DimsCHW img_dims,
    const weight_map &weights, DataType data_type, ILogger &log);
} // namespace tensorrt
} // namespace redtail

#endif
