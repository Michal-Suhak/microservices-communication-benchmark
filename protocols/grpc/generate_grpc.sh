#!/bin/bash

PROTO_DIR="protocols/grpc/protos"
OUT_DIR="protocols/grpc/generated"

mkdir -p $OUT_DIR

python -m grpc_tools.protoc \
  -I $PROTO_DIR \
  --python_out=$OUT_DIR \
  --grpc_python_out=$OUT_DIR \
  --pyi_out=$OUT_DIR \
  $PROTO_DIR/common.proto \
  $PROTO_DIR/order.proto \
  $PROTO_DIR/payment.proto \
  $PROTO_DIR/notification.proto

echo "gRPC code generated successfully in $OUT_DIR"