The current configuration is

cd ~/Workspace/taka-3/jetson/stereoDNN
./bin/nvstereo_taka_debug "udp://192.168.0.178:9999?overrun_nonfatal=1&fifo_size=1316" 640 360 ./models/ResNet-18_2D/TensorRT/trt_weights_fp16.bin
