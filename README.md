# delta27-branches

## Nerfstudio

The local environment uses Python 3.12, PyTorch with CUDA, and Nerfstudio:

See [REQUIREMENTS.md](REQUIREMENTS.md) for the complete Czech guide to capture,
training, viewing, transferring, and editing Gaussian Splats.

```bash
source ./activate-nerfstudio.sh
ns-train --help
```

## Video splats

The videos were reconstructed with Splatfacto (30,000 iterations per run):

| Video | Registered cameras | Exported Gaussians | PSNR | SSIM | LPIPS |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20261013_162008` | 328/328 | 774,142 | 30.07 | 0.931 | 0.054 |
| `20261029_112409` | 464/464 | 726,256 | 24.50 | 0.859 | 0.136 |
| `20261029_112548` | 471/471 | 728,615 | 24.91 | 0.861 | 0.141 |
| `20261029_112834` | 597/597 | 834,428 | 30.44 | 0.937 | 0.097 |
| `20261029_112959` | 596/596 | 828,076 | 30.32 | 0.941 | 0.101 |

Each trained run is under `outputs/<video>/splatfacto/splatfacto-l40/` and its
portable Gaussian splat is at `exports/<video>/splat.ply`.

Open the trained scene in the Nerfstudio viewer with:

```bash
source ./activate-nerfstudio.sh
ns-viewer --load-config outputs/20261029_112959/splatfacto/splatfacto-l40/config.yml
```

Replace the video ID in the path to open another run. On your local computer,
forward the viewer port over SSH and then open `http://127.0.0.1:7007`:

```bash
ssh -N -L 7007:127.0.0.1:7007 cejnemat@hop.fsid.cvut.cz
```
