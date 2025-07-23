# A module for parsing HTML snippets with individual race reports from mtecresults.com
# The custom parameters are in config/params.yaml

import numpy as np, pandas as pd
import bs4, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import itertools, os, random, time
import yaml
from datetime import datetime

def extract_splits(html_data, runner_id, config_params):
    # This takes a HTML snippet for a single runner provided by the mtecresults server,
    # extracts the data from the splits table and returns the values as a dictionary {field_name: field_value}.
    # The entries for the splits by segment are kept in a table within the 'detailedresultsseg' div-container.
    # The entries for the cumulative splits are kept in a table within the 'detailedresultscum' div-container.
    # NOTE: This is sensitive to the table format that mtecresults is currently using.
    
    # Map user-readable column captions in an individual race report to the dataframe field names.
    PANDAS_COL_MAP = config_params['column_mapping']    
    PANDAS_START_MAP = config_params['splits']['start']
    
    SPLITS_DISTANCE = config_params['splits']['distance']    
    # Map a split label to an index 1...m, where m is the finish line.
    SPLITS_ORDER = {split: i for i, split in enumerate(SPLITS_DISTANCE, start=1)}
    
    splits_table = html_data.find('div', class_='detailedresultsseg')
    if not splits_table:
        print (f'Warning: could not find splits data for runner {runner_id}. Skipping.')
        return {}
        
    rows = iter(splits_table.find_all('tr'))    
    # We expect to see the column headers in the first row of the HTML table with a race report.
    headers = [header.get_text(strip=True) for header in next(rows).find_all('th')]
    headers.pop(0) # Drop the first column title (it just says 'Location')
    
    res = {}
    for row in rows:
        split_name = row.find('th').get_text(strip=True)
        if split_name in SPLITS_ORDER:
            for col, value in zip(headers, row.find_all('td')):
                if col in PANDAS_COL_MAP:
                    res[f'split_{SPLITS_ORDER[split_name]}_' + PANDAS_COL_MAP[col]] = value.get_text(strip=True)
                else:
                    print (f'Warning: unknown field "{col}" detected for runner {runner_id}.')
        elif split_name in PANDAS_START_MAP:
            # ChipStart, GunStart
            res[PANDAS_START_MAP[split_name]] = row.find('td').get_text(strip=True)
        else:
            print (f'Warning: unknown split label "{split_name}" detected for runner {runner_id}.')
           
    return res 

def extract_personal(html_data, runner_id):
    # This takes a HTML snippet for a single runner returned by the mtecresults server, 
    # extracts the personal data (the runner's name is omitted) and returns the values.
    # The personal data is kept in the 'me-auto mb-3 mb-md-0' div-container.
    #
    # Note that this is sensitive to the output format that mtecresults is currently using.

    personal = html_data.find('div', class_='me-auto mb-3 mb-md-0')    
    if not personal:
        print(f'Warning: could not find personal data for runner {runner_id}')
        return {}   
        
    # The personal data values are tagged by <strong>...</strong>
    res = {}
    try:
        strong_values = [value.get_text(strip=True) for value in personal.find_all('strong', class_='text-primary')]
        
        # The expected order of the values appearance: the event type, runner's ID (which we already have by now), sex, age, residence.
        res['event'], _, res['sex'], res['age'], res['residence'] = strong_values       
    except Exception as e:
        print(f'Warning: unexpected personal data format for runner {runner_id}. Error ({type(e).__name__}: {e})')
        return {}
        
    return res

