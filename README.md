# PlantWise

`PlantWise` is the baseline code snapshot of the PlantWise India model and web app before improvements from the newer `PlantWise` tree are ported over.

This repository intentionally does not track private or manually seeded datasets. Contributors are expected to populate those files locally before running the web app, training the model, or comparing outputs.

## New Files

The repository root still contains the original baseline scripts and app code. A few files and directories were added later to support regression analysis and single-species experiment runs without changing the baseline training flow.

- `generate_reports.py`
  New helper that packages run artifacts into report bundles for regression comparison.
- `reports/`
  New regression report store and static comparison viewer.
- `src/`
  New experiment/debugging implementation with its own backend, frontend, and config, separate from the original baseline runner and backend app.

## What is tracked

- Model harness and binary in the repo root.
- Backend source in `backend/app/`.
- Frontend source in `frontend/habitability-tool/`.
- Dependency manifests such as `requirements.txt` and frontend `package.json` files.
- Reports that contain aggregate trends.

## What is not tracked

- Datasets.
- Environmental layers.
- Trained model outputs (tif/asc files).
- Virtual environments, node packages and editor noise.
- logs/ directory. This data is only included in aggregate reports. 

## Data format

Presence points 
```
Species,Latitude,Longitude
```

## Python setup

Create a fresh virtual environment and install the minimum tracked Python dependencies:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Quickstart


### Run one raw maxent iteration 

From the root of this repo run
```console
$ uv venv .venv
$ source .venv/bin/activate 
# This assumes you have the directory setup described in "To train the model" section 
$ python3 separateSpecies.py
$ mkdir -p /tmp/deldata
$ java -Djava.awt.headless=true -cp maxent.jar density.MaxEnt nowarnings noprefixes jackknife outputdirectory=/tmp/deldata samplesfile=sp_data_final/Morinda_coreia.csv environmentallayers=final_attributes autoRun visible=False
```
This runs maxent once, against the species `Morinda_coreia.csv`, using the env layers in `final_attributes` and puts the output in `/tmp/deldata`

### Train the model

Assumes you have already seeded `Final_Species.csv`, `maxent.jar`, and `final_attributes/` locally.

```bash
cd PlantWise_v0
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
python3 separateSpecies.py
python3 InitialImplementation.py
```

To monitor Maxent CPU and memory usage in parallel and log only active samples to CSV, run this in another terminal before starting training:

```bash
cd PlantWise_v0
python3 monitor_maxent_pidstat.py --output logs/maxent_usage.csv
```

The monitor watches `java` processes, filters to Maxent invocations, and writes timestamped samples for CPU and RSS memory without filling the file with idle zero rows.

To start training from a clean slate, it is safe to remove generated runtime state and then re-run the splitter:

```bash
rm -rf sp_data_final pr_sp_data_final res tif_data_final
python3 separateSpecies.py
```
Do not remove these if you want to preserve your seeded inputs:

- `Final_Species.csv`
- `maxent.jar`
- `final_attributes/`

To verify the split-input state before training:

```bash
ls sp_data_final | head
ls sp_data_final/species_presence_counts.csv
```

### Generate reports 

To generate the auc report from all the independent per-species model outputs, run 
```bash
cd PlantWise_v0
python3 generate_reports.py
```

That creates a new timestamped directory under `reports/`, for example:

