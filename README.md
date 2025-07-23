# Marathon Data Analysis Project

This is a data analysis project. This project provides tools for scraping race reports collected and hosted by MTEC results (`https://www.mtecresults.com/`), cleaning the data and performing some analysis of runners' performance. As an example, we provide a detailed analysis of the Twin Cities Marathon 2013 race (`https://www.tcmevents.org/`) concerning runner demographics, pacing patterns and performance variability.

---
<!-- 
## Features

* **Web Scraper (`mtecresults_scraper.py`):** A customizable data scraper. Collects detailed race reports (personal info, split times) from `mtecresults.com`.
* **Data Analysis for TCM 2013 (`02-data_analysis-tcm2013.ipynb`):** A comprehensive Jupyter Notebook for exploring runner demographics, pacing patterns and performance variability for the Twin Cities Marathon 2013.
* **Configurable Parameters:** Race report format and scraping parameters are managed via a `params.yaml` file.
--- -->

## Usage

The workflow is organized via Jupyter notebooks.

### Collecting Data

The `01-data_scraping.ipynb` notebook handles both scraping and initial cleaning.

1.  **Configure `params.yaml`**: Make sure the `config/params.yaml` file is set up for the race you want to scrape (e.g. the race report format, the checkpoint placements along the course etc.). We provide YAML configurations for the Twin Cities Marathons of 2013 and 2024.
2.  **Run the notebook**: Open and run `notebooks/01-data_scraping.ipynb`.
    ```bash
    jupyter notebook notebooks/01-data_scraping.ipynb
    ```
    This will save raw data to `data/raw/` and cleaned data to `data/clean/`.

We include the dataset for the TCM 2013.

### Data Analysis

The `02-data_analysis.ipynb` notebook contains statistical analysis of the collected race reports.

1.  **Ensure cleaned data exists**: Run the scraping and cleaning notebook first.
2.  **Run the analysis notebook**: Open and run all cells in `notebooks/02-data_analysis.ipynb`.
    ```bash
    jupyter notebook notebooks/02-data_analysis.ipynb
    ```
    This notebook will load the cleaned data and present various analyses on pacing, demographics, and performance.
---

### Customization

* **`config/params.yaml`**: Modify this file to specify different races (`race_id`), adjust runner ID ranges for scraping (`runner_id_ranges`), or update parsing-related parameters.
* **`src/scraping/mtecresults_scraper.py`**: For changes to scraping logic (e.g. if a race report HTML structure changes) or cleaning rules.
* **Notebooks**: Extend or modify the analysis in `02-data_analysis_tcm2013.ipynb` to explore different aspects of the data.

---

## Results & Insights
Some initial observations that we found interesting.
* Negative splitting appears in about 10% of cases among both professional and non-professional athletes, thus showing little correlation with such aerobic efficiency factors as VO2max.
* Male runners seem to be more prone to the "hitting the wall" phenomenon.

---
## Further development
Our working hypothesis is that a long-distance race outcome should be amenable to polynomial regression analysis. In particular, for a marathon, the pacing dynamics of a runner over the first half (provided enough checkpoint measurements provided) should be a reasonably good predictor of the race outcome. Also, it would be interesting to identify pacing patterns for different categories of runners (in terms of their athletic abilities) by means of clusterization.