def scrape_race_data(config_params, output_file):
    # For a pool of runner IDs, attempt to download and parse the invidual race reports from the mtecresults server.
    # The results are to be saved in an output CSV file and are returned as a pandas dataframe.
    
    # The parameters for the scraping session are passed as a yaml dictionary.
        
    # Setting up some constants for a scraping session.    
    URL_TEMPLATE = config_params['scraping']['url_template']
    RACE_ID = config_params['scraping']['race_id']

    # Some headers spoofing will be needed. The mtecresults server does not return results otherwise.
    HEADERS = config_params['scraping']['headers']

    # Scraping might take a while, since we will impose random delays in between requests.
    # Runners' IDs will be processed in batches, while saving intermediate results to the output file.
    BATCH_SIZE = config_params['scraping']['batch_size']
    OUTPUT_FILE = output_file
    # The last processed runner ID is to be kept in this file.
    SESSION_FILE = output_file + '.session' 

    # Runners' IDs are not assigned contiguously, but may appear within the union of some intervals [L1, R1], [L2, R2], ... [Lm, Rm]
    # according to the official status of a runner (competitive/non-competitive) and the starting corral.
    # For instance, for the TCM 2013 race, the official elite and sub-elite entries are in the interval [1,400].
    # The wheelchair athlete entries are in [401, 500]. The general public entries are in [1001, 14000].
    RUNNER_IDS_POOL = config_params['scraping']['runner_ids_pool']
    RUNNER_ID = config_params['scraping']['runner_id'] # Note: runner's ID is not necessarily the bib number.

    # Map user-readable column captions in an individual race report to the dataframe field names.
    PANDAS_COL_MAP = config_params['column_mapping']   
    PANDAS_START_MAP = config_params['splits']['start']

    # Map user-readable row captions in an individual race report to the actual distance marks.
    SPLITS_DISTANCE = config_params['splits']['distance']    
   
    # Personal data fields.
    PERSONAL = config_params['personal']    

    # Initiate the scraping process. If an output file is already present, try to resume from the last processed runner's ID saved in SESSION_FILE.    
    column_names = []
    if os.path.exists(OUTPUT_FILE):
        try:
            df = pd.read_csv(OUTPUT_FILE)
            if not df.empty and os.path.exists(SESSION_FILE):
                with open(SESSION_FILE, 'r') as f:
                    runner_id_init = int(f.read()) + 1 # Resume from the last ID + 1.
                column_names = pd.read_csv(OUTPUT_FILE, nrows=0).columns.tolist()                
                print(f'Found a scraping output file {OUTPUT_FILE}.\nResuming at runner ID {runner_id_init}.')
            else:
                print(f'Found a scraping output file {OUTPUT_FILE}, but the session data is incomplete.')                
        except Exception as e:
            raise Exception(f'Found a scraping output file {OUTPUT_FILE}, but cannot proceed due to an error: {e}.')
    # If there is no session to resume, start a new one.
    if not column_names:
        column_names = [RUNNER_ID] + PERSONAL
        # For each split add all the relevant data fields.
        for i,_ in enumerate(SPLITS_DISTANCE, start=1):
            for col_name in PANDAS_COL_MAP.values():
                column_names.append(f'split_{i}_' + col_name)
        column_names.extend(PANDAS_START_MAP.values()) 
    
        df = pd.DataFrame(columns=column_names)
        df.to_csv(OUTPUT_FILE, mode='w', header=True, index=False)
    
        # A new sessions starts at the lower bound of the first ID interval in the pool
        runner_id_init = RUNNER_IDS_POOL[0][0]
    
        print (f'Starting a new scraping session at runner ID {runner_id_init}.\nThe results are to be saved in {OUTPUT_FILE}.')
    
    # Putting together ID ranges to go through.
    runner_id_ranges = []
    total = 0
    for left, right in RUNNER_IDS_POOL:
        if runner_id_init <= right:
            new_left = max(runner_id_init, left)
            runner_id_ranges.append(range(new_left, right + 1))
            total += right - max(new_left, left) + 1
    print (f'{total} IDs are to be processed.')

    # Setting up a communication policy.
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504], # Status codes to retry on (429 is Too Many Requests).
        allowed_methods=["HEAD", "GET", "OPTIONS"] 
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)    

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    saved = len(df)
    entries_batch = []
    # The main scraping loop
    for runner_id in itertools.chain.from_iterable(runner_id_ranges):
        try:
            url = URL_TEMPLATE.format(rid=runner_id, race=RACE_ID)
            page_content = session.get(url, headers=HEADERS, allow_redirects=False, timeout=100)
            if page_content.status_code == 200: 
                # The server has returned some content. Presumably, a valid race report.
                html_data = bs4.BeautifulSoup(page_content.text, 'html.parser')
                
                entry = {'runner_id': runner_id}            
                entry.update(extract_personal(html_data, runner_id))
                entry.update(extract_splits(html_data, runner_id, config_params))
                entries_batch.append(entry)
                
            # Saving a batch when it is full or the last processed runner_id is a multiple of 2 * (batch size) to report on progress.
            if len(entries_batch) >= BATCH_SIZE or not runner_id % (BATCH_SIZE * 2):
                # Appending a new batch of entries to the output CSV file.
                df_batch = pd.DataFrame(entries_batch)
                df_batch = df_batch.reindex(columns=column_names)
                df_batch.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)                
                saved += len(entries_batch)   
                entries_batch.clear()
                
                if not runner_id % (BATCH_SIZE * 2):
                    print (f'Last processed runner ID: {runner_id}; {saved} entries saved.')
                    
                # Save the the runner ID processed last for this batch.
                with open(SESSION_FILE, 'w') as f:
                    f.write(str(runner_id))
                
        except requests.exceptions.RequestException as e:
            print (f'Error getting data for runner {runner_id} from {url}: {e}. Skipping.')
            
        # Being polite.
        time.sleep(random.uniform(0.5, 1))

    # Appending the final batch, if there is one.
    if entries_batch:
        df_batch = pd.DataFrame(entries_batch)
        df_batch = df_batch.reindex(columns=column_names)
        df_batch.to_csv(OUTPUT_FILE, mode='a', header=False, index=False)                
        saved += len(entries_batch)
        with open(SESSION_FILE, 'w') as f:
            f.write(str(runner_id))
        
    print (f'Data fetching completed. {processed} IDs have been processed.\n{saved} entrie(s) are saved in {OUTPUT_FILE}.')

    return df

