## Marathon Data Analysis Project

This is a data analysis project. This project features a script for scraping race reports collected and hosted by the MTEC results (`https://www.mtecresults.com/`), cleaning the data and Jupyter notebooks for the race data analysis. As an example, we provide a detailed analysis of the Twin Cities Marathon races (`https://www.tcmevents.org/`) of 2013 and 2024.

---
<!-- 
## Features

* **Web Scraper (`mtecresults_scraper.py`):** A customizable data scraper. Collects detailed race reports (personal info, split times) from `mtecresults.com`.
* **Data Analysis for TCM 2013 (`02-data_analysis-tcm2013.ipynb`):** A comprehensive Jupyter Notebook for exploring runner demographics, pacing patterns and performance variability for the Twin Cities Marathon 2013.
* **Configurable Parameters:** Race report format and scraping parameters are managed via a `params.yaml` file.
--- -->

### Usage

The workflow is organized via Jupyter notebooks.

### Collecting Data

The `01-data_scraping.ipynb` notebook handles both scraping and initial cleaning.

1.  **Configure `params.yaml`**: Make sure the `config/params.yaml` file is set up properly for a race to scrape. This includes describing the outline of a race report, the checkpoint placements along the course etc. We provide YAML configurations for the Twin Cities Marathons of 2013 and 2024.
2.  **Run the notebook**: Open and run `notebooks/01-data_scraping.ipynb`.
    ```bash
    jupyter notebook notebooks/01-data_scraping.ipynb
    ```
    This will save raw data to `data/raw/` and cleaned data to `data/clean/`.

We include the datasets for the TCM 2013 and TCM 2024.

### Data Analysis

The `02-data_analysis-tcm2013.ipynb`, `02-data_analysis-tcm2024.ipynb` notebooks contains statistical analysis of the TCM 2013 and TCM 2024 races.

1.  **Ensure cleaned data exists**: Run the scraping and cleaning notebook first.
2.  **Run the analysis notebooks**: Open and run all cells in `notebooks/02-data_analysis-<...>.ipynb` and `notebooks/03-regression.ipynb`

The notebooks will load the cleaned data and present various data on runners' performance.

The latter notebook features a polynomial regression final time predictor. A quadratic one seems to produce satisfactory results, when it comes to estimating the final time based on the split measurements at 5K, 10K and the half-marathon marks.



### Customization

* **`config/params.yaml`**: Modify this file to specify a race, adjust runner ID ranges for scraping and set parsing-related parameters.
* **`src/scraping/mtecresults_scraper.py`**: This can be modified to accomodate possible changes in the scraping logic (for instance, if a race report HTML structure changes) or cleaning rules.
* **Notebooks**: Extend or modify the analysis in `02-data_analysis_<...>.ipynb` to explore different aspects of the data.



### Results & Insights
Some initial observations that we found interesting:
* according to the TCM 2013 analysis, negative splitting appears almost uniformly in about 10% of cases among both professional and non-professional athletes, thus showing little correlation with such aerobic efficiency factors as VO2max. A similar conclusion can be made based on the 2024 data, though with some reservations;
* male runners seem to be more prone to the "hitting the wall" condition.


### Further development
It could be interesting to identify the pacing patterns, exhibited in particular by the professional athletes, leading to better performance via some form of a clusterization analysis.