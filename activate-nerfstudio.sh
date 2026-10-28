#!/usr/bin/env bash

_NERFSTUDIO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

source "${_NERFSTUDIO_ROOT}/.venv/bin/activate"
export CUDA_HOME="/usr/local/cuda"
export PATH="${CUDA_HOME}/bin:${PATH}"
export TORCH_EXTENSIONS_DIR="${_NERFSTUDIO_ROOT}/.cache/torch_extensions"
export LD_LIBRARY_PATH="${CUDA_HOME}/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"

unset _NERFSTUDIO_ROOT