def clean_race_data(config_params, raw_df):
    # We refine the raw data in raw_df to the only fields that we find useful in our model. 
    # This is customized in config/params.yaml and passed as config_params.
     
    PERSONAL = config_params['cleaning']['personal']
    SPLITS_DISTANCE = config_params['splits']['distance']
    SPLIT_INFO = config_params['cleaning']['split_info']
    PANDAS_START_MAP = config_params['splits']['start']
    FILTER_BY = config_params['cleaning']['filter_by']
    RUNNER_ID = config_params['scraping']['runner_id']

    if not isinstance(raw_df, pd.DataFrame):
        raise TypeError('raw_df must be a pandas DataFrame.')

    # We have some fields to filter by first. For instance, event == 'Marathon'.
    filter_and = pd.Series(True, index=raw_df.index)
    for filt_cond in FILTER_BY:
        for key, value in filt_cond.items():
            if key not in raw_df.columns:
                raise KeyError(f'Wrong dataset format. Column {key} not found.')
            filter_and &= (raw_df[key] == value)
    raw_df = raw_df[filter_and].copy()

    # We check the raw data for some consistency and build a clean dataset.
    try:
        clean_df = raw_df[[RUNNER_ID] + PERSONAL].copy()  
    except:
        raise KeyError(f'Wrong dataset format.') 
    
    # Any runner with at least one piece of non-split-related data missing is excluded from the dataset.
    runners_no_info = clean_df[PERSONAL].isnull().any(axis=1)
    if runners_no_info.any():
        print ('Warning: The following runners miss personal data and are excluded from the dataset:')
        print (raw_df[RUNNER_ID][runners_no_info])
    raw_df = raw_df[~runners_no_info]
    
    # A field may contain data for a split. Such fields are named 'split_{i}_<some split info>',
    # and are always included into the final dataset. Here, i is in 1...m, 
    # where the very last split i=m corresponds to the the finish line.
    split_columns = [f'split_{i}_' + col_name for i in range(1, len(SPLITS_DISTANCE) + 1) for col_name in SPLIT_INFO]
    split_columns.append(PANDAS_START_MAP['ChipStart'])
    try:
        clean_df[split_columns] = raw_df[split_columns]  
    except:
        raise KeyError(f'Wrong dataset format.') 
    
    # Stripping off what should be a state name. Go Minnesota! Ski-U-Mah!
    clean_df['residence'] = raw_df['residence'].map(lambda x: x.split(',')[-1].strip() if ',' in x else '')

    def convert_split_info(split_info):
        # If the argument is a string representing time in the format hh:mm:ss, mm:ss,
        # then convert it to the corresponding total time interval length in seconds.
        # If the argument is a string of the form 'place/total' representing the overall place of a runner at a split, return place as an int.
        if pd.isna(split_info):
            return np.nan
        try: 
            return int(split_info.split('/')[0])
        except:
            pass
        try:
            t = datetime.strptime(split_info, '%H:%M:%S').time()
            return 3600 * t.hour + 60 * t.minute + t.second
        except ValueError:
            pass             
        try:
            t = datetime.strptime(split_info, '%M:%S').time()
            return 60 * t.minute + t.second
        except ValueError:
            return np.nan

    # Convert split info from strings to numerics. 
    clean_df[split_columns] = clean_df[split_columns].map(convert_split_info).astype('Int32')

    clean_df.set_index(RUNNER_ID, inplace=True)
    
    return clean_df

if __name__ == '__main__':
    # Determine the project root dynamically, relative to the script's location
    # to make sure that paths like 'config/params.yaml' are resolved correctly.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, os.pardir)) # One level up from src/scraping

    try:
        config_yaml_path = sys.argv[1]
    except IndexError:
        print('Error: Missing a YAML config file path as an argument.')
        print('Usage: python mtecresults_scraper.py <path_to_config_yaml_file>')
        sys.exit(1)
    try:
        with open(os.path.join(project_root, config_yaml_path), 'r') as f:
            config_params = yaml.safe_load(f)

        output_file_relative = config_params['scraping']['output_file']
        output_file_abs = os.path.join(project_root, output_file_relative)

        df = scrape_race_data(config_params, output_file_abs)        
        print(df.head())

    except FileNotFoundError:
        print(f'Error: the YAML config file not found.')
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f'Error parsing the config file.')
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
