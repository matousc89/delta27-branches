# delta27-branches

## Nerfstudio

The local environment uses Python 3.12, PyTorch with CUDA, and Nerfstudio:

```bash
source ./activate-nerfstudio.sh
ns-train --help
```

## Video splat

The video in `data/vids` was reconstructed with Splatfacto (30,000 iterations).
The trained run and the exported Gaussian splat are located at:

- `outputs/20261013_162008/splatfacto/splatfacto-l40/`
- `exports/20261013_162008/splat.ply`

Open the trained scene in the Nerfstudio viewer with:

```bash
source ./activate-nerfstudio.sh
ns-viewer --load-config outputs/20261013_162008/splatfacto/splatfacto-l40/config.yml
```

##  How to run it

> source ./activate-nerfstudio.sh
ns-viewer --load-config outputs/20261013_162008/splatfacto/splatfacto-l40/config.yml

> ssh -N -L 7007:127.0.0.1:7007 cejnemat@hop.fsid.cvut.cz 