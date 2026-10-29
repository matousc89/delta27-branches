# Vytváření, prohlížení a editace Gaussian Splatů

Tento dokument popisuje, co je potřeba připravit pro vytvoření 3D Gaussian
Splatting (3DGS) reprezentace z videa nebo fotografií, jak ji vytvořit pomocí
Nerfstudio a jak výsledný soubor prohlížet, sdílet a editovat.

Příkazy v části „Workflow v tomto repozitáři“ odpovídají zdejšímu již
nainstalovanému prostředí. Obecné instalační příkazy je vhodné porovnat s
aktuální [dokumentací Nerfstudio](https://docs.nerf.studio/quickstart/installation.html),
protože kompatibilní verze PyTorch a CUDA se časem mění.

## 1. Co je výsledkem

Pipeline vytváří tři typy výstupů:

- `data/nerfstudio/<video>/` – vybrané snímky, odhadnuté pozice kamer a řídké
  SfM body;
- `outputs/<video>/splatfacto/<run>/` – plný checkpoint a `config.yml` pro
  další trénování, evaluaci a Nerfstudio viewer;
- `exports/<video>/splat.ply` – přenositelný export Gaussian Splatů.

`splat.ply` není klasický polygonový model. Obsahuje jednotlivé 3D Gaussiány:
jejich polohu, měřítko, rotaci, opacitu a barevné spherical-harmonics
koeficienty. Proto ho běžný PLY prohlížeč může interpretovat pouze jako body
nebo ho zobrazit chybně.

Jeden `splat.ply` představuje statickou scénu. Lze kolem ní animovat kameru,
ale pohyb objektů v původním videu v něm není zachován jako časová animace.
Animovaný/4D Gaussian Splatting je jiná pipeline.

## 2. Hardware

### Nutné

- NVIDIA GPU podporovaná zvolenou verzí CUDA a PyTorch;
- aktuální NVIDIA driver;
- dostatek RAM a volného disku pro snímky, příznaky, checkpointy a exporty.

### Praktické doporučení

- 8 GB VRAM je použitelné jen pro menší scény a nižší rozlišení;
- 12–16 GB VRAM je rozumné minimum pro běžnou práci;
- 24 GB a více výrazně snižuje potřebu omezovat rozlišení a počet Gaussiánů;
- 32 GB systémové RAM je rozumný základ, 64 GB je vhodných pro větší datasety;
- počítat alespoň s desítkami GB volného disku na projekt.

Tento projekt byl úspěšně zpracován na NVIDIA L40. Samotné exportované PLY zde
mají přibližně 170–200 MB, ale pracovní data a checkpointy jsou podstatně větší.

## 3. Software

### Doporučená platforma

Linux je nejjednodušší a nejlépe podporovaná varianta. Windows lze použít
nativně nebo přes WSL2, ale instalace CUDA rozšíření, COLMAP a kompilátorů bývá
křehčí. Alternativou je oficiální Docker image Nerfstudio s přístupem ke GPU.

### Potřebné komponenty

- Python 3.10–3.12 v samostatném virtuálním prostředí;
- PyTorch sestavený pro CUDA kompatibilní s místním NVIDIA driverem;
- Nerfstudio se Splatfacto/gsplat;
- FFmpeg pro extrakci snímků z videa;
- COLMAP, případně HLoc + pycolmap, pro Structure-from-Motion;
- Git a běžné C/C++ build nástroje pro instalaci CUDA rozšíření;
- moderní webový prohlížeč pro Nerfstudio nebo externí webový viewer.

Reprodukovaná konfigurace tohoto repozitáře:

| Komponenta | Verze |
| --- | --- |
| Python | 3.12.13 |
| PyTorch | 2.12.0+cu132 |
| CUDA použitá pro PyTorch | 13.2 |
| Nerfstudio | 1.1.5 |
| HLoc | 1.5 |
| pycolmap | 4.2.1 |
| FFmpeg | 7.1.2 |

Verze nejsou univerzální požadavek. Důležité je, aby NVIDIA driver, CUDA,
PyTorch a případná kompilovaná rozšíření byla vzájemně kompatibilní.

### Rychlá kontrola prostředí

V tomto repozitáři:

```bash
cd /home/cejnemat/delta27-branches
source ./activate-nerfstudio.sh

python --version
python -c "import torch; print(torch.__version__, torch.version.cuda); print(torch.cuda.is_available())"
nvidia-smi
ns-train --help
```

Na clusteru může být GPU dostupná až uvnitř přidělené GPU úlohy, nikoli na
login nodu. `torch.cuda.is_available()` proto musí být ověřeno tam, kde poběží
trénink.

Pro zpracování videa je zde potřeba načíst FFmpeg modul:

```bash
module load FFmpeg/7.1.2-GCCcore-14.3.0
ffmpeg -version
```

## 4. Požadavky na vstupní data

Kvalita záznamu má obvykle větší vliv než dlouhé ladění tréninku.

### Vhodný záznam

- scéna a objekty se během snímání nehýbou;
- kamera se pohybuje pomalu a plynule, nikoli pouze otáčí z jednoho místa;
- sousední pohledy mají velký překryv;
- objekt je zachycen z více stran a pokud možno z více výšek;
- expozice, vyvážení bílé a ostření se během záznamu nemění;
- snímky nejsou rozmazané a neobsahují digitální zoom;
- povrchy mají dostatek textury, podle níž lze spojovat snímky;
- v záběru se nepohybují lidé, auta, listí nebo výrazné stíny.

Pro strom a jemné větvičky je důležitý dostatečný úhlový rozsah. Pouhý posun
kamery po krátké přímce nevytvoří dost paralaxy pro spolehlivou hloubku.
Vítr je problematický: 3DGS a SfM předpokládají statickou scénu a pohybující se
větve mohou vzniknout jako rozmazané nebo zdvojené splaty.

### Počet snímků

Neexistuje pevné minimum. Přibližně 80 kvalitních a různorodých snímků může
stačit pro jednoduchý objekt, ale pro tenké větve je bezpečnější několik set
pohledů. Tisíce téměř identických video snímků nejsou automaticky lepší –
zvyšují čas a spotřebu paměti bez nové geometrické informace.

## 5. Workflow v tomto repozitáři

Následující příklad používá ID `20261029_112959`. Pro nové video změňte `ID`
a cestu k souboru.

### 5.1 Aktivace

```bash
cd /home/cejnemat/delta27-branches
module load FFmpeg/7.1.2-GCCcore-14.3.0
source ./activate-nerfstudio.sh
export MPLCONFIGDIR=/tmp/nerfstudio-mpl

ID=20261029_112959
```

### 5.2 Odhad kamer a řídké geometrie

Zdejší videa byla zpracována HLocem se SuperPoint a SuperGlue:

```bash
ns-process-data video \
  --data "data/vids/${ID}.mp4" \
  --output-dir "data/nerfstudio/${ID}" \
  --num-frames-target 400 \
  --sfm-tool hloc \
  --feature-type superpoint_aachen \
  --matcher-type superglue \
  --matching-method vocab_tree \
  --camera-type perspective \
  --num-downscales 3 \
  --colmap-cmd /usr/bin/true \
  --verbose
```

`--colmap-cmd /usr/bin/true` je lokální workaround: tato instalace používá
HLoc/pycolmap, ale Nerfstudio 1.1.5 přesto předem kontroluje existenci externího
COLMAP příkazu. Na standardní instalaci s dostupným `colmap` tento parametr
vynechte.

U složky fotografií se změní pouze vstupní subcommand:

```bash
ns-process-data images \
  --data data/images/moje_scena \
  --output-dir data/nerfstudio/moje_scena
```

Po zpracování zkontrolujte hlavně:

- kolik snímků bylo zaregistrováno;
- zda vznikl jeden souvislý model;
- zda `data/nerfstudio/<ID>/transforms.json` obsahuje očekávané kamery;
- zda trajektorie kamer a sparse point cloud dávají geometrický smysl.

Nízký podíl zaregistrovaných kamer nelze spolehlivě napravit delším 3DGS
tréninkem. Nejdřív je nutné opravit snímání nebo SfM.

### 5.3 Trénování Splatfacto

```bash
ns-train splatfacto \
  --data "data/nerfstudio/${ID}" \
  --output-dir outputs \
  --experiment-name "${ID}" \
  --timestamp splatfacto-l40 \
  --vis tensorboard \
  --max-num-iterations 30000
```

Výsledný konfigurační soubor bude v:

```text
outputs/<ID>/splatfacto/splatfacto-l40/config.yml
```

### 5.4 Evaluace

```bash
ns-eval \
  --load-config "outputs/${ID}/splatfacto/splatfacto-l40/config.yml" \
  --output-path "outputs/${ID}/splatfacto/splatfacto-l40/results.json"
```

PSNR a SSIM jsou lepší při vyšších hodnotách, LPIPS při nižších. Samotné
číselné metriky ale nenahrazují vizuální kontrolu floaters, děr a rozmazané
geometrie.

### 5.5 Export přenosného PLY

```bash
ns-export gaussian-splat \
  --load-config "outputs/${ID}/splatfacto/splatfacto-l40/config.yml" \
  --output-dir "exports/${ID}" \
  --output-filename splat.ply
```

Nerfstudio podporuje export Gaussian Splat PLY pouze z metod založených na
splatech, například Splatfacto; nelze takto exportovat checkpoint Nerfacto.

## 6. Prohlížení

### Varianta A: Nerfstudio viewer

Nejpřesnější kontrola původního trénovaného modelu. Potřebuje `config.yml`,
checkpoint a původní zpracovaná data, nikoli pouze `splat.ply`.

Na serveru:

```bash
source ./activate-nerfstudio.sh
ns-viewer \
  --load-config outputs/20261029_112959/splatfacto/splatfacto-l40/config.yml
```

Na lokálním počítači:

```bash
ssh -N -L 7007:127.0.0.1:7007 cejnemat@hop.fsid.cvut.cz
```

Poté otevřete `http://127.0.0.1:7007`. SSH terminál musí zůstat otevřený.

### Varianta B: SuperSplat

[SuperSplat](https://superspl.at/editor) je nejjednodušší univerzální volba pro
samotný `splat.ply`. Soubor lze přetáhnout do aktuálního Chrome/Edge nebo jiného
prohlížeče s WebGPU. Pro lokální načtení a editaci není potřeba účet; účet je
potřeba až pro publikování na hostované platformě.

SuperSplat umí:

- orbit/fly prohlížení;
- výběr, skrytí a odstranění floaters;
- crop, posun, rotaci a změnu měřítka;
- úpravy barvy, jasu a opacity;
- export PLY, komprimovaného PLY, SOG, SPZ nebo samostatného vieweru;
- vytvoření kamer, anotací a prezentace.

Při nahrání do hostované služby je nutné zvážit citlivost dat. Pro neveřejná
data použijte lokální open-source editor nebo self-hostovaný viewer.

### Varianta C: samostatný webový viewer

Oficiální [SuperSplat Viewer](https://github.com/playcanvas/supersplat-viewer)
lze provozovat jako statický web a předat mu PLY/SOG. Hodí se pro prezentaci,
nikoli pro trénování. SuperSplat Editor navíc umí vyexportovat samostatný HTML
viewer nebo ZIP balíček.

Lehkou alternativou je WebGL viewer
[antimatter15/splat](https://github.com/antimatter15/splat). Je vhodný pro
rychlé prohlížení, ale nabízí méně editačních funkcí.

### Varianta D: Postshot

[Postshot](https://www.jawset.com/docs/d/Postshot%20User%20Guide/Getting%20Started)
je desktopová aplikace pro vytvoření, prohlížení, kamerové animace a export
splatů. Je uživatelsky jednodušší než ruční Nerfstudio pipeline, ale podporované
platformy, GPU požadavky, licence a možnosti exportu závisejí na aktuální
verzi. Před použitím je proto nutné ověřit současné podmínky výrobce.

### Co nepoužívat bez 3DGS podpory

MeshLab, CloudCompare a běžný Blender import PLY nejsou samy o sobě 3DGS
renderery. Mohou zobrazit středy Gaussiánů jako point cloud, ale nezobrazí
správně anizotropní měřítko, rotaci, opacitu a view-dependent SH barvy.
Opětovný export z takového nástroje může 3DGS atributy zahodit. Pro Blender či
jiný DCC nástroj je nutný konkrétní doplněk s deklarovanou podporou formátu
Gaussian Splat PLY.

## 7. Editace a bezpečný export

Doporučený postup:

1. Originální `splat.ply` ponechat beze změny.
2. Otevřít kopii v SuperSplat Editoru.
3. Nejprve odstranit izolované floaters a oříznout oblast zájmu.
4. Scénu zkontrolovat z opačných a bočních pohledů; výběr v obrazovce může
   nechtěně zasáhnout i Gaussiány za objektem.
5. Až potom upravit orientaci, měřítko, barvy a opacitu.
6. Průběžnou práci uložit jako projekt a finální viditelné splaty exportovat do
   nového souboru.

PLY je vhodný jako plnokvalitní pracovní/archivní formát. Pro web je zbytečně
velký; SOG, SPZ nebo komprimovaný PLY se načítají rychleji, ale mohou používat
kvantizaci nebo menší počet SH pásem. Po konverzi proto vždy vizuálně
porovnejte barvy, průhlednost a detaily s originálem.

Gaussian Splat není topologický mesh. Pokud je cílem měření, fyzika, kolize,
3D tisk nebo klasická editace vrcholů a polygonů, je nutné vytvořit samostatný
mesh/point-cloud workflow. Přímý převod 3DGS na čistý mesh není bezeztrátový.

## 8. Kopírování výsledků na lokální počítač

Jeden export:

```bash
scp \
  cejnemat@hop.fsid.cvut.cz:/home/cejnemat/delta27-branches/exports/20261029_112959/splat.ply \
  .
```

Všechny exporty:

```bash
rsync -av --progress \
  cejnemat@hop.fsid.cvut.cz:/home/cejnemat/delta27-branches/exports/ \
  ./exports/
```

Pro externí 3DGS viewer obvykle stačí pouze `splat.ply`. Pro pokračování v
tréninku nebo Nerfstudio viewer je nutné zachovat `config.yml`, checkpoint a
zpracovaná data, ideálně celou odpovídající strukturu `outputs/` a
`data/nerfstudio/`.

## 9. Typické problémy

| Problém | Pravděpodobná příčina | Co zkusit |
| --- | --- | --- |
| Málo zaregistrovaných kamer | blur, malý překryv, opakující se textura | lepší záznam, více paralaxy, HLoc matcher |
| Zdvojené větve nebo duchové | pohyb objektu/vítr | natáčet za bezvětří, odstranit problematické snímky |
| Floaters kolem objektu | málo pohledů, odlesky, nekonzistentní pozadí | více úhlů, masky, cleanup v SuperSplat |
| Rozmazané tenké větve | nedostatek pixelů nebo úhlů | bližší/ostřejší záznam, vyšší rozlišení |
| CUDA out of memory | příliš velké obrazy/model | downscale, méně snímků, menší model nebo větší GPU |
| PLY vypadá jako body | použitý viewer neumí 3DGS PLY | použít SuperSplat či jiný 3DGS renderer |
| Nerfstudio viewer nenajde model | chybí checkpoint nebo data | použít celou trénovací složku, ne samotný PLY |
| Barvy se po exportu změnily | konverze/omezení SH pásem | exportovat více SH pásem, porovnat s originálem |

## 10. Další dokumentace

- [Nerfstudio – instalace](https://docs.nerf.studio/quickstart/installation.html)
- [Nerfstudio – vlastní video a fotografie](https://docs.nerf.studio/quickstart/custom_dataset.html)
- [Nerfstudio – Splatfacto a export](https://docs.nerf.studio/nerfology/methods/splat.html)
- [Nerfstudio – viewer a SSH tunel](https://docs.nerf.studio/quickstart/viewer_quickstart.html)
- [SuperSplat – začínáme](https://developer.playcanvas.com/user-manual/supersplat/getting-started/)
- [SuperSplat – podporované importy a exporty](https://developer.playcanvas.com/user-manual/supersplat/editor/import-export/)