```text
reports/20260324_131500/
```
Which can be opened via the regression viewer - [Jump to section](#3-to-verify-regression)

### Run the app

#### Backend 

You can run the backend through the [container](./container/README.md) - this is probably simples but hard to modify. 

##### Run the backend throug the source

Assumes you have already seeded:

- `backend/app/data/auc_and_contributions.csv`
- `backend/app/data/final_tif_files_withNWG/`
- `frontend/habitability-tool/public/wgg.geojsonl.json`
- `frontend/habitability-tool/public/species_presence.csv`

Backend:

```bash
cd PlantWise_v0
source .venv/bin/activate
cd backend/app
python3 app.py
```

Frontend:

```bash
cd PlantWise_v0/frontend/habitability-tool
npm install
npm start
```

## Frontend setup

The actual React app lives in `frontend/habitability-tool`.

```bash
cd frontend/habitability-tool
npm install
npm start
```

There is also a legacy `frontend/package.json` at the parent level (recorded for baseline accuracy). Treat `frontend/habitability-tool/package.json` as the source of truth for the web app.

## Internals: data, bootstrap, regression etc.. 

## 0. End-to-end model training pipeline 


Baseline harness: 

1. User seeds `Final_Species.csv`, `maxent.jar`, and `final_attributes/`.
2. User runs `separateSpecies.py`.
3. That creates:
- `sp_data_final/<species>.csv`
- `sp_data_final/species_presence_counts.csv`
4. User runs `InitialImplementation.py`.
5. That runs Maxent per species CSV, writes Maxent outputs into `res/`, converts `.asc` to `tif_data_final/`, and moves successful species CSVs
into `pr_sp_data_final/`.
6. User runs `generate_reports.py`.
7. That copies the run artifacts into `reports/<run-id>/` and refreshes the regression viewer manifest.
8. User opens `reports/index.html` and compares the new report against `reports/baseline`.

For debugging, there is a separate single species experimentation flow which is net new which doesn't touch the queue directories or disrupt the end to end flow above. It writes to `experiments/`.



### 1. To run the end-to-end web app

The backend can serve predictions without the full training inputs, but it does require precomputed model outputs and summary metadata.

Desired local filesystem:

```text
PlantWise_v0/
  backend/
    app/
      data/
        auc_and_contributions.csv
        final_tif_files_withNWG/
          <species>.tif
          ...
  frontend/
    habitability-tool/
      public/
        wgg.geojsonl.json
        species_presence.csv
```

What each file is for:

- `backend/app/data/auc_and_contributions.csv`
  Used by the backend to attach AUC values to API results.
- `backend/app/data/final_tif_files_withNWG/*.tif`
  Used by the backend to look up suitability scores for requested coordinates.
- `frontend/habitability-tool/public/wgg.geojsonl.json`
  Used by the map UI to draw the geography layer.
- `frontend/habitability-tool/public/species_presence.csv`
  Used by the frontend download link on the "Our Model" page.

None of the above are tracked in git in this baseline.

### 2. To train the model

Training requires the source occurrence dataset, the environmental layers, and the Maxent binary. The script trains on the species CSVs found in `sp_data_final/`, which are generated from `Final_Species.csv`, and it reads the weather/environmental layers from `final_attributes/`.

Pipeline:

1. Seed `Final_Species.csv`, `maxent.jar`, and `final_attributes/` locally.
2. Run `python3 separateSpecies.py`.
3. This creates `sp_data_final/`, which is the pending input queue for model training.
4. It also creates `sp_data_final/species_presence_counts.csv`, a derived summary used to decide whether a species has enough presence points to train.
5. Run `python3 InitialImplementation.py`.
6. `InitialImplementation.py` reads per-species CSVs from `sp_data_final/`, writes temporary Maxent outputs to `res/`, converts the species `.asc` output into `.tif`, and then moves processed species CSVs into `pr_sp_data_final/`.

Directory roles:

- `sp_data_final/`
  One CSV per species generated from `Final_Species.csv`, this is a kind of "input queue" for training 
- `sp_data_final/species_presence_counts.csv`
  Preprocessing summary derived from `Final_Species.csv`; used to skip species with too few presence points.
- `pr_sp_data_final/`
  Archive of already-processed species CSVs; used to resume interrupted runs.
  After a species is handled, its CSV is moved here. This is how the harness tries to support resumable runs.
- `res/`
  Temporary Maxent working directory for intermediate `.asc`, `.html`, and plot outputs during training.
  The script converts the .asc into a .tif and deletes the per-species intermediates from `res/`.

Current expectation:

- `separateSpecies.py` should be run before `InitialImplementation.py`.
- These runtime directories are not tracked in git.
- On a clean checkout, the training script should fail clearly if the split-input state has not been created yet, rather than silently regenerating it.

Maxent binary source and version:

- Source location: https://biodiversityinformatics.amnh.org/open_source/maxent/
- Version used in the existing `PlantWise` workspace jar: `3.4.4`
- Expected location in `PlantWise_v0`: `PlantWise_v0/maxent.jar`

How to verify the version from a jar:

```bash
$ jshell --class-path maxent.jar <<'EOF'
> System.out.println(density.Utils.getVersion());
> EOF
|  Welcome to JShell -- Version 17.0.17
|  For an introduction type: /help intro

jshell> 3.4.4
```

In this workspace, running that against `PlantWise/maxent.jar` shows that `density.Utils.version` is initialized to `3.4.4`.

How to sanity-check that the jar is runnable in headless mode:

```bash
java -Djava.awt.headless=true -cp maxent.jar density.MaxEnt visible=false nowarnings
```

That command may still fail later if input layers are missing, but it confirms that Java can load the Maxent main class from the jar.

Desired local filesystem:

```text
PlantWise_v0/
  Final_Species.csv
  maxent.jar
  final_attributes/
    wc2.1_30s_bio_*_fc.asc
    wc2.1_30s_bio_*_fc.prj
    wc2.1_30s_bio_*_fc.tif
    wc2.1_30s_bio_*_fc.asc.aux.xml
    maxent.cache/
      ...
```

Generated at runtime:

```text
PlantWise_v0/
  sp_data_final/
  pr_sp_data_final/
  res/
  tif_data_final/
```

Notes:

- `separateSpecies.py` reads `Final_Species.csv` and creates `sp_data_final/`.
- `InitialImplementation.py` reads species CSVs from `sp_data_final/` and environmental layers from `final_attributes/`.
- `maxent.jar` must exist in the repository root next to `InitialImplementation.py`.
- The source occurrence and raster data are not in git. They must be seeded manually from the restricted dataset location below.
- None of the source data or generated outputs above are tracked in git in this baseline.

Dataset source:

- Data location: https://drive.google.com/drive/folders/1Z0fG6c9xir-KALGFmKkOPUeF1LxHJ-EF?usp=drive_link

### 3. To verify regressions

Regression verification in this repository is based on derived report bundles rather than the private raw occurrence or raster inputs.

Current layout:

```text
PlantWise_v0/
  reports/
    baseline/
      auc_and_contributions.csv
    <timestamp>/
      auc_and_contributions.csv
      report_summary.json
      report_bundle.json
      model_outputs/
        <species>.html
    report_manifest.js
    index.html
```

How to generate a new report bundle after a training run:

```bash
cd PlantWise_v0
python3 generate_reports.py
```

That creates a new timestamped directory under `reports/`, for example:

```text
reports/20260324_131500/
```

Each generated report bundle contains:

- `auc_and_contributions.csv`
  The species-level comparison surface used for regression checking.
- `report_summary.json`
  Timing, CPU/RAM, metric-source, and report metadata for the run.
- `report_bundle.json`
  Serialized data used by the browser dashboard.
- `model_outputs/`
  A preserved copy of the Maxent `res/` output tree for that run, including species HTML files, linked plots, and sibling raw outputs. This allows the dashboard to deep-link into the full species report even after `res/` is overwritten by later runs.

`generate_reports.py` also refreshes `reports/report_manifest.js`, which is what powers the dropdown list in `reports/index.html`.

How the comparison works:

- `reports/baseline/auc_and_contributions.csv` is the checked-in reference report.
- Each timestamped directory is a candidate run.
- Open `reports/index.html` in a browser.
- Select `baseline` as the baseline report and the timestamped directory as the candidate report.

This keeps the regression artifacts safe to commit because they are summaries and reports, not the private raw datasets themselves.

### 4. To run single-species experiments

There is also a small experiment service under `src/` for validating uploaded datasets, trying alternate Maxent args, and running one species into an isolated run directory.

Layout:

```text
PlantWise_v0/
  src/
    backend/
      app.py
      config/
        config.json
    frontend/
      index.html
      app.js
      styles.css
```

Config is in `src/backend/config/config.json`:

- `run_root`
  The parent directory where all experiment runs are stored.
- `seed_data`
  The seed CSV that every uploaded dataset is added to in memory. By default this points to `Final_Species.csv`.
- `maxent_args`
  The default Maxent args used when the form leaves args empty.
- `maxent_allowed_args`
  The allowed Maxent arg names used during validation. This list was prepopulated from the current Maxent parameter set and can be edited later if needed.

The upload schema must match `Final_Species.csv` exactly:

```text
Species,Latitude,Longitude
```

`seed_data` is resolved relative to the `PlantWise_v0` repository root, so the default value `Final_Species.csv` refers to:

```text
PlantWise_v0/Final_Species.csv
```

To start the experiment service:

```bash
cd PlantWise_v0
source .venv/bin/activate
python3 src/backend/app.py
```

Then open:

```text
http://127.0.0.1:5050/
```

Current flow:

1. Enter a run name and validate it against the configured `run_root`.
2. Upload one or more CSVs and validate that they match the seed schema and contain the target species.
3. Enter optional Maxent args and validate them against `maxent_allowed_args`.
4. Submit the run.
5. The backend creates `<run_root>/<name>/`, stores uploaded data, filters the requested species, runs Maxent into `<run_root>/<name>/model/res/`, writes logs, and generates a report bundle under `<run_root>/<name>/reports/`.
6. Visit `/runs/<name>` to refresh status and inspect logs.

The root regression viewer manifest is also refreshed after experiment report generation, so experiment report bundles can be compared alongside the checked-in baseline and full-run reports.

## Current policy

If a contributor clones this repository, they should expect to seed the runtime and training datasets by hand in the paths above before using the app or model training pipeline.

## Citations

While this repository itself adopts the same MIT license as maxent, we would like to acknowledge the contribution that made this work possible: 
```
Steven J. Phillips, Miroslav Dudík, Robert E. Schapire. [Internet] Maxent software for modeling species niches and distributions (Version 3.4.1). Available from url: http://biodiversityinformatics.amnh.org/open_source/maxent/. Accessed on 2026-3-17.
```
