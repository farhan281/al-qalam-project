# Shamela Project - Category-Specific Run Instructions

## Quick Start

### Option 1: Run All Categories
```bash
cd /home/ubuntu/shamela_project
source shamela_env/bin/activate
python run.py
```

### Option 2: Run a Specific Category by Folder
Navigate to the category folder and run `run.py` directly:

```bash
cd /home/ubuntu/shamela_project
source shamela_env/bin/activate
cd "1_العقيدة"
python run.py
```

Or use the parent command:
```bash
cd /home/ubuntu/shamela_project
source shamela_env/bin/activate
python run.py --cat 1
```

## Category Folder Structure

Each category has its own folder with a dedicated `run.py`:

```
/home/ubuntu/shamela_project/
├── run.py                      # Main runner (all categories or specific --cat)
├── 1_العقيدة/
│   └── run.py                  # Scrapes only category 1
├── 2_الفرق والردود/
│   └── run.py                  # Scrapes only category 2
├── 3_التفسير/
│   └── run.py                  # Scrapes only category 3
├── ...
└── 40_علوم أخرى/
    └── run.py                  # Scrapes only category 40
```

## Running Categories

### Single Category (from folder)
```bash
cd "14_الفقه_الحنفي"
python run.py
```

### Single Category (from root)
```bash
python run.py --cat 14
```

### All Categories
```bash
python run.py
```

### Parallel Execution (recommended for speed)

In Terminal 1:
```bash
source shamela_env/bin/activate
cd "1_العقيدة"
python run.py
```

In Terminal 2:
```bash
source shamela_env/bin/activate
cd "3_التفسير"
python run.py
```

In Terminal 3:
```bash
source shamela_env/bin/activate
cd "6_كتب_السنة"
python run.py
```

All runs share the same `shamela_output/progress.json` and `shamela_output/reports/`, so books won't be duplicated even if running in parallel.

## Resume Support

If a category run is interrupted (Ctrl+C), restart the same command to resume from the last saved page:

```bash
cd "1_العقيدة"
python run.py  # Resumes from last checkpoint
```

## Output Structure

All categories save to:
```
shamela_output/
├── progress.json               # Shared resume state
├── report.csv                  # Master CSV (all books)
├── reports/
│   ├── report.csv              # Master CSV
│   ├── 1_العقيدة.csv           # Category 1 CSV
│   ├── 3_التفسير.csv           # Category 3 CSV
│   └── ...                     # Per-category CSVs
├── 1_العقيدة/
│   ├── الفقه_الأبسط.txt
│   ├── 1_العقيدة.csv
│   └── ...
├── 3_التفسير/
│   ├── تفسير_الطبري.txt
│   ├── 3_التفسير.csv
│   └── ...
└── ...
```

## Command Reference

| Command | Purpose |
|---------|---------|
| `python run.py` | Scrape all categories sequentially |
| `python run.py --cat 1` | Scrape only category 1 (العقيدة) |
| `python run.py --cat 14` | Scrape only category 14 (الفقه الحنفي) |
| `cd "14_الفقه_الحنفي" && python run.py` | Same as above (folder method) |
| `./run_all.sh` | Activate env and scrape all categories |
| `./run_all.sh status` | Show saved cursor and partial entries |
| `./run_all.sh clear-cursor` | Clear resume state to start fresh |

## Notes

- Each category folder is independent and can be run from its location
- Progress is saved globally in `shamela_output/progress.json` 
- No duplicates across parallel runs due to `category_id_book_id` key tracking
- All timestamps use Indian Standard Time (IST)
- CSV reports include: category, book, author, publisher, edition, pages, status, scraped_at, topics, URL, file path

See [scripts/README.md](scripts/README.md) and [RESUME_AND_GIT_INSTRUCTIONS.txt](RESUME_AND_GIT_INSTRUCTIONS.txt) for additional options.